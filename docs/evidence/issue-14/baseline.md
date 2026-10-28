# Index and query baseline — issue #14

Recorded 2026-10-28 from commit `30ea92c844b9ba8dc9bf0bc0acc9ce5b9ceae30a`.

| | |
|---|---|
| Machine | x86_64 |
| CPU | AMD Ryzen 3 3250U with Radeon Graphics |
| Cores | 4 |
| Memory | 13.6 GiB |
| OS | Linux-7.2.8-9-omarchy-x86_64-with-glibc2.44 |
| Zig | 0.17.0 |
| Binary SHA-256 | `4f3caf58be5ee93c19e6a3f3cf0236adc3dc9ad08e51803ab0796c89f952fe44` |
| Command | `python3 scripts/baseline.py --binary zig-out/bin/benchmark --root . --runs 5 --iterations 100` |
| Samples | 1 warmup + 5 recorded runs × 100 iterations per query |

## Noise band

A rerun on the same CPU class is inside the band when its five-run medians match this baseline's: index within ±15%, query p50 within ±15% or 50.0 µs, query p95 within ±35% or 50.0 µs, and peak RSS within ±5%. The absolute floor keeps sub-50.0 µs dispatches from failing on timer noise. File count and per-query hit counts must match exactly. The baseline values below are medians across the 5 recorded runs.

Run-to-run spread on this machine: index 4.5% from the median, RSS 0.6%, query p50 0 of 70 values outside the band, query p95 1 of 70 outside. A single run can land outside the band while the machine's median is unchanged, so the acceptance test compares five-run medians, not individual runs.
  - `search:database` p95 run 4: 204.5 µs vs 151.5 µs median (35.1%).

## Index and memory

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | p50 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Index time | 1124.56 ms | 1045.73 ms | 1094.28 ms | 1076.31 ms | 1042.80 ms | 1076.31 ms | 1124.56 ms |
| Peak RSS | 177.0 MiB | 176.4 MiB | 176.9 MiB | 176.5 MiB | 177.9 MiB | 176.9 MiB | 177.9 MiB |
| Wall time | 1.47 s | 1.37 s | 1.43 s | 1.41 s | 1.37 s | 1.41 s | 1.47 s |

## Query latency

Median of the per-run percentiles. The range is the smallest to largest per-run value.

| Query | Kind | Hits | p50 | p95 | p50 range | p95 range |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `middleware` | search | 50 | 143.0 µs | 192.0 µs | 140.8 µs–154.8 µs | 163.3 µs–214.5 µs |
| `authentication` | search | 28 | 801.0 µs | 903.5 µs | 785.7 µs–829.0 µs | 836.6 µs–982.9 µs |
| `webhook` | search | 5 | 89.9 µs | 110.4 µs | 88.4 µs–95.0 µs | 99.1 µs–142.2 µs |
| `database` | search | 50 | 129.8 µs | 151.5 µs | 126.0 µs–145.0 µs | 144.8 µs–204.5 µs |
| `error` | search | 50 | 187.6 µs | 231.2 µs | 184.1 µs–201.6 µs | 215.6 µs–261.2 µs |
| `error` | cached | 50 | 15.8 µs | 25.5 µs | 15.1 µs–16.5 µs | 24.5 µs–29.2 µs |
| `request` | word | 1680 | 17.0 µs | 22.9 µs | 16.0 µs–17.2 µs | 19.8 µs–23.8 µs |
| `response` | word | 2307 | 18.6 µs | 24.4 µs | 18.4 µs–19.9 µs | 22.5 µs–25.5 µs |
| `config` | word | 2924 | 20.8 µs | 24.6 µs | 20.6 µs–23.5 µs | 24.1 µs–40.4 µs |
| `error` | word | 2924 | 21.1 µs | 25.7 µs | 21.1 µs–22.9 µs | 25.4 µs–28.7 µs |
| `init` | symbol | 35 | 44.2 µs | 57.9 µs | 42.7 µs–46.0 µs | 56.1 µs–75.1 µs |
| `main` | symbol | 47 | 49.5 µs | 66.7 µs | 48.1 µs–51.3 µs | 61.9 µs–81.7 µs |
| `handleRequest` | symbol | 0 | 60 ns | 61 ns | 50 ns–60 ns | 60 ns–61 ns |
| `render` | symbol | 15 | 16.4 µs | 29.5 µs | 16.1 µs–20.4 µs | 28.8 µs–32.3 µs |

## Reproduce

```bash
zig build benchmark-bin
python3 scripts/baseline.py --binary zig-out/bin/benchmark --root . --runs 5 --iterations 100
```

The benchmark scans the checkout in process and writes no snapshot. Search rows disable the result cache; the `cached` row measures a cache hit.

## Second machine

- [ ] Reproduced on a second machine: five-run medians inside the band on the same CPU class, or identical file and hit counts with that machine's latency and RSS recorded.

Pending. Run the command above on the second machine, then record its hardware, five-run medians, and file and hit counts in this file. Index time and RSS depend on the CPU and memory, so a machine of a different class records its own absolute numbers instead of matching this band.
