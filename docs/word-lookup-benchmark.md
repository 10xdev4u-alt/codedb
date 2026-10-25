# Word lookup scaling

Recorded 2026-10-25 at commit `92074c5` with the compiler pinned in
[`build.zig.zon`](../build.zig.zon).

The debug test suite used to assert one wall-clock bound for a word lookup.
That bound measured the host, not the algorithm: it failed 25 of 25 runs on
the machine below. The test now compares corpora of different sizes, and this
page records the curve the test protects.

## Reproduce

```bash
zig build bench-word -- --json
```

The binary is always built with `-Ofast`. Each point indexes a synthetic
corpus where every file contributes one unique symbol and one shared word,
then times a lookup of the last file's symbol and of the shared word. Five
in-process samples are sorted, and the median is the point.

The table below aggregates five separate invocations. p50 is the third of
five sorted run values; p95 is the maximum (nearest rank, n = 5).

## Environment

| Field | Value |
|---|---|
| CPU | AMD Ryzen 3 3250U with Radeon Graphics, 4 threads |
| RAM | 13.6 GiB |
| OS | Omarchy, Linux 7.2.8-9-omarchy, x86_64 |
| Compiler | Zig 0.17.0 |
| Build | `-Ofast`, `DebugAllocator` |
| Clock | monotonic |

## Results

Nanoseconds per lookup.

| Files | Unique p50 | Unique p95 | Shared p50 | Shared p95 | Unique hits | Shared hits |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 23 | 24 | 22 | 24 | 1 | 100 |
| 1,000 | 22 | 23 | 22 | 23 | 1 | 1,000 |
| 10,000 | 23 | 24 | 22 | 23 | 1 | 10,000 |

Across a 100x increase in corpus size, the unique-symbol lookup grows 1.0x
and the shared-word lookup stays at 22 ns. Both are hash probes; neither
walks the corpus.

## Scope

These numbers isolate the `WordIndex.search` probe. They exclude real
postings iteration, filesystem access, MCP framing, and cache misses on a
cold process. End-to-end latency belongs to the repo benchmark
(`zig build benchmark`) and the retrieval evaluation, not this page.

A regression that turns the probe into a linear scan over 2,000 files is
more than 20x slower than the 100-file corpus, so the test's 10x band fails.
Inserting a linear scan during review made the test fail.
