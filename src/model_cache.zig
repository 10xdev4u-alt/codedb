//! Shared model cache for the local embedding engine (issue #29).
//!
//! One copy per machine, not per project: the text model is shared by every
//! checkout. Downloads resume from a `.partial` file, verify SHA-256 before
//! the final rename, and never touch the network when a valid cache exists or
//! the caller asks for offline mode.

const std = @import("std");
const builtin = @import("builtin");
const cio = @import("cio.zig");

pub const override_env = "CODEDB_MODEL_DIR";
pub const offline_env = "CODEDB_OFFLINE";

pub const Spec = struct {
    /// File name inside the cache directory. No path separators.
    name: []const u8,
    url: []const u8,
    /// Lowercase or uppercase hex; 64 characters.
    sha256_hex: []const u8,
    size_bytes: u64,
};

pub const Options = struct {
    /// Never open a network connection. A missing or invalid cache fails with
    /// `error.ModelNotCachedOffline`.
    offline: bool = false,
};

pub const Error = error{
    ModelNotCachedOffline,
    ModelChecksumMismatch,
    ModelSizeMismatch,
    ModelDownloadFailed,
    InvalidModelSpec,
    InvalidModelCacheDir,
};

/// The machine-wide cache directory, created on demand.
///
/// Resolution order:
///   1. `$CODEDB_MODEL_DIR`
///   2. Windows: `%LOCALAPPDATA%/codedb/models`
///   3. macOS: `~/Library/Application Support/codedb/models`
///   4. Linux: `$XDG_DATA_HOME/codedb/models`, else
///      `~/.local/share/codedb/models`
pub fn cacheDir(io: std.Io, allocator: std.mem.Allocator) ![]u8 {
    if (cio.posixGetenv(override_env)) |value| {
        if (value.len == 0) return error.InvalidModelCacheDir;
        const dir = try allocator.dupe(u8, value);
        errdefer allocator.free(dir);
        std.Io.Dir.cwd().createDirPath(io, dir) catch return error.InvalidModelCacheDir;
        return dir;
    }

    const home = cio.homeDir() orelse return error.InvalidModelCacheDir;
    const dir = switch (builtin.os.tag) {
        .windows => blk: {
            const local = cio.posixGetenv("LOCALAPPDATA") orelse home;
            break :blk try std.fmt.allocPrint(allocator, "{s}/codedb/models", .{local});
        },
        .macos => try std.fmt.allocPrint(allocator, "{s}/Library/Application Support/codedb/models", .{home}),
        else => blk: {
            if (cio.posixGetenv("XDG_DATA_HOME")) |xdg| {
                if (xdg.len > 0) break :blk try std.fmt.allocPrint(allocator, "{s}/codedb/models", .{xdg});
            }
            break :blk try std.fmt.allocPrint(allocator, "{s}/.local/share/codedb/models", .{home});
        },
    };
    errdefer allocator.free(dir);
    std.Io.Dir.cwd().createDirPath(io, dir) catch return error.InvalidModelCacheDir;
    return dir;
}

/// The final path for a model. The directory is created.
pub fn modelPath(io: std.Io, allocator: std.mem.Allocator, spec: Spec) ![]u8 {
    try validateSpec(spec);
    const dir = try cacheDir(io, allocator);
    defer allocator.free(dir);
    return std.fmt.allocPrint(allocator, "{s}/{s}", .{ dir, spec.name });
}

/// The resumable download path for a model.
pub fn partialPath(io: std.Io, allocator: std.mem.Allocator, spec: Spec) ![]u8 {
    const path = try modelPath(io, allocator, spec);
    defer allocator.free(path);
    return std.fmt.allocPrint(allocator, "{s}.partial", .{path});
}

pub fn isOffline() bool {
    const raw = cio.posixGetenv(offline_env) orelse return false;
    return raw.len > 0 and
        !std.mem.eql(u8, raw, "0") and
        !std.ascii.eqlIgnoreCase(raw, "false");
}

/// Return the verified cache path, downloading only when needed.
///
/// A file that exists but fails size or hash verification is deleted and
/// fetched again. A `.partial` file is resumed with a `Range` request, so a
/// dropped 310 MB transfer does not start over.
pub fn ensure(io: std.Io, allocator: std.mem.Allocator, spec: Spec, options: Options) ![]u8 {
    try validateSpec(spec);
    const path = try modelPath(io, allocator, spec);
    errdefer allocator.free(path);
    const partial = try partialPath(io, allocator, spec);
    defer allocator.free(partial);

    if (try verify(io, allocator, path, spec)) {
        // A valid cache wins even when a stale partial is lying around.
        std.Io.Dir.deleteFileAbsolute(io, partial) catch {};
        return path;
    }

    // A file that exists but fails verification is corrupt. Remove it so the
    // download cannot append to bad bytes.
    std.Io.Dir.deleteFileAbsolute(io, path) catch {};

    if (options.offline or isOffline()) return error.ModelNotCachedOffline;

    try download(io, allocator, spec, path);
    if (!try verify(io, allocator, path, spec)) return error.ModelChecksumMismatch;
    return path;
}

/// True only when the file exists, has the declared size, and hashes to the
/// declared digest.
pub fn verify(io: std.Io, allocator: std.mem.Allocator, path: []const u8, spec: Spec) !bool {
    _ = allocator;
    const file = std.Io.Dir.openFileAbsolute(io, path, .{}) catch |err| switch (err) {
        error.FileNotFound => return false,
        else => return err,
    };
    defer file.close(io);

    const size = try file.length(io);
    if (size != spec.size_bytes) return false;
    return hashMatches(io, file, spec);
}

fn hashMatches(io: std.Io, file: std.Io.File, spec: Spec) !bool {
    var hasher = std.crypto.hash.sha2.Sha256.init(.{});
    var buffer: [64 * 1024]u8 = undefined;
    var offset: u64 = 0;
    while (offset < spec.size_bytes) {
        const read_len = try file.readPositionalAll(io, &buffer, offset);
        if (read_len == 0) return false;
        hasher.update(buffer[0..read_len]);
        offset += read_len;
    }
    var digest: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
    hasher.final(&digest);
    const hex = std.fmt.bytesToHex(digest, .lower);
    return std.ascii.eqlIgnoreCase(&hex, spec.sha256_hex);
}

fn validateSpec(spec: Spec) !void {
    if (spec.name.len == 0 or spec.name.len > 128) return error.InvalidModelSpec;
    if (std.mem.indexOfAny(u8, spec.name, "/\\") != null) return error.InvalidModelSpec;
    if (spec.url.len == 0 or spec.url.len > 2048) return error.InvalidModelSpec;
    if (spec.sha256_hex.len != 64) return error.InvalidModelSpec;
    for (spec.sha256_hex) |c| if (!std.ascii.isHex(c)) return error.InvalidModelSpec;
    if (spec.size_bytes == 0) return error.InvalidModelSpec;
    try validateUrl(spec.url);
}

fn validateUrl(url: []const u8) !void {
    const uri = std.Uri.parse(url) catch return error.InvalidModelSpec;
    if (uri.user != null or uri.password != null or uri.fragment != null) return error.InvalidModelSpec;
    if (std.ascii.eqlIgnoreCase(uri.scheme, "https")) return;
    if (!std.ascii.eqlIgnoreCase(uri.scheme, "http")) return error.InvalidModelSpec;
    var host_buf: [std.Io.net.HostName.max_len]u8 = undefined;
    const host = (uri.host orelse return error.InvalidModelSpec).toRaw(&host_buf) catch return error.InvalidModelSpec;
    if (std.ascii.eqlIgnoreCase(host, "localhost") or
        std.mem.eql(u8, host, "127.0.0.1") or
        std.mem.eql(u8, host, "[::1]")) return;
    return error.InvalidModelSpec;
}

fn download(io: std.Io, allocator: std.mem.Allocator, spec: Spec, final_path: []const u8) !void {
    const partial = try std.fmt.allocPrint(allocator, "{s}.partial", .{final_path});
    defer allocator.free(partial);

    var existing: u64 = 0;
    if (std.Io.Dir.openFileAbsolute(io, partial, .{})) |file| {
        existing = file.length(io) catch 0;
        file.close(io);
    } else |_| {}
    if (existing > spec.size_bytes) {
        std.Io.Dir.deleteFileAbsolute(io, partial) catch {};
        existing = 0;
    }

    var headers: [1]std.http.Header = undefined;
    var header_count: usize = 0;
    var range_buffer: [64]u8 = undefined;
    if (existing > 0) {
        const value = try std.fmt.bufPrint(&range_buffer, "bytes={d}-", .{existing});
        headers[0] = .{ .name = "range", .value = value };
        header_count = 1;
    }

    var client = std.http.Client{ .allocator = allocator, .io = io };
    defer client.deinit();
    const uri = try std.Uri.parse(spec.url);
    var req = try client.request(.GET, uri, .{
        .extra_headers = headers[0..header_count],
        .redirect_behavior = @fromBackingInt(@intCast(3)),
    });
    defer req.deinit();
    try req.sendBodiless();
    var redirect_buffer: [8 * 1024]u8 = undefined;
    var response = try req.receiveHead(&redirect_buffer);

    if (response.head.status == .range_not_satisfiable and existing == spec.size_bytes) {
        // The partial already holds every byte. Verify it below.
        return finishPartial(io, allocator, spec, partial, final_path);
    }

    const resuming = response.head.status == .partial_content and existing > 0;
    if (response.head.status != .ok and !resuming) return error.ModelDownloadFailed;

    // A 200 answer to a Range request means the server ignored the range.
    // Start over instead of appending the whole body to the prefix.
    var offset: u64 = if (resuming) existing else 0;
    const file = try std.Io.Dir.createFileAbsolute(io, partial, .{ .truncate = !resuming });
    defer file.close(io);

    var transfer_buffer: [64 * 1024]u8 = undefined;
    const reader = response.reader(&transfer_buffer);
    var body_buffer: [64 * 1024]u8 = undefined;
    while (true) {
        const read_len = reader.readSliceShort(&body_buffer) catch |err| switch (err) {
            error.ReadFailed => return response.bodyErr() orelse error.ModelDownloadFailed,
        };
        if (read_len == 0) break;
        if (offset + read_len > spec.size_bytes) return error.ModelSizeMismatch;
        try file.writePositionalAll(io, body_buffer[0..read_len], offset);
        offset += read_len;
    }
    try file.sync(io);

    // An interrupted body keeps the partial for the next resume.
    if (offset != spec.size_bytes) return error.ModelSizeMismatch;
    return finishPartial(io, allocator, spec, partial, final_path);
}

fn finishPartial(
    io: std.Io,
    allocator: std.mem.Allocator,
    spec: Spec,
    partial: []const u8,
    final_path: []const u8,
) !void {
    _ = allocator;
    const file = std.Io.Dir.openFileAbsolute(io, partial, .{}) catch return error.ModelDownloadFailed;
    defer file.close(io);
    if (!try hashMatches(io, file, spec)) {
        std.Io.Dir.deleteFileAbsolute(io, partial) catch {};
        return error.ModelChecksumMismatch;
    }
    std.Io.Dir.deleteFileAbsolute(io, final_path) catch {};
    try std.Io.Dir.renameAbsolute(partial, final_path, io);
}

// ── Tests ────────────────────────────────────────────────────────────────────

const testing = std.testing;
const test_io = testing.io;

const EnvGuard = struct {
    name: []const u8,
    had_prev: bool,
    prev_len: usize,
    prev: [4096]u8,

    fn save(name: []const u8) EnvGuard {
        var guard = EnvGuard{ .name = name, .had_prev = false, .prev_len = 0, .prev = undefined };
        if (cio.posixGetenv(name)) |value| {
            if (value.len <= guard.prev.len) {
                @memcpy(guard.prev[0..value.len], value);
                guard.prev_len = value.len;
                guard.had_prev = true;
            }
        }
        return guard;
    }

    fn restore(self: *const EnvGuard) void {
        if (self.had_prev) cio.posixSetenv(self.name, self.prev[0..self.prev_len]) else cio.posixUnsetenv(self.name);
    }
};

const MockModelServer = struct {
    server: *std.Io.net.Server,
    body: []const u8,
    connections: usize,
    request_count: usize = 0,
    last_range: [64]u8 = undefined,
    last_range_len: usize = 0,
    failure: ?anyerror = null,

    fn run(self: *MockModelServer) void {
        for (0..self.connections) |_| {
            self.serveOne() catch |err| {
                self.failure = err;
                return;
            };
            self.request_count += 1;
        }
    }

    fn serveOne(self: *MockModelServer) !void {
        const stream = try self.server.accept(test_io);
        defer stream.close(test_io);

        var request_buffer: [8192]u8 = undefined;
        var request_len: usize = 0;
        while (request_len < request_buffer.len) {
            var iov = [1][]u8{request_buffer[request_len..]};
            const n = (try stream.readWithControl(test_io, &iov, &.{})).data_len;
            if (n == 0) break;
            request_len += n;
            if (std.mem.indexOf(u8, request_buffer[0..request_len], "\r\n\r\n") != null) break;
        }
        const request = request_buffer[0..request_len];

        self.last_range_len = 0;
        var start: usize = 0;
        var status: []const u8 = "200 OK";
        var extra_header: []const u8 = "";
        var header_buffer: [256]u8 = undefined;
        if (findHeader(request, "range")) |value| {
            if (value.len <= self.last_range.len) {
                @memcpy(self.last_range[0..value.len], value);
                self.last_range_len = value.len;
            }
            if (std.mem.startsWith(u8, value, "bytes=") and std.mem.endsWith(u8, value, "-")) {
                const parsed = std.fmt.parseInt(usize, value[6 .. value.len - 1], 10) catch 0;
                if (parsed <= self.body.len) {
                    start = parsed;
                    status = "206 Partial Content";
                    extra_header = std.fmt.bufPrint(
                        &header_buffer,
                        "Content-Range: bytes {d}-{d}/{d}\r\n",
                        .{ start, self.body.len - 1, self.body.len },
                    ) catch "";
                }
            }
        }

        const slice = self.body[start..];
        var head_buffer: [512]u8 = undefined;
        const head = try std.fmt.bufPrint(
            &head_buffer,
            "HTTP/1.1 {s}\r\nContent-Length: {d}\r\n{s}Connection: close\r\n\r\n",
            .{ status, slice.len, extra_header },
        );
        var writer_buffer: [4096]u8 = undefined;
        var writer = stream.writer(test_io, &writer_buffer);
        try writer.interface.writeAll(head);
        try writer.interface.writeAll(slice);
        try writer.interface.flush();
    }
};

fn findHeader(request: []const u8, name: []const u8) ?[]const u8 {
    var lines = std.mem.splitSequence(u8, request, "\r\n");
    while (lines.next()) |line| {
        const colon = std.mem.indexOfScalar(u8, line, ':') orelse continue;
        if (std.ascii.eqlIgnoreCase(std.mem.trim(u8, line[0..colon], " \t"), name)) {
            return std.mem.trim(u8, line[colon + 1 ..], " \t");
        }
    }
    return null;
}

const TestModel = struct {
    body: []u8,
    sha256_hex: [64]u8,

    fn init(allocator: std.mem.Allocator) !TestModel {
        const body = try allocator.alloc(u8, 8192);
        for (body, 0..) |*byte, i| byte.* = @intCast(i % 251);
        var digest: [std.crypto.hash.sha2.Sha256.digest_length]u8 = undefined;
        std.crypto.hash.sha2.Sha256.hash(body, &digest, .{});
        return .{ .body = body, .sha256_hex = std.fmt.bytesToHex(digest, .lower) };
    }

    fn deinit(self: *TestModel, allocator: std.mem.Allocator) void {
        allocator.free(self.body);
    }

    fn spec(self: *const TestModel, url: []const u8) Spec {
        return .{
            .name = "test-model.gguf",
            .url = url,
            .sha256_hex = &self.sha256_hex,
            .size_bytes = self.body.len,
        };
    }
};

fn tmpCacheDir(tmp: *std.testing.TmpDir) ![]u8 {
    var path_buffer: [std.fs.max_path_bytes]u8 = undefined;
    const len = try tmp.dir.realPath(test_io, &path_buffer);
    return testing.allocator.dupe(u8, path_buffer[0..len]);
}

test "model cache: honors the directory override and rejects traversal" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    const resolved = try cacheDir(test_io, testing.allocator);
    defer testing.allocator.free(resolved);
    try testing.expectEqualStrings(override, resolved);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);
    const bad = Spec{
        .name = "../escape.gguf",
        .url = "https://example.com/model.gguf",
        .sha256_hex = &model.sha256_hex,
        .size_bytes = model.body.len,
    };
    try testing.expectError(error.InvalidModelSpec, ensure(test_io, testing.allocator, bad, .{ .offline = true }));
}

test "model cache: downloads once, then reuses the cache offline" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);

    const addr = try std.Io.net.IpAddress.parse("127.0.0.1", 0);
    var server = try addr.listen(test_io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(test_io);
    var url_buffer: [128]u8 = undefined;
    const url = try std.fmt.bufPrint(&url_buffer, "http://127.0.0.1:{d}/model.gguf", .{server.socket.address.getPort()});

    var mock = MockModelServer{ .server = &server, .body = model.body, .connections = 1 };
    const thread = try std.Thread.spawn(.{}, MockModelServer.run, .{&mock});
    const spec = model.spec(url);

    const path = try ensure(test_io, testing.allocator, spec, .{});
    defer testing.allocator.free(path);
    thread.join();
    if (mock.failure) |err| return err;
    try testing.expectEqual(@as(usize, 1), mock.request_count);
    try testing.expectEqual(@as(usize, 0), mock.last_range_len);
    try testing.expect(try verify(test_io, testing.allocator, path, spec));

    const reused = try ensure(test_io, testing.allocator, spec, .{ .offline = true });
    defer testing.allocator.free(reused);
    try testing.expectEqualStrings(path, reused);
}

test "model cache: resumes a partial download" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);

    const addr = try std.Io.net.IpAddress.parse("127.0.0.1", 0);
    var server = try addr.listen(test_io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(test_io);
    var url_buffer: [128]u8 = undefined;
    const url = try std.fmt.bufPrint(&url_buffer, "http://127.0.0.1:{d}/model.gguf", .{server.socket.address.getPort()});
    const spec = model.spec(url);

    const partial = try partialPath(test_io, testing.allocator, spec);
    defer testing.allocator.free(partial);
    {
        const file = try std.Io.Dir.createFileAbsolute(test_io, partial, .{ .truncate = true });
        defer file.close(test_io);
        try file.writePositionalAll(test_io, model.body[0..1000], 0);
    }

    var mock = MockModelServer{ .server = &server, .body = model.body, .connections = 1 };
    const thread = try std.Thread.spawn(.{}, MockModelServer.run, .{&mock});
    const path = try ensure(test_io, testing.allocator, spec, .{});
    defer testing.allocator.free(path);
    thread.join();
    if (mock.failure) |err| return err;

    try testing.expectEqual(@as(usize, 1), mock.request_count);
    try testing.expectEqualStrings("bytes=1000-", mock.last_range[0..mock.last_range_len]);
    try testing.expect(try verify(test_io, testing.allocator, path, spec));
}

test "model cache: re-downloads a truncated final file" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);

    const addr = try std.Io.net.IpAddress.parse("127.0.0.1", 0);
    var server = try addr.listen(test_io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(test_io);
    var url_buffer: [128]u8 = undefined;
    const url = try std.fmt.bufPrint(&url_buffer, "http://127.0.0.1:{d}/model.gguf", .{server.socket.address.getPort()});
    const spec = model.spec(url);

    const path = try modelPath(test_io, testing.allocator, spec);
    defer testing.allocator.free(path);
    {
        const file = try std.Io.Dir.createFileAbsolute(test_io, path, .{ .truncate = true });
        defer file.close(test_io);
        try file.writePositionalAll(test_io, model.body[0..100], 0);
    }

    var mock = MockModelServer{ .server = &server, .body = model.body, .connections = 1 };
    const thread = try std.Thread.spawn(.{}, MockModelServer.run, .{&mock});
    const ensured = try ensure(test_io, testing.allocator, spec, .{});
    defer testing.allocator.free(ensured);
    thread.join();
    if (mock.failure) |err| return err;

    try testing.expectEqual(@as(usize, 1), mock.request_count);
    try testing.expectEqual(@as(usize, 0), mock.last_range_len);
    try testing.expect(try verify(test_io, testing.allocator, ensured, spec));
}

test "model cache: offline without a valid cache fails with a typed reason" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);
    const spec = model.spec("https://example.com/model.gguf");
    try testing.expectError(
        error.ModelNotCachedOffline,
        ensure(test_io, testing.allocator, spec, .{ .offline = true }),
    );
}

test "model cache: rejects a checksum mismatch and leaves no final file" {
    var dir_guard = EnvGuard.save(override_env);
    defer dir_guard.restore();
    var offline_guard = EnvGuard.save(offline_env);
    defer offline_guard.restore();
    cio.posixUnsetenv(offline_env);

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const override = try tmpCacheDir(&tmp);
    defer testing.allocator.free(override);
    cio.posixSetenv(override_env, override);

    var model = try TestModel.init(testing.allocator);
    defer model.deinit(testing.allocator);
    const tampered = try testing.allocator.dupe(u8, model.body);
    defer testing.allocator.free(tampered);
    tampered[0] ^= 0xff;

    const addr = try std.Io.net.IpAddress.parse("127.0.0.1", 0);
    var server = try addr.listen(test_io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(test_io);
    var url_buffer: [128]u8 = undefined;
    const url = try std.fmt.bufPrint(&url_buffer, "http://127.0.0.1:{d}/model.gguf", .{server.socket.address.getPort()});
    const spec = model.spec(url);

    var mock = MockModelServer{ .server = &server, .body = tampered, .connections = 1 };
    const thread = try std.Thread.spawn(.{}, MockModelServer.run, .{&mock});
    try testing.expectError(
        error.ModelChecksumMismatch,
        ensure(test_io, testing.allocator, spec, .{}),
    );
    thread.join();
    if (mock.failure) |err| return err;

    const path = try modelPath(test_io, testing.allocator, spec);
    defer testing.allocator.free(path);
    const final = std.Io.Dir.openFileAbsolute(test_io, path, .{});
    if (final) |file| {
        file.close(test_io);
        return error.TestUnexpectedResult;
    } else |err| try testing.expectEqual(error.FileNotFound, err);
}
