# GitHub Mention Sweep — 2026-10-18

This sweep was run through the authenticated GitHub CLI. It searched repository names, descriptions, READMEs, and code. No repositories were cloned and no model or repository artifacts were downloaded.

## Search Queries

Repository search used:

- `embeddinggemma2`
- `embeddinggemma 2`
- `embedding gemma 2`
- `embeddinggemma2 in:readme`

Code search used:

- `embeddinggemma2`
- `embeddinggemma-2`
- `"embeddinggemma-2"`
- `embeddinggemma 2`
- `embedding gemma 2`

## Counts

| Metric | Count |
|---|---:|
| Repository-mention query rows | 26 + 49 + 95 + 191 |
| Unique repositories in repo-name/description/readme union | 264 |
| Unique repositories from code hits | 883 |
| Full unique union | 1,073 |
| Metadata failures | 0 |

The five code queries collectively returned two 1,000-result caps. This means GitHub's legacy code-search index contains at least that many matching files; the sweep should be read as a large representative maximum-relevance sample, not a claim that GitHub contains exactly N matching files.

## Files

- `all_mentioning_repos.txt`: deduplicated union of repository and code hits.
- `all_repos_metadata.tsv`: sorted metadata for every repo in the union.
- `code_hits_all.tsv`: deduplicated code hit paths and URLs.
- `mentioned_repos_all.txt`: unique repo-name/description/readme hits.
- `code_hit_repos_all.txt`: unique repos from code mentions.
- `repos_*.tsv`: raw repo-search variants.
- `code_*.tsv`: raw code-search variants.

The repo metadata sorting is descending by stars. File format is TSV: `full_name, stars, forks, language, license, created_date, pushed_date, description, URL`.

## High-Level Shape

These are approximate string-derived categories over the 1,073-repo union, useful for scale rather than a strict taxonomy:

| Theme | Matching rows |
|---|---:|
| Search-oriented metadata or code | 165 |
| macOS-related metadata | 76 |
| Windows-related metadata | 36 |
| Android/iOS-related metadata | 30 |
| ASR/transcription/speech mentions | 51 |
| NPU/ANE/accelerator mentions | 91 |
| DigUp references anywhere in the union | 23 |
| Spotlight references anywhere in the union | 7 |
| Repos declaring Rust as their primary language | 69 |
| Repos declaring Swift as their primary language | 43 |
| Repos declaring C/C++/C# as primary language | 98 |

This is a wider ecosystem than the launch-week projects. It includes major inference servers adding EG2, native Mac/Windows/Linux search apps, Flutter/C#/.NET ports, agent memory systems, RAG stacks, video pipelines, browser/SQLite/WASM search, code search, and speech-to-text experiments.

## Notable Projects

These are not a ranking; they show the range found in the sweep:

- [ARahim3/DigUp](https://github.com/ARahim3/DigUp): 4,534 stars. Multimodal local search on Mac/Windows/Linux.
- [The-Vibe-Company/quivr](https://github.com/The-Vibe-Company/quivr): 39,598 stars. EG2-backed content-stream search.
- [qnguyen3/QUAN-Transcribe](https://github.com/qnguyen3/QUAN-Transcribe): fast Vietnamese speech recognition using EG2's audio encoder.
- [tc3oliver/embed2asr](https://github.com/tc3oliver/embed2asr): frozen EG2 audio encoder plus a 9.66M-parameter GRU-CTC reader.
- [DenisovAV/flutter_edge_ai](https://github.com/DenisovAV/flutter_edge_ai): 641 stars. Flutter multimodal embeddings/RAG/speech on Android, iOS, web, desktop.
- [zhongkaifu/TensorSharp](https://github.com/zhongkaifu/TensorSharp): 592 stars. Native .NET engine with iPhone app and GPU support.
- [FluidInference/FluidUse](https://github.com/FluidInference/FluidUse): 520 stars. Apple Silicon computer-use stack using typed decisions.
- [JimLiu/baocut](https://github.com/JimLiu/baocut): 1,046 stars. AI video editing with transcription/subtitling/translation.
- [antflydb/antfly](https://github.com/antflydb/antfly): EG2-backed multimodal search.
- [ml-explore/mlx-swift-lm](https://github.com/ml-explore/mlx-swift-lm): native Swift MLX model implementation.
- [curiosity-ai/sentence-transformers-sharp](https://github.com/curiosity-ai/sentence-transformers-sharp): full C# implementation including audio/vision paths.
- [google-ai-edge/litert-samples](https://github.com/google-ai-edge/litert-samples) and [google-ai-edge/mediapipe-samples](https://github.com/google-ai-edge/mediapipe-samples): official edge integration examples.
- [lattifai/awesome-EmbeddingGemma](https://github.com/lattifai/awesome-EmbeddingGemma): curated bilingual resource list.
- [misterekkk/lantern](https://github.com/misterekkk/lantern): lightweight macOS Spotlight-style semantic search.
- [KB01111/WinSearch](https://github.com/KB01111/WinSearch): Windows 11 multimodal launcher.
- [xafold/SpotLite](https://github.com/xafold/SpotLite): Linux Spotlight-style GPU search.
- [thakurious/trowel](https://github.com/thakurious/trowel): Linux/Omarchy DigUp-style Rust/QML port.
- [rabimba/Prism](https://github.com/rabimba/Prism): cross-platform Linux/macOS multimodal search with ASR.
