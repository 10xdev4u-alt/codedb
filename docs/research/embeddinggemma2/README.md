# EmbeddingGemma 2 research dossier

Snapshot date: 2026-10-18. Audited and re-verified: 2026-10-23.

This directory holds the research behind milestones M2 and M3: the model facts, the provider landscape, the community evidence, and the verification scripts that keep the claims honest. It is curated for the product repository, not a dump of the research workspace.

## Contents

| Path | What it is |
|---|---|
| `EMBEDDINGGEMMA2_REPORT.md` | Full report, 40 sources, text and code benchmarks, providers, community projects |
| `AUDIT_2026-10-23.md` | Every correction from the audit, with severity and evidence |
| `verification/sources_2026-10-23.tsv` | Dated snapshot of 49 cited links |
| `verify_sources.py` | Rechecks the cited links. 47 resolve, 2 return HTTP 401 |
| `github_sweep/` | Manifest of 1,073 unique repositories, with a script that recomputes the count |
| `providers/` | Provider cards for llama.cpp, LiteRT-LM, MLX, Core ML, and community ports |

## Reproduce

```bash
python3 verify_sources.py --offline
python3 github_sweep/verify_sweep.py
```

The first command compares the report against the dated link snapshot. The second recomputes the sweep: 264 repositories from name and description searches, 883 from code hits, 74 overlaps, 1,073 unique, and 2,576 code-hit rows.

## What is not here

Raw HTML, search JSON, and the captured WebGPU bundle stay in the research workspace. The report cites them as "Local file" for provenance. Each citation also carries a public URL, which is the reproducible route. No product build step depends on those captures.

## Scope for this product

The build uses the text-only path: 270M text parameters, 768 native dimensions with MRL to 512, 256, and 128, 8,192 usable tokens, and a 309.9 MB Q8_0 GGUF. Vision and audio are out of scope. The model card reports code MTEB 78.68 against 68.76 for v1; the 128-question suite in `evals/` decides whether that advantage survives this corpus.

The licensing question is open until #85 is closed: the model card says Apache-2.0, and the weights have to be cleared for redistribution before the artifact is published.
