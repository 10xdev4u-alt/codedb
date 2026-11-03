//! Managed llama.cpp sidecar for local embeddings (issue #26).
//!
//! The parent never talks to the model process directly. It spawns a small
//! supervisor (`codedb-sidecar`) with a stdin pipe, and the supervisor owns
//! the server process in its own process group. When the parent dies — even
//! from SIGKILL — the pipe closes, the supervisor wakes on EOF, terminates
//! the server group, and exits. That is what keeps a killed codedb from
//! leaving a 310 MB model process behind.
//!
//! This module is transport only. It does not build query/document prefixes
//! or parse vectors; the provider in #30 does that through the seam from #25.

const std = @import("std");
const builtin = @import("builtin");
const cio = @import("cio.zig");

pub const default_startup_timeout_ms: u32 = 30_000;
pub const default_stop_grace_ms: u32 = 5_000;
pub const default_request_timeout_ms: u32 = 30_000;
pub const health_poll_interval_ms: u32 = 50;
pub const max_server_args: usize = 32;
pub const max_request_bytes: usize = 4 * 1024 * 1024;
pub const max_response_bytes: usize = 8 * 1024 * 1024;
pub const max_inputs: usize = 256;

pub const Error = error{
    InvalidSidecarOptions,
    SidecarUnavailable,
    SidecarRequestRejected,
    SidecarRequestTooLarge,
    SidecarStartTimeout,
    SidecarRestartFailed,
};

const FetchRace = union(enum) {
    fetch: anyerror![]u8,
    timeout: std.Io.Cancelable!void,
};

pub const Options = struct {
    /// Path to the `codedb-sidecar` supervisor.
    supervisor_path: []const u8,
    /// Path to the model server. In production this is `llama-server`.
    server_path: []const u8,
    /// Model file passed to the server as `--model`.
    model_path: []const u8,
    /// Extra server arguments, for example `--embeddings` and `--ctx-size`.
    server_args: []const []const u8 = &.{},
    startup_timeout_ms: u32 = default_startup_timeout_ms,
    stop_grace_ms: u32 = default_stop_grace_ms,
    request_timeout_ms: u32 = default_request_timeout_ms,
};

pub const EmbedResult = struct {
    /// Raw JSON response body. The caller owns it.
    body: []u8,
    /// True when the first attempt failed at the transport level, the
    /// sidecar was restarted once, and the retry succeeded.
    restarted: bool,
};

/// A running supervisor plus its port. `stop` is idempotent; `deinit` frees
/// the owned copy of the options and must be the last call.
pub const Sidecar = struct {
    io: std.Io,
    allocator: std.mem.Allocator,
    /// Owned copy of the caller's options. The caller may free its own
    /// strings as soon as `start` returns.
    arena: std.heap.ArenaAllocator,
    options: Options,
    child: std.process.Child,
    port: u16,
    restarts: u32 = 0,
    health_url_buffer: [64]u8 = undefined,
    health_url_len: usize = 0,
    embed_url_buffer: [64]u8 = undefined,
    embed_url_len: usize = 0,

    pub fn start(io: std.Io, allocator: std.mem.Allocator, options: Options) !Sidecar {
        try validateOptions(options);
        var arena = std.heap.ArenaAllocator.init(allocator);
        errdefer arena.deinit();
        const port = try pickPort(io);
        // Clone before copying the arena into `self`: the copy snapshots the
        // arena's linked list, and allocating afterwards would update only
        // the local variable.
        const owned_options = try cloneOptions(arena.allocator(), options);
        var self = Sidecar{
            .io = io,
            .allocator = allocator,
            .arena = arena,
            .options = owned_options,
            .child = undefined,
            .port = port,
        };
        self.buildUrls();
        try self.spawnSupervisor();
        errdefer self.stop();
        try self.waitForHealth();
        return self;
    }

    /// Stop the supervisor and release the owned options.
    pub fn deinit(self: *Sidecar) void {
        self.stop();
        self.arena.deinit();
    }

    /// Close the pipe first: the supervisor sees EOF and terminates the
    /// server itself. If it does not exit within the grace period, kill it.
    pub fn stop(self: *Sidecar) void {
        closeStdin(self.io, &self.child);
        // Closing the pipe is the stop request. Wait for the supervisor to
        // run its own cleanup before escalating: a signal sent now would kill
        // it while it is still waking up on EOF and orphan the server.
        terminate(self.io, &self.child, self.options.stop_grace_ms, false, null);
    }

    pub fn health(self: *Sidecar) !bool {
        const body = try self.fetchWithTimeout(self.healthUrl(), .GET, null, &.{});
        defer self.allocator.free(body);
        return true;
    }

    /// POST the inputs to the server's OpenAI-compatible embeddings endpoint.
    /// A transport failure triggers exactly one restart and retry.
    pub fn embed(self: *Sidecar, inputs: []const []const u8) !EmbedResult {
        if (inputs.len == 0 or inputs.len > max_inputs) return error.InvalidSidecarOptions;
        const body = try self.encodeEmbedRequest(inputs);
        defer self.allocator.free(body);

        const first = self.postEmbeddings(body);
        if (first) |response| {
            return .{ .body = response, .restarted = false };
        } else |err| {
            if (err != error.SidecarUnavailable) return err;
            try self.restart();
            const response = try self.postEmbeddings(body);
            return .{ .body = response, .restarted = true };
        }
    }

    fn restart(self: *Sidecar) !void {
        self.stop();
        self.restarts += 1;
        self.spawnSupervisor() catch return error.SidecarRestartFailed;
        self.waitForHealth() catch {
            self.stop();
            return error.SidecarRestartFailed;
        };
    }

    fn buildUrls(self: *Sidecar) void {
        const health_url = std.fmt.bufPrint(&self.health_url_buffer, "http://127.0.0.1:{d}/health", .{self.port}) catch unreachable;
        self.health_url_len = health_url.len;
        const embed_url = std.fmt.bufPrint(&self.embed_url_buffer, "http://127.0.0.1:{d}/v1/embeddings", .{self.port}) catch unreachable;
        self.embed_url_len = embed_url.len;
    }

    fn healthUrl(self: *const Sidecar) []const u8 {
        return self.health_url_buffer[0..self.health_url_len];
    }

    fn embedUrl(self: *const Sidecar) []const u8 {
        return self.embed_url_buffer[0..self.embed_url_len];
    }

    fn spawnSupervisor(self: *Sidecar) !void {
        var port_buffer: [8]u8 = undefined;
        const port_text = std.fmt.bufPrint(&port_buffer, "{d}", .{self.port}) catch return error.InvalidSidecarOptions;

        var argv: [6 + max_server_args][]const u8 = undefined;
        var count: usize = 0;
        argv[count] = self.options.supervisor_path;
        count += 1;
        argv[count] = "--";
        count += 1;
        argv[count] = self.options.server_path;
        count += 1;
        // Server-specific arguments come first so a helper can see its own
        // subcommand before the flags every server shares.
        for (self.options.server_args) |arg| {
            argv[count] = arg;
            count += 1;
        }
        argv[count] = "--model";
        count += 1;
        argv[count] = self.options.model_path;
        count += 1;
        argv[count] = "--port";
        count += 1;
        argv[count] = port_text;
        count += 1;

        self.child = std.process.spawn(self.io, .{
            .argv = argv[0..count],
            .stdin = .pipe,
            .stdout = .ignore,
            .stderr = .inherit,
        }) catch return error.SidecarUnavailable;
    }

    fn waitForHealth(self: *Sidecar) !void {
        const deadline = cio.milliTimestamp() + @as(i64, self.options.startup_timeout_ms);
        while (cio.milliTimestamp() < deadline) {
            if (self.health()) |ok| {
                if (ok) return;
            } else |_| {}
            self.io.sleep(.fromMilliseconds(health_poll_interval_ms), .awake) catch return error.SidecarStartTimeout;
        }
        return error.SidecarStartTimeout;
    }

    fn encodeEmbedRequest(self: *Sidecar, inputs: []const []const u8) ![]u8 {
        const Request = struct {
            model: []const u8 = "embeddinggemma",
            input: []const []const u8,
        };
        return std.json.Stringify.valueAlloc(self.allocator, Request{ .input = inputs }, .{});
    }

    fn postEmbeddings(self: *Sidecar, body: []const u8) ![]u8 {
        if (body.len > max_request_bytes) return error.SidecarRequestTooLarge;
        const headers = [_]std.http.Header{
            .{ .name = "content-type", .value = "application/json" },
        };
        return self.fetchWithTimeout(self.embedUrl(), .POST, body, &headers);
    }

    fn fetchWithTimeout(
        self: *Sidecar,
        url: []const u8,
        method: std.http.Method,
        payload: ?[]const u8,
        headers: []const std.http.Header,
    ) ![]u8 {
        const Race = FetchRace;
        var completed: [2]Race = undefined;
        var select = std.Io.Select(Race).init(self.io, &completed);
        select.async(.fetch, fetchOnce, .{ self.io, self.allocator, url, method, payload, headers });
        select.async(.timeout, sleepFor, .{ self.io, self.options.request_timeout_ms });

        const first = try select.await();
        return switch (first) {
            .fetch => |outcome| blk: {
                cancelAndDrain(self.allocator, &select);
                break :blk try outcome;
            },
            .timeout => |outcome| {
                try outcome;
                cancelAndDrain(self.allocator, &select);
                return error.SidecarUnavailable;
            },
        };
    }
};

fn cloneOptions(allocator: std.mem.Allocator, options: Options) !Options {
    const args = try allocator.alloc([]const u8, options.server_args.len);
    for (options.server_args, 0..) |arg, index| {
        args[index] = try allocator.dupe(u8, arg);
    }
    return .{
        .supervisor_path = try allocator.dupe(u8, options.supervisor_path),
        .server_path = try allocator.dupe(u8, options.server_path),
        .model_path = try allocator.dupe(u8, options.model_path),
        .server_args = args,
        .startup_timeout_ms = options.startup_timeout_ms,
        .stop_grace_ms = options.stop_grace_ms,
        .request_timeout_ms = options.request_timeout_ms,
    };
}

fn validateOptions(options: Options) !void {
    if (options.supervisor_path.len == 0 or options.supervisor_path.len > 4096) return error.InvalidSidecarOptions;
    if (options.server_path.len == 0 or options.server_path.len > 4096) return error.InvalidSidecarOptions;
    if (options.model_path.len == 0 or options.model_path.len > 4096) return error.InvalidSidecarOptions;
    if (options.server_args.len > max_server_args) return error.InvalidSidecarOptions;
    if (options.startup_timeout_ms == 0 or options.stop_grace_ms == 0 or options.request_timeout_ms == 0) {
        return error.InvalidSidecarOptions;
    }
    for ([_][]const u8{ options.supervisor_path, options.server_path, options.model_path }) |path| {
        if (std.mem.indexOfScalar(u8, path, 0) != null) return error.InvalidSidecarOptions;
    }
}

/// Bind port 0 on loopback, take the assigned port, and release it. The
/// window before the server binds is small and the server fails loudly if it
/// loses the race.
fn pickPort(io: std.Io) !u16 {
    const address = try std.Io.net.IpAddress.parse("127.0.0.1", 0);
    var server = try address.listen(io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(io);
    return server.socket.address.getPort();
}

fn closeStdin(io: std.Io, child: *std.process.Child) void {
    if (child.stdin) |stdin| {
        stdin.close(io);
        child.stdin = null;
    }
}

fn sleepFor(io: std.Io, milliseconds: u32) std.Io.Cancelable!void {
    try io.sleep(.fromMilliseconds(milliseconds), .awake);
}

/// Wait up to `grace_ms` for the child to exit, then SIGKILL and reap. An
/// `initial_signal` sends a signal first (the supervisor uses SIGTERM on the
/// server group); `null` waits without signalling, which is what the parent
/// does after closing the supervisor's pipe.
///
/// Polling `waitpid` instead of racing `Child.wait` against a timer keeps the
/// escalation deterministic: the timer task in a `Select` can be starved by
/// the blocking wait, which leaves a process alive past its grace period with
/// no second signal. On Windows there is no graceful signal, so the process is
/// terminated directly.
pub fn terminate(
    io: std.Io,
    child: *std.process.Child,
    grace_ms: u32,
    group: bool,
    initial_signal: ?std.posix.SIG,
) void {
    if (child.id == null) return;
    if (builtin.os.tag == .windows) {
        child.kill(io);
        return;
    }

    const pid = child.id.?;
    if (initial_signal) |sig| signal(pid, group, sig);

    if (!waitForExit(io, pid, grace_ms)) {
        signal(pid, group, .KILL);
        _ = std.c.waitpid(pid, null, 0);
    }
    child.id = null;
}

/// Returns true once the child is reaped, false if it is still running when
/// the grace period ends. A wait error means there is nothing left to reap, so
/// it counts as exited.
fn waitForExit(io: std.Io, pid: std.posix.pid_t, grace_ms: u32) bool {
    var waited: u32 = 0;
    while (true) {
        const result = std.c.waitpid(pid, null, std.c.W.NOHANG);
        if (result == pid) return true;
        if (result < 0) return true;
        if (waited >= grace_ms) return false;
        const step = @min(@as(u32, 50), grace_ms - waited);
        io.sleep(.fromMilliseconds(step), .awake) catch return false;
        waited += step;
    }
}

fn signal(pid: std.posix.pid_t, group: bool, sig: std.posix.SIG) void {
    if (group) {
        std.posix.kill(-pid, sig) catch {};
    } else {
        std.posix.kill(pid, sig) catch {};
    }
}

fn cancelAndDrain(allocator: std.mem.Allocator, select: *std.Io.Select(FetchRace)) void {
    while (select.cancel()) |result| switch (result) {
        .fetch => |outcome| if (outcome) |body| allocator.free(body) else |_| {},
        .timeout => {},
    };
}

fn fetchOnce(
    io: std.Io,
    allocator: std.mem.Allocator,
    url: []const u8,
    method: std.http.Method,
    payload: ?[]const u8,
    headers: []const std.http.Header,
) anyerror![]u8 {
    var client = std.http.Client{ .allocator = allocator, .io = io };
    defer client.deinit();

    var response: std.Io.Writer.Allocating = .init(allocator);
    defer response.deinit();

    const result = client.fetch(.{
        .location = .{ .url = url },
        .method = method,
        .payload = payload,
        .extra_headers = headers,
        .response_writer = &response.writer,
    }) catch return error.SidecarUnavailable;
    if (result.status != .ok) return error.SidecarRequestRejected;
    if (response.writer.end > max_response_bytes) return error.SidecarRequestTooLarge;
    return response.toOwnedSlice();
}
