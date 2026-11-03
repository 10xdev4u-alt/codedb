//! Test helper for the managed sidecar (#26).
//!
//! Two roles, one executable so `build.zig` installs a single dependency:
//!
//!   serve  — a stand-in for llama-server: `/health` and an
//!            OpenAI-compatible `/v1/embeddings`, with optional flags that
//!            simulate a crash or a server that ignores SIGTERM.
//!   parent — starts a real sidecar, prints `ready`, and sleeps. The test
//!            SIGKILLs it to prove the server does not outlive its parent.

const std = @import("std");
const builtin = @import("builtin");
const sidecar = @import("sidecar.zig");

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const allocator = init.gpa;

    var args = std.process.Args.Iterator.initAllocator(init.minimal.args, allocator) catch {
        std.process.exit(2);
    };
    defer args.deinit();
    const self_path = args.next() orelse std.process.exit(2);
    const mode = args.next() orelse std.process.exit(2);

    if (std.mem.eql(u8, mode, "serve")) return serve(io, allocator, &args);
    if (std.mem.eql(u8, mode, "parent")) return parent(io, allocator, self_path, &args);
    std.process.exit(2);
}

const ServeOptions = struct {
    port: u16 = 0,
    pid_file: ?[]const u8 = null,
    ignore_term: bool = false,
    exit_after_ms: ?u32 = null,
};

fn serve(io: std.Io, allocator: std.mem.Allocator, args: *std.process.Args.Iterator) !void {
    var options = ServeOptions{};
    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--port")) {
            const value = args.next() orelse return error.MissingValue;
            options.port = try std.fmt.parseInt(u16, value, 10);
        } else if (std.mem.eql(u8, arg, "--pid-file")) {
            options.pid_file = args.next() orelse return error.MissingValue;
        } else if (std.mem.eql(u8, arg, "--ignore-term")) {
            options.ignore_term = true;
        } else if (std.mem.eql(u8, arg, "--exit-after-ms")) {
            const value = args.next() orelse return error.MissingValue;
            options.exit_after_ms = try std.fmt.parseInt(u32, value, 10);
        } else if (std.mem.eql(u8, arg, "--model")) {
            // Shared sidecar flag; the stub has no model.
            _ = args.next() orelse return error.MissingValue;
        }
    }

    if (options.pid_file) |path| try writePidFile(io, allocator, path);
    if (options.ignore_term) ignoreTerm();
    if (options.exit_after_ms) |milliseconds| {
        try io.sleep(.fromMilliseconds(milliseconds), .awake);
        std.process.exit(0);
    }
    if (options.port == 0) return error.MissingPort;

    const address = try std.Io.net.IpAddress.parse("127.0.0.1", options.port);
    var server = try address.listen(io, .{ .reuse_address = true, .mode = .stream, .protocol = .tcp });
    defer server.deinit(io);

    while (true) {
        const stream = server.accept(io) catch continue;
        handleConnection(io, allocator, stream) catch {};
        stream.close(io);
    }
}

fn handleConnection(io: std.Io, allocator: std.mem.Allocator, stream: std.Io.net.Stream) !void {
    var request_buffer: [16 * 1024]u8 = undefined;
    var length: usize = 0;
    while (length < request_buffer.len) {
        var iovec = [1][]u8{request_buffer[length..]};
        const read = stream.readWithControl(io, &iovec, &.{}) catch return;
        if (read.data_len == 0) return;
        length += read.data_len;
        if (std.mem.indexOf(u8, request_buffer[0..length], "\r\n\r\n") != null) break;
    }
    const head = request_buffer[0..length];

    const request_line_end = std.mem.indexOf(u8, head, "\r\n") orelse return;
    var request_line = std.mem.splitScalar(u8, head[0..request_line_end], ' ');
    const method = request_line.next() orelse return;
    const path = request_line.next() orelse return;

    if (std.mem.eql(u8, method, "POST")) {
        const content_length = headerValue(head, "content-length") orelse "0";
        const expected = std.fmt.parseInt(usize, content_length, 10) catch 0;
        const body_start = (std.mem.indexOf(u8, head, "\r\n\r\n") orelse return) + 4;
        while (length - body_start < expected and length < request_buffer.len) {
            var iovec = [1][]u8{request_buffer[length..]};
            const read = stream.readWithControl(io, &iovec, &.{}) catch return;
            if (read.data_len == 0) break;
            length += read.data_len;
        }
        const body = request_buffer[body_start..@min(length, body_start + expected)];

        if (std.mem.eql(u8, path, "/v1/embeddings")) {
            const response = try embeddingsResponse(allocator, body);
            defer allocator.free(response);
            try respond(io, stream, "200 OK", response);
            return;
        }
    }

    if (std.mem.eql(u8, path, "/health")) {
        try respond(io, stream, "200 OK", "{\"status\":\"ok\"}");
        return;
    }
    try respond(io, stream, "404 Not Found", "{\"error\":\"not found\"}");
}

fn embeddingsResponse(allocator: std.mem.Allocator, body: []const u8) ![]u8 {
    var count: usize = 1;
    if (std.json.parseFromSlice(std.json.Value, allocator, body, .{})) |parsed| {
        defer parsed.deinit();
        if (parsed.value == .object) {
            if (parsed.value.object.get("input")) |input| {
                if (input == .array and input.array.items.len > 0) count = input.array.items.len;
            }
        }
    } else |_| {}

    var out: std.Io.Writer.Allocating = .init(allocator);
    defer out.deinit();
    try out.writer.writeAll("{\"object\":\"list\",\"model\":\"stub\",\"data\":[");
    for (0..count) |index| {
        if (index != 0) try out.writer.writeByte(',');
        try out.writer.print(
            "{{\"object\":\"embedding\",\"index\":{d},\"embedding\":[0.125,0.25,0.5,1.0]}}",
            .{index},
        );
    }
    try out.writer.writeAll("],\"usage\":{\"prompt_tokens\":1,\"total_tokens\":1}}");
    return out.toOwnedSlice();
}

fn respond(io: std.Io, stream: std.Io.net.Stream, status: []const u8, body: []const u8) !void {
    var head_buffer: [256]u8 = undefined;
    const head = try std.fmt.bufPrint(
        &head_buffer,
        "HTTP/1.1 {s}\r\nContent-Type: application/json\r\nContent-Length: {d}\r\nConnection: close\r\n\r\n",
        .{ status, body.len },
    );
    var write_buffer: [4096]u8 = undefined;
    var writer = stream.writer(io, &write_buffer);
    try writer.interface.writeAll(head);
    try writer.interface.writeAll(body);
    try writer.interface.flush();
}

fn headerValue(head: []const u8, name: []const u8) ?[]const u8 {
    var lines = std.mem.splitSequence(u8, head, "\r\n");
    while (lines.next()) |line| {
        const colon = std.mem.indexOfScalar(u8, line, ':') orelse continue;
        if (std.ascii.eqlIgnoreCase(std.mem.trim(u8, line[0..colon], " \t"), name)) {
            return std.mem.trim(u8, line[colon + 1 ..], " \t");
        }
    }
    return null;
}

fn writePidFile(io: std.Io, allocator: std.mem.Allocator, path: []const u8) !void {
    const file = try std.Io.Dir.createFileAbsolute(io, path, .{ .truncate = true });
    defer file.close(io);
    const text = try std.fmt.allocPrint(allocator, "{d}\n", .{currentPid()});
    defer allocator.free(text);
    try file.writePositionalAll(io, text, 0);
}

fn currentPid() u32 {
    return switch (builtin.os.tag) {
        .windows => std.os.windows.GetCurrentProcessId(),
        else => @intCast(std.c.getpid()),
    };
}

fn ignoreTerm() void {
    if (builtin.os.tag == .windows) return;
    var action: std.posix.Sigaction = .{
        .handler = .{ .handler = std.posix.SIG.IGN },
        .mask = std.posix.sigemptyset(),
        .flags = 0,
    };
    std.posix.sigaction(std.posix.SIG.TERM, &action, null);
}

/// Start a real sidecar, announce readiness on stdout, then sleep until the
/// test kills this process.
fn parent(
    io: std.Io,
    allocator: std.mem.Allocator,
    self_path: []const u8,
    args: *std.process.Args.Iterator,
) !void {
    var supervisor_path: ?[]const u8 = null;
    var model_path: ?[]const u8 = null;
    var pid_file: ?[]const u8 = null;
    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "--supervisor")) {
            supervisor_path = args.next() orelse return error.MissingValue;
        } else if (std.mem.eql(u8, arg, "--model")) {
            model_path = args.next() orelse return error.MissingValue;
        } else if (std.mem.eql(u8, arg, "--pid-file")) {
            pid_file = args.next() orelse return error.MissingValue;
        }
    }

    const server_args = [_][]const u8{ "serve", "--pid-file", pid_file orelse return error.MissingValue };
    var instance = try sidecar.Sidecar.start(io, allocator, .{
        .supervisor_path = supervisor_path orelse return error.MissingValue,
        .server_path = self_path,
        .model_path = model_path orelse return error.MissingValue,
        .server_args = &server_args,
    });
    _ = &instance;

    const stdout = std.Io.File.stdout();
    stdout.writeStreamingAll(io, "ready\n") catch {};
    while (true) {
        try io.sleep(.fromMilliseconds(1000), .awake);
    }
}
