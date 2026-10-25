/// Synthetic word-index benchmark for the O(1) lookup claim.
///
/// Every file contributes one unique symbol and one shared word. As the file
/// count grows, a hash probe stays flat; a linear scan grows with the corpus.
/// The test suite asserts the ratio. This binary records the curve with five
/// samples per point.
///
/// Usage: zig build bench-word -- [--iterations N] [--json]
const std = @import("std");
const cio = @import("cio.zig");
const WordIndex = @import("index.zig").WordIndex;

const sizes = [_]usize{ 100, 1_000, 10_000 };
const sample_count = 5;

const Sample = struct {
    files: usize,
    unique_ns: u64,
    shared_ns: u64,
    unique_hits: usize,
    shared_hits: usize,
};

fn buildIndex(gpa: std.mem.Allocator, arena: std.mem.Allocator, files: usize) !WordIndex {
    var wi = WordIndex.init(gpa);
    errdefer wi.deinit();
    for (0..files) |i| {
        const name = try std.fmt.allocPrint(arena, "bench_{d}.zig", .{i});
        const content = try std.fmt.allocPrint(arena, "pub fn handle_{d}(ctx: *Context) void {{}}\nconst allocator = getDefaultAllocator();\n", .{i});
        try wi.indexFile(name, content);
    }
    return wi;
}

/// Fill `times` with per-call nanoseconds, then sort so p50 is one index.
fn lookupTimes(wi: *WordIndex, word: []const u8, iterations: usize, times: *[sample_count]u64) !void {
    for (times) |*slot| {
        var timer = try cio.Timer.start();
        for (0..iterations) |_| {
            std.mem.doNotOptimizeAway(wi.search(word));
        }
        slot.* = timer.read() / iterations;
    }
    std.mem.sort(u64, times, {}, std.sort.asc(u64));
}

fn measure(gpa: std.mem.Allocator, files: usize, iterations: usize) !Sample {
    var arena = std.heap.ArenaAllocator.init(gpa);
    defer arena.deinit();

    var wi = try buildIndex(gpa, arena.allocator(), files);
    defer wi.deinit();

    const tail = try std.fmt.allocPrint(arena.allocator(), "handle_{d}", .{files - 1});
    var unique_times: [sample_count]u64 = undefined;
    var shared_times: [sample_count]u64 = undefined;
    try lookupTimes(&wi, tail, iterations, &unique_times);
    try lookupTimes(&wi, "allocator", iterations, &shared_times);

    return .{
        .files = files,
        // The median sample is the reported point; the fastest sample would
        // hide a real regression behind one lucky run.
        .unique_ns = unique_times[sample_count / 2],
        .shared_ns = shared_times[sample_count / 2],
        .unique_hits = wi.search(tail).len,
        .shared_hits = wi.search("allocator").len,
    };
}

fn writeJson(samples: []const Sample) !void {
    var buf: [64 * 1024]u8 = undefined;
    var w = std.Io.Writer.fixed(&buf);
    try w.print(
        "{{\"benchmark\":\"word-lookup\",\"zig_version\":\"{s}\",\"clock\":\"monotonic\",\"samples\":[",
        .{@import("builtin").zig_version_string},
    );
    for (samples, 0..) |s, i| {
        if (i != 0) try w.writeAll(",");
        try w.print(
            "{{\"files\":{d},\"unique_ns\":{d},\"shared_ns\":{d},\"unique_hits\":{d},\"shared_hits\":{d}}}",
            .{ s.files, s.unique_ns, s.shared_ns, s.unique_hits, s.shared_hits },
        );
    }
    try w.writeAll("]}\n");
    try cio.File.stdout().writeAll(w.buffered());
}

fn writeHuman(samples: []const Sample) !void {
    var buf: [8 * 1024]u8 = undefined;
    var w = std.Io.Writer.fixed(&buf);
    try w.print("word lookup, median of {d} samples (ns/query)\n", .{sample_count});
    try w.print("  {s:>8}  {s:>10}  {s:>10}  {s:>11}  {s:>11}\n", .{ "files", "unique", "shared", "unique hits", "shared hits" });
    for (samples) |s| {
        try w.print("  {d:>8}  {d:>10}  {d:>10}  {d:>11}  {d:>11}\n", .{ s.files, s.unique_ns, s.shared_ns, s.unique_hits, s.shared_hits });
    }
    const first = samples[0];
    const last = samples[samples.len - 1];
    const growth = if (first.unique_ns == 0) 0.0 else @as(f64, @floatFromInt(last.unique_ns)) / @as(f64, @floatFromInt(first.unique_ns));
    try w.print("\nunique lookup growth {d:.1}x over {d}x files; shared lookup {d} -> {d} ns\n", .{
        growth, last.files / first.files, first.shared_ns, last.shared_ns,
    });
    try cio.File.stderr().writeAll(w.buffered());
}

pub fn main(init: std.process.Init.Minimal) !void {
    cio.setProcessArgs(cio.bootstrapArgs(init.args));

    var gpa: std.heap.DebugAllocator(.{}) = .init;
    defer _ = gpa.deinit();
    const gpa_alloc = gpa.allocator();

    const argv = try cio.argsAlloc(gpa_alloc);
    defer cio.argsFree(gpa_alloc, argv);

    var iterations: usize = 200_000;
    var json = false;
    var i: usize = 1;
    while (i < argv.len) : (i += 1) {
        if (std.mem.eql(u8, argv[i], "--iterations") and i + 1 < argv.len) {
            i += 1;
            iterations = try std.fmt.parseInt(usize, argv[i], 10);
        } else if (std.mem.eql(u8, argv[i], "--json")) {
            json = true;
        } else {
            std.debug.print("unknown argument: {s}\n", .{argv[i]});
            return error.InvalidArgument;
        }
    }
    if (iterations == 0) return error.InvalidArgument;

    var samples: [sizes.len]Sample = undefined;
    for (sizes, 0..) |files, index| {
        samples[index] = try measure(gpa_alloc, files, iterations);
    }

    if (json) {
        try writeJson(&samples);
    } else {
        try writeHuman(&samples);
    }
}
