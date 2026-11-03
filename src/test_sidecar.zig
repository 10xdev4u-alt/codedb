//! Sidecar lifecycle tests (#26). They spawn the real supervisor and a stub
//! server, so they prove the process contract instead of mocking it.

const std = @import("std");
const builtin = @import("builtin");
const testing = std.testing;
const io = testing.io;
const cio = @import("cio.zig");
const sidecar = @import("sidecar.zig");
const build_options = @import("build_options");

fn helperPath() []const u8 {
    return build_options.sidecar_helper;
}

fn supervisorPath() []const u8 {
    return build_options.sidecar_supervisor;
}

fn tmpPath(tmp: *std.testing.TmpDir, allocator: std.mem.Allocator, name: []const u8) ![]u8 {
    var buffer: [std.fs.max_path_bytes]u8 = undefined;
    const length = try tmp.dir.realPath(io, &buffer);
    return std.fmt.allocPrint(allocator, "{s}/{s}", .{ buffer[0..length], name });
}

fn readPid(path: []const u8) !u32 {
    const file = try std.Io.Dir.openFileAbsolute(io, path, .{});
    defer file.close(io);
    var buffer: [32]u8 = undefined;
    const length = try file.readPositionalAll(io, &buffer, 0);
    return std.fmt.parseInt(u32, std.mem.trim(u8, buffer[0..length], " \r\n"), 10);
}

fn waitForPid(path: []const u8, timeout_ms: u32) !u32 {
    const deadline = cio.milliTimestamp() + @as(i64, timeout_ms);
    while (cio.milliTimestamp() < deadline) {
        if (readPid(path)) |pid| {
            if (pid != 0) return pid;
        } else |_| {}
        try io.sleep(.fromMilliseconds(50), .awake);
    }
    return error.PidFileTimeout;
}

fn processAlive(pid: u32) bool {
    if (comptime builtin.os.tag == .windows) return false;
    return std.c.kill(@intCast(pid), @fromBackingInt(@intCast(0))) == 0;
}

fn waitForProcessGone(pid: u32, timeout_ms: u32) !bool {
    const deadline = cio.milliTimestamp() + @as(i64, timeout_ms);
    while (cio.milliTimestamp() < deadline) {
        if (!processAlive(pid)) return true;
        try io.sleep(.fromMilliseconds(50), .awake);
    }
    return !processAlive(pid);
}

fn killPid(pid: u32) void {
    if (comptime builtin.os.tag == .windows) return;
    std.posix.kill(@intCast(pid), .KILL) catch {};
}

fn startSidecar(
    allocator: std.mem.Allocator,
    pid_path: []const u8,
    extra_args: []const []const u8,
) !sidecar.Sidecar {
    var args: [8][]const u8 = undefined;
    args[0] = "serve";
    args[1] = "--pid-file";
    args[2] = pid_path;
    var count: usize = 3;
    for (extra_args) |arg| {
        args[count] = arg;
        count += 1;
    }
    return sidecar.Sidecar.start(io, allocator, .{
        .supervisor_path = supervisorPath(),
        .server_path = helperPath(),
        .model_path = "unused-model.gguf",
        .server_args = args[0..count],
        .startup_timeout_ms = 10_000,
        .stop_grace_ms = 2_000,
        .request_timeout_ms = 5_000,
    });
}

test "sidecar: starts, reports health, embeds, and stops the server" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const pid_path = try tmpPath(&tmp, testing.allocator, "server.pid");
    defer testing.allocator.free(pid_path);

    var instance = try startSidecar(testing.allocator, pid_path, &.{});
    defer instance.deinit();

    const server_pid = try waitForPid(pid_path, 5_000);
    try testing.expect(processAlive(server_pid));
    try testing.expect(try instance.health());

    const result = try instance.embed(&.{ "first", "second" });
    defer testing.allocator.free(result.body);
    try testing.expect(!result.restarted);
    try testing.expect(std.mem.indexOf(u8, result.body, "\"embedding\"") != null);
    try testing.expect(std.mem.indexOf(u8, result.body, "\"index\":1") != null);

    instance.stop();
    try testing.expect(try waitForProcessGone(server_pid, 5_000));
}

test "sidecar: a killed server is restarted once and the retry is reported" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const pid_path = try tmpPath(&tmp, testing.allocator, "server.pid");
    defer testing.allocator.free(pid_path);

    var instance = try startSidecar(testing.allocator, pid_path, &.{});
    defer instance.deinit();

    const first_pid = try waitForPid(pid_path, 5_000);
    killPid(first_pid);

    // The killed server is a zombie until its supervisor reaps it, which
    // happens when the failed request triggers the restart. Do not wait for
    // the pid to vanish before the request; on Linux a zombie still answers
    // `kill(pid, 0)`.
    const result = try instance.embed(&.{"code"});
    defer testing.allocator.free(result.body);
    try testing.expect(result.restarted);
    try testing.expect(std.mem.indexOf(u8, result.body, "\"embedding\"") != null);
    try testing.expectEqual(@as(u32, 1), instance.restarts);
    try testing.expect(try waitForProcessGone(first_pid, 5_000));

    const second_pid = try waitForPid(pid_path, 5_000);
    try testing.expect(second_pid != first_pid);
    try testing.expect(processAlive(second_pid));
}

test "sidecar: a server that exits before health fails with a typed error" {
    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const pid_path = try tmpPath(&tmp, testing.allocator, "server.pid");
    defer testing.allocator.free(pid_path);

    try testing.expectError(
        error.SidecarStartTimeout,
        sidecar.Sidecar.start(io, testing.allocator, .{
            .supervisor_path = supervisorPath(),
            .server_path = helperPath(),
            .model_path = "unused-model.gguf",
            .server_args = &.{ "serve", "--pid-file", pid_path, "--exit-after-ms", "50" },
            .startup_timeout_ms = 500,
            .stop_grace_ms = 500,
            .request_timeout_ms = 500,
        }),
    );
}

test "sidecar: stop escalates to SIGKILL when the server ignores SIGTERM" {
    if (comptime builtin.os.tag == .windows) return error.SkipZigTest;

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const pid_path = try tmpPath(&tmp, testing.allocator, "server.pid");
    defer testing.allocator.free(pid_path);

    var instance = try startSidecar(testing.allocator, pid_path, &.{"--ignore-term"});
    defer instance.deinit();

    const server_pid = try waitForPid(pid_path, 5_000);
    try testing.expect(processAlive(server_pid));

    instance.stop();
    try testing.expect(try waitForProcessGone(server_pid, 5_000));
}

test "sidecar: no server survives SIGKILL of the parent" {
    if (comptime builtin.os.tag == .windows) return error.SkipZigTest;

    var tmp = testing.tmpDir(.{});
    defer tmp.cleanup();
    const pid_path = try tmpPath(&tmp, testing.allocator, "server.pid");
    defer testing.allocator.free(pid_path);

    var parent = try std.process.spawn(io, .{
        .argv = &.{
            helperPath(),
            "parent",
            "--supervisor",
            supervisorPath(),
            "--model",
            "unused-model.gguf",
            "--pid-file",
            pid_path,
        },
        .stdin = .ignore,
        .stdout = .ignore,
        .stderr = .inherit,
    });
    defer {
        if (parent.id != null) {
            parent.kill(io);
            _ = parent.wait(io) catch {};
        }
    }

    const server_pid = try waitForPid(pid_path, 10_000);
    try testing.expect(processAlive(server_pid));

    std.posix.kill(parent.id.?, .KILL) catch {};
    _ = try parent.wait(io);

    try testing.expect(try waitForProcessGone(server_pid, 5_000));
}
