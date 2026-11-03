//! `codedb-sidecar` — lifetime guard for the local embedding server (#26).
//!
//! Usage: `codedb-sidecar -- <server> [args...]`
//!
//! The supervisor owns the server process and blocks on its own stdin. The
//! parent keeps the write end open for the whole session; when the parent
//! exits or is killed, the pipe closes, the supervisor wakes on EOF,
//! terminates the server process group, and exits. The server is started in
//! its own group so one signal reaches every child it may have spawned.
//!
//! This process deliberately does no health checking or restarting. The
//! parent detects a dead server through a failed request and restarts the
//! whole sidecar once.

const std = @import("std");
const builtin = @import("builtin");
const sidecar = @import("sidecar.zig");

pub fn main(init: std.process.Init) !void {
    const io = init.io;
    const allocator = init.gpa;

    var args = std.process.Args.Iterator.initAllocator(init.minimal.args, allocator) catch {
        return fail(io, "could not read arguments");
    };
    defer args.deinit();
    _ = args.next();

    const separator = args.next() orelse return fail(io, "missing `--` and server command");
    if (!std.mem.eql(u8, separator, "--")) return fail(io, "expected `--` before the server command");

    var server_argv: [64][]const u8 = undefined;
    var count: usize = 0;
    while (args.next()) |arg| {
        if (count == server_argv.len) return fail(io, "too many server arguments");
        server_argv[count] = arg;
        count += 1;
    }
    if (count == 0) return fail(io, "missing server command");

    // The parent stops this process by closing the pipe, so the supervisor
    // must survive a terminal signal long enough to clean up. Install the
    // handlers only after the server is spawned: signal dispositions are
    // inherited across exec, and a server that ignores SIGTERM cannot be
    // stopped gracefully.
    var child = std.process.spawn(io, .{
        .argv = server_argv[0..count],
        .stdin = .ignore,
        .stdout = .inherit,
        .stderr = .inherit,
        // A new process group lets the supervisor take down any helper the
        // server forks. Windows has no process groups here; the pipe still
        // covers parent death, and `kill` covers a direct stop.
        .pgid = if (builtin.os.tag == .windows) null else 0,
    }) catch return fail(io, "could not start the embedding server");

    ignoreStopSignals();

    waitForParentExit(io);

    // The parent's grace period is longer than this one, so the supervisor
    // finishes its own escalation before the parent gives up on it.
    sidecar.terminate(io, &child, 1_000, true, .TERM);
    std.process.exit(0);
}

/// Block until the parent closes the pipe. Any read error is treated as EOF:
/// losing the parent is the only reason this process should stop.
fn waitForParentExit(io: std.Io) void {
    const stdin = std.Io.File.stdin();
    var buffer: [256]u8 = undefined;
    while (true) {
        var iovec = [1][]u8{buffer[0..]};
        _ = stdin.readStreaming(io, &iovec) catch return;
    }
}

fn ignoreStopSignals() void {
    if (builtin.os.tag == .windows) return;
    var action: std.posix.Sigaction = .{
        .handler = .{ .handler = std.posix.SIG.IGN },
        .mask = std.posix.sigemptyset(),
        .flags = 0,
    };
    std.posix.sigaction(std.posix.SIG.TERM, &action, null);
    std.posix.sigaction(std.posix.SIG.INT, &action, null);
}

fn fail(io: std.Io, message: []const u8) noreturn {
    var buffer: [256]u8 = undefined;
    const text = std.fmt.bufPrint(&buffer, "codedb-sidecar: {s}\n", .{message}) catch "codedb-sidecar: fatal error\n";
    std.Io.File.stderr().writeStreamingAll(io, text) catch {};
    std.process.exit(2);
}
