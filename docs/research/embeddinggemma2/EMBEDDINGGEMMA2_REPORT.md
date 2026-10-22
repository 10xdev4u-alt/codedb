# EmbeddingGemma 2: The Full Community Report

Snapshot date: 2026-10-18. Re-verified: 2026-10-23 (`verification/sources_2026-10-23.tsv`, produced by `verify_sources.py`). This report is built from the official Hugging Face model files, provider cards, GitHub repositories, Hugging Face discussions, HN threads, Google launch material, and local clones. X/Reddit scraping was mostly unavailable, so the strongest social evidence here is HN and Hugging Face. Source IDs map to the [source table](#sources).

Star and download counts below are a dated snapshot, not live values. Where the 2026-10-23 recheck found a different number, the corrected value is used; table headers and inline dates say which snapshot they belong to. What the report cannot support is listed in [What This Report Does Not Prove](#what-this-report-does-not-prove).

> Curated import: the raw HTML and search JSON captures stay in the research workspace. "Local file" entries record provenance; the public URL beside each citation is the reproducible route. `verify_sources.py` and `github_sweep/verify_sweep.py` recheck the citations and the sweep counts.

## TL;DR

EmbeddingGemma 2 is Google's 740M multimodal embedding model: text, code, image, video, and audio all enter one 768-dimensional retrieval space. It is Apache-2.0, built on Gemma 4, and can run through llama.cpp, LiteRT-LM, Core ML, ONNX/WebGPU, MLX, vLLM, Rust, C, and NPU-specific stacks [S1](#s1) [S4](#s4). The text benchmark is essentially flat versus v1 (MTEB multilingual 61.36 versus 61.15), but code retrieval jumps from 68.76 to 78.68 and the headline upgrade is a shared media embedding space [S1](#s1) [S5](#s5).

The community response was disproportionate to the model size. The standout is **DigUp**: a macOS Spotlight replacement that indexes photos, PDFs, recordings, video, documents, and code by meaning. It uses EG2 through llama.cpp/Metal or Vulkan, stores SQLite vectors locally, adds exact-word boosts and a separate `code:` index, and sits at 5,500 stars as of 2026-10-23. Its Windows/Linux beta is already live [S6](#s6).

The second breakout is ASR. By freezing or lightly adapting EG2's audio tower and adding tiny CTC/RNN-T readers, people turned a "300M for ears" model into surprisingly fast speech recognition: QUAN-Transcribe reports 6.87% average WER and about 3,713× real time on H100 [S7](#s7); eg2.haku.sh reports one hour of audio transcribed in about 13 seconds on an M3 MacBook Air [S8](#s8); a Turkish CTC reader was trained on an M4 Pro [S9](#s9); and an African-speech LoRA reports Recall@1 improving from 0.938 to 0.997 [S10](#s10).

## What It Is

| Fact | Value |
|---|---:|
| Developer | Google DeepMind [S1](#s1) |
| License | Apache 2.0 [S1](#s1) |
| Release / model visibility | 2026-10-06; repo created 2026-09-14 [S3](#s3) |
| Base | Gemma 4 [S1](#s1) |
| Total parameters | 740M [S1](#s1) [S3](#s3) |
| Text parameters | 270M total; about 130M transformer plus about 140M embedding table [S1](#s1) [S5](#s5) |
| Vision parameters | 170M [S5](#s5) |
| Audio parameters | 300M [S5](#s5) |
| Dimensions | 768 / 512 / 256 / 128 via MRL truncation [S1](#s1) |
| Context | 8,192 tokens of usable input [S1](#s1); `max_position_embeddings` in the config is 262,144 [S2](#s2) |
| Vocabulary | 262,144 tokens [S2](#s2) |
| Layers | 24 [S2](#s2) |
| Hidden size | 512 [S2](#s2) |
| FFN intermediate size | 2,048 [S2](#s2) |
| Pooling / projection | Mean pooling then a 512→768 projection [S1](#s1) [S2](#s2) |

EG2's useful trick is one shared vector space. Search results can match a mixed text/image/audio/video collection, but prefixes and document formatting still matter [S1](#s1).

## Usage and Prompt Shape

Use these task prefixes for queries [S1](#s1):

```text
task: search result | query: ...
task: question answering | query: ...
task: fact checking | query: ...
task: code retrieval | query: ...
task: classification | query: ...
task: clustering | query: ...
task: sentence similarity | query: ...
```

For documents, use [S1](#s1):

```text
title: {title} | text: {content}
title: none | text: {content}
```

Media inputs use placeholders [S1](#s1):

```text
<start_of_image>...<end_of_image>
<start_of_video>...<end_of_video>
<start_of_audio>...<end_of_audio>
```

Practical budgets from the model card [S1](#s1):

- Image: about 280 tokens.
- Video: about 140 tokens/frame, 1 fps.
- Audio: about 25 tokens/sec, mono, 16 kHz.
- Audio maximum: roughly 5.5 minutes per input.
- Vision soft-token range: 70–1,120.

## Dimensions, Precision, and Loading

- MRL sizes: 768, 512, 256, and 128 [S1](#s1).
- Near-lossless cutoff: about 256d for text.
- 128d remains usable for text, but multimodal retrieval degrades badly at that size.
- fp16 is explicitly forbidden because it can produce NaNs or silent degradation; use bf16 or fp32 [S1](#s1).
- Selective loading is supported: text-only is about 270M parameters; text+vision about 440M; text+audio about 570M [S1](#s1).
- Pixel 11 Pro RAM estimates from Google: about 191 MB text-only and about 567 MB fully quantized [S11](#s11).

## Official And Upstream Benchmarks

Benchmarks below are from the model card's 768d comparison unless noted [S1](#s1).

| Benchmark | EG2 | EG1 | Δ |
|---|---:|---:|---:|
| MTEB multilingual | 61.36 | 61.15 | +0.21 |
| MTEB code | **78.68** | 68.76 | **+9.92** |
| MIEB lite | 64.64 | — | — |
| MMEB v2 image | 57.28 | — | — |
| MMEB v2 visual docs | 67.84 | — | — |
| MMEB v2 video | 50.67 | — | — |
| MSEB | 69.54 | — | — |
| MAEB | 49.39 | — | — |

The biggest non-multimodal gain is code. The flat text score was confirmed in a Hugging Face discussion by a Google staff member [S5](#s5). Training-data cutoff is January 2025 [S1](#s1).

Two config discrepancies are worth knowing. First, the model card's overview table lists a 1,024-token sliding window, while `hf_config.json` contains `sliding_window: 512` [S1](#s1) [S2](#s2). Second, the card documents an 8,192-token usable context, while the same config sets `max_position_embeddings: 262144` [S1](#s1) [S2](#s2). The 8K figure is the product promise and the budget the provider cards are written against; the larger config value is the positional capacity, not a promise that quality holds there. Treat 8,192 as the number to design against, and test the local runtime if exact window behavior matters.

## Runtime Ecosystem

| Runtime | State | Why it matters |
|---|---|---|
| llama.cpp | Native text/vision/audio via PR #30054; official and Unsloth GGUFs | Main engine behind DigUp; broad Apple Metal/Vulkan/CUDA coverage [S4](#s4) [S12](#s12) [S13](#s13) |
| LiteRT-LM | QAT INT4/INT8/INT2 bundles at 165/388/485 MB | Cross-device mobile/edge path with TPU/GPU/NPU/CPU and WASM targets [S14](#s14) |
| Core ML | FluidInference port | Apple ANE path; text 100% ANE; audio/image GPU; fp16 RMSNorm workaround retains cosine 0.9996 [S15](#s15) |
| ONNX + Transformers.js | onnx-community port; Transformers.js 4.3.1 | Browser and JS stack; WebGPU demo uses Q4 ONNX [S16](#s16) |
| WebGPU | `embeddinggemma-2-webgpu` demo | In-browser semantic image/audio/video search [S17](#s17) |
| MLX | Native MLX-VLM; bf16 and mxfp4/mxfp8/nvfp4 variants | Apple Silicon experimentation [S18](#s18) |
| vLLM | PR #60254 merged | Server-side serving and batching [S19](#s19) |
| Rust | candle port | Independent Rust runtime [S20](#s20) |
| C11/Metal/CUDA | `embeddinggemma.c` | Standalone custom multimodal server; reported RTX 3090 CUDA throughput of 102,755 tok/s at 2,048 context for the 300M variant [S21](#s21) |
| NPU/edge ports | OpenVINO, Apple ANE, Synaptics, FastFlowLM, Arduino/Radxa/RDKX5, etc. | Proves the model is small enough to chase unusual accelerators [S22](#s22) |

### LiteRT-LM numbers

Reported from the LiteRT provider cards [S14](#s14):

| Device | Target | Result |
|---|---|---:|
| Pixel 11 Pro | TPU, text | 8.3 ms |
| Pixel 11 Pro | TPU, full media | 149 ms |
| iPhone 18 Pro | GPU, text | 11.6 ms |
| MacBook M5 | GPU, text | 9.5 ms |
| XPS 16 | NPU, text | 13.3 ms |
| RTX 4090 | GPU/CUDA, text | 7.6 ms |
| Raspberry Pi 5 | CPU | 161 ms |
| Arduino VENTUNO Q | NPU | 13.6 ms |

### Core ML numbers

FluidInference reports [S15](#s15):

- M5 Pro text: 2.6 ms at 32 tokens, 27.4 ms at 512 tokens.
- `pack_256`: about 644 texts/sec.
- One hour of audio: 5.8 sec, or 617× real time.
- RMSNorm fp16 rescale workaround: cosine 0.9996 despite the official fp16 warning.
- Text ops: 100% ANE.

### CPU-Max fork

`Yazeedx0/embeddinggemma-cpu-max`, announced on 2026-10-16, claims a 2.46× geomean over the fastest CPU backend across 16/16 workloads while retaining cosine ≥ 0.99914 against official FP32. It reports about 1.4 GB RAM versus 4.8 GB PyTorch and an AVX-VNNI int8 kernel around 7× per core [S23](#s23). Treat media/video results carefully: the fork's own caveat says upstream video semantics deviate up to cosine 0.876, so do not mix those vectors into one index [S23](#s23).

## DigUp: The Spotlight Alternative

**Repo:** [ARahim3/DigUp](https://github.com/ARahim3/DigUp) [S6](#s6)

The model card ecosystem's most user-visible project is not a library; it is a local search app. DigUp searches:

- Photos.
- PDFs.
- Documents.
- Recordings.
- Video.
- Code.

Implementation details from its README [S6](#s6):

- Swift, macOS 14+.
- v0.7.0-beta.1 adds Windows/Linux beta.
- Uses ggml-org Q8_0 EG2 through llama.cpp.
- Metal on Apple Silicon; Vulkan on Windows/Linux.
- Model size: text about 310 MB plus media about 555 MB, about 865 MB total.
- SQLite vector index.
- One vector per picture, PDF page, passage, frame, or 30-second audio window.
- Hybrid exact-word boost on top of semantic search.
- Separate index and `code:` search mode.
- Hotkey: `⇧⌘Space` on macOS or `Ctrl+Shift+Space` elsewhere.
- Index is versioned against the model version.
- Example workload: indexing all of llama.cpp's code takes about 20 minutes and 130 MB.

Why this matters: DigUp demonstrates the product shape that EG2 enables—private, on-device, multimodal "everything search" without uploading your disk to a cloud search API.

### DigUp-related ports and forks

- [sunboss/DigUp-Windows](https://github.com/sunboss/DigUp-Windows) [S6](#s6)
- [ajisrawi/DigUp-Windows](https://github.com/ajisrawi/DigUp-Windows) [S6](#s6)
- [cgoat/DigUp-Windows](https://github.com/cgoat/DigUp-Windows) [S6](#s6)
- [Nuu-maan/omarchy-digup](https://github.com/Nuu-maan/omarchy-digup): 5-star QML port [S6](#s6)
- [radimsem/omafind](https://github.com/radimsem/omafind) [S6](#s6)
- `depletingmode/omarchy-semsearch` was listed here on 2026-10-18 and returns 404 as of 2026-10-23; it is removed rather than linked.

## Community Applications

The full GitHub CLI sweep found **1,073 unique repositories** across names, descriptions, READMEs, and code: 264 from repo/description/readme search, 883 from code hits, and 2,576 deduplicated file-hit rows. The sweep itself cloned and downloaded nothing; the earlier DigUp and Quivr deep dives did clone those two repositories. `github_sweep/verify_sweep.py` recomputes every number in this paragraph from the manifests and passes. The structured sweep is in `github_sweep/README.md`, `github_sweep/all_mentioning_repos.txt`, `github_sweep/all_repos_metadata.tsv`, and `github_sweep/code_hits_all.tsv`; launch-week highlights remain in `repos_table.tsv` and `gh_embeddinggemma.json` [S24](#s24) [S25](#s25).

| Project | Stars (2026-10-23) | What it does |
|---|---:|---|
| [The-Vibe-Company/quivr](https://github.com/The-Vibe-Company/quivr) | 39,601 | Content-stream search engine; EG2 is the selected demo embedding, E5 is the default ingest encoder [S26](#s26) |
| [ARahim3/DigUp](https://github.com/ARahim3/DigUp) | 5,500 | Multimodal macOS search / Spotlight alternative [S6](#s6) |
| [allenv0/SCM](https://github.com/allenv0/SCM) | 504 | macOS multimodal memory agent [S27](#s27) |
| [ampersandru/VectorDash](https://github.com/ampersandru/VectorDash) | 30 | Rust Windows full-search replacement, clipboard, launcher [S28](#s28) |
| [meangrinch/LocalLens](https://github.com/meangrinch/LocalLens) | 23 | Local multimodal finder [S24](#s24) |
| [iDiagoValeta/localOllamaRAG](https://github.com/iDiagoValeta/localOllamaRAG) | 14 | Local RAG stack [S24](#s24) |
| [raisulsohan/lazyFinds](https://github.com/raisulsohan/lazyFinds) | 10 | Bengali-oriented local search [S24](#s24) |
| [yazzang-homelab/im-looking-for](https://github.com/yazzang-homelab/im-looking-for) | 9 | CLI/app/MCP search [S24](#s24) |
| [pdstn12/Recall](https://github.com/pdstn12/Recall) | 7 | Linux Rust file search [S24](#s24) |
| [jwa91/sift-it](https://github.com/jwa91/sift-it) | 2 | Rust macOS file search [S24](#s24) |

One row from the 2026-10-18 version was removed: "lawvault, 13 stars." It is not a GitHub repository and not an EG2 model. The only match is `ByronLeeee/EmbeddingGemma-300M-LawVault` on Hugging Face, a 300M v1-era fine-tune with 1 like, so it does not belong in an EG2 application table [S40](#s40).

The wider GitHub sweep adds a second wave of interesting work [S24](#s24):

- [DenisovAV/flutter_edge_ai](https://github.com/DenisovAV/flutter_edge_ai): 643 stars, Flutter multimodal embeddings/RAG/speech across Android, iOS, web, and desktop.
- [zhongkaifu/TensorSharp](https://github.com/zhongkaifu/TensorSharp): 600 stars, native .NET inference engine with Windows/MacOS/iOS/Linux support.
- [FluidInference/FluidUse](https://github.com/FluidInference/FluidUse): 524 stars, Apple Silicon computer-use stack using typed decisions.
- [JimLiu/baocut](https://github.com/JimLiu/baocut): 1,208 stars, AI video editing with transcription/subtitling/translation.
- [ml-explore/mlx-swift-lm](https://github.com/ml-explore/mlx-swift-lm): native Swift MLX model implementation.
- [curiosity-ai/sentence-transformers-sharp](https://github.com/curiosity-ai/sentence-transformers-sharp): C# implementation including audio/vision paths.
- [misterekkk/lantern](https://github.com/misterekkk/lantern): macOS Spotlight-style semantic search.
- [KB01111/WinSearch-lumen-engine](https://github.com/KB01111/WinSearch-lumen-engine): Windows 11 multimodal launcher. The repo was renamed from `KB01111/WinSearch` and has no stars yet; the earlier "WinSearch" link still redirects.
- [xafold/SpotLite](https://github.com/xafold/SpotLite): Linux Spotlight-style GPU search.
- [thakurious/trowel](https://github.com/thakurious/trowel): Linux/Omarchy DigUp-style Rust/QML port.
- [rabimba/Prism](https://github.com/rabimba/Prism): cross-platform Linux/macOS multimodal search with ASR.

Quivr deserves special mention, with one correction to the 2026-10-18 wording. EG2 is **not** its default embedder. `core.ingest` with E5 is pinned by default; EG2 appears twice: as the selected embedding for the hosted demo deployment (`QUIVR_DEMO_EMBEDDING=gemma`, text-only bf16 on a Modal L4, batch size 32, scale-to-zero), and as an optional CPU query encoder that is off unless the image is built with `QUIVR_BUILD_LOCAL_QUERY_ENCODER=1`. It pins EG2 at revision `914f7f89…` and stores float32 768d vectors [S26](#s26). Its CPU sample measured about 0.546 passages/sec on four Xeon cores, and the sample's own note says the synthetic input turned out to be 1,533 tokens rather than the requested 512, so it is not a 512-token benchmark [S26](#s26). It also calibrated a 0.65 alert threshold on 156 French/English pairs, 16 of them related: positive scores spanned 0.660–0.831 and negatives 0.473–0.728 [S26](#s26).

## The ASR Wave: "300M For Ears"

The community discovered that EG2's audio tower can act as an acoustic encoder for speech, with a small reader trained on top. The HF discussion #9 sums up the tension: about 470M parameters for vision+audio versus about 130M transformer parameters for text, with the other half of the 270M text stack being vocabulary table [S5](#s5).

### QUAN-Transcribe

Vietnamese ASR built on the EG2 audio encoder plus a CTC reader [S7](#s7):

- 356M parameters.
- Average WER: **6.87%** across eight test sets.
- About **3,713× real time** on H100.
- Streaming chunks: 0.48 sec.
- Training: 3 hours on 8×H100.
- Optional KenLM.
- Beats the listed Gemini-Flash-3.8, Qwen3-ASR-1.7B, Cohere, ElevenLabs, PhoWhisper-large, and Whisper large-v3 comparisons in average WER.

### eg2.haku.sh / EG2 Transcribe

The HN post reached 433 points [S8](#s8). The saved item carries 33 top-level comments and no total count, so the earlier "97 comments" figure is dropped as unverifiable. The speed and WER numbers below come from the project page, not the HN item [S8](#s8):

- One hour of audio in about 13 sec on a base M3 MacBook Air.
- About 288× real time.
- About 5% WER.
- Reader trained in under 2 hours on 8×H100.
- English vocabulary of about 229,000 words discovered by nearest-neighbor lookup in embedding space.

Related checkpoints include a 1,000-hour English RNNT model by Steveeeeeeen and Deep-unlearning's smol-audio work [S29](#s29) [S30](#s30).

### Other speech projects

- [mstkyvz/embeddinggemma2-turkish-stt](https://huggingface.co/mstkyvz/embeddinggemma2-turkish-stt): frozen 300M audio encoder plus an 8.3M CTC reader, trained on 8.3 hours of FLEURS using a MacBook M4 Pro; 15.5% clean WER with LM+Zemberek and it beats Whisper small on telephone simulation [S9](#s9).
- [naijaml/embeddinggemma-2-african-speech-lora](https://huggingface.co/naijaml/embeddinggemma-2-african-speech-lora): 5M-parameter LoRA for six languages; speech→transcript Recall@1 mean improves from 0.938 to 0.997; 128d retains 0.99 with the adapter [S10](#s10).
- `norsk-asr`, `embed2asr`, Cantonese CTC, Arabic/Gulf ASR, KolStream Hebrew/English, Persian speech retrieval, Android/iOS and Linux transcribe ports, and a Vietnamese Elixir port [S24](#s24).

## Fine-Tunes And Domain Forks

- [mrm8488/embeddinggemma-2-ft-typed-decision](https://huggingface.co/mrm8488/embeddinggemma-2-ft-typed-decision): schema-conditioned scorer with choice/score/noul typed outputs. Accuracy improves 67.7%→76.4%, works multilingual with softer probabilities, and already has GGUF/Core ML derivatives [S31](#s31).
- [eulogik/bharat-embed-270m-gemma2](https://huggingface.co/eulogik/bharat-embed-270m-gemma2): Hindi/Hinglish fine-tune. IndicQA improves 0.7279→0.7324; truncation cost is -0.030 at 256d and -0.103 at 128d; ONNX INT8 drift is 0.0066 [S32](#s32).
- [jonpark0/embeddinggemma-2-ko](https://huggingface.co/jonpark0/embeddinggemma-2-ko): Korean variant [S24](#s24).
- [pastel-labs/embeddinggemma-2-photo-anchor](https://huggingface.co/pastel-labs/embeddinggemma-2-photo-anchor): COCO photo anchors plus compact tables. 4-bit at 768d retains 0.997; 1-bit moves from 0.954 to 0.998 with top-20 reranking; storage drops to 384/96 bytes per photo [S33](#s33).
- Medical LoRA, birds classifier, Persian speech, Turkish STT, and dozens of per-language trimmed variants exist in the broader HF sweep [S24](#s24).

## Community Benchmarks And Compression

### EG2 versus Gemini

`shivanathd/embeddinggemma2-vs-gemini-bench` runs 19 tests. Local EG2 wins 4, cloud wins 6, 8 tie, and 1 is neither; local wins or ties 12/19. Local text queries take about 13 ms versus about 617 ms for cloud [S34](#s34).

Where local wins:

- Legal contracts: 0.771 versus 0.732.
- STS-B: 0.875 versus 0.771, though Gemini received no task prefix in that test.
- PDF page retrieval from image: 0.778 versus 0.611.
- Video moment retrieval: 0.722 versus 0.611.

Where cloud wins:

- Urdu, Arabic, Tamil, and Malayalam by 9–18 points.
- Finance FiQA: 0.508 local versus 0.719 cloud.
- Some health cases.

The repo openly lists methodology caveats including contamination and provider load spikes [S34](#s34).

### Qdrant 1-bit compression

Qdrant's TurboQuant analysis reports [S35](#s35):

| Configuration | Bytes/vector | nDCG retained | RAM reduction |
|---|---:|---:|---:|
| 768d 1-bit | 104 | 99.0% | 30× |
| 768d 1-bit + rescoring | 104 | 99.7% | 30× |
| 512d 1-bit | 72 | 97.3% | 43× |
| 256d 1-bit | 40 | 88.1% | 77× |
| 256d 1-bit + rescoring | 40 | 94.5% | 77× |

For 10M documents, the vector RAM estimate falls from 30.7 GB to about 1 GB in the best-demonstrated setup [S35](#s35).

### FluidInference demos

FluidInference reports on M5 Pro [S15](#s15):

- 10,080 posts sorted at about 600/sec (`TopicSortDemo`).
- 4.5 hours of audio indexed in 38 sec, about 431× real time, with audio on the GPU and text on the Neural Engine at once (`AudioSearchDemo`).
- 5,617 code functions indexed in 16 sec (`CodeSearchDemo`).
- About 710 searches/sec on the audio demo and about 700/sec on the code demo.
- The earlier "11/16 known-answer code queries at top 1" is dropped: it appears in neither the Core ML card nor the FluidUse README [S15](#s15).

## Google Ecosystem And Product Integrations

Google's launch blog positions EG2 as v2 of EmbeddingGemma, notes 20M+ v1 downloads, and gives Pixel RAM estimates [S11](#s11).

The AI Edge blog adds [S36](#s36):

- Google AI Edge Gallery app on Android/iOS.
- Instant Media Search with search-as-you-type.
- SQLite plus cosine reranking.
- Live example: "Katze schläft auf Tastatur" reranks as typing continues.
- Video Moments Finder using text→keyframe search without transcription.
- AI Edge Foresight Mac meeting companion using Gemma 4.
- MediaPipe UniversalEmbedder/SemanticRetriever with single-digit-ms ANN.
- MediaPipe Decision Task under 100 ms for 500 options, including a chess demo.
- ML Kit Android support coming.
- LiteRT QAT INT4/INT8 plus MRL slicing for up to 8× memory savings.
- M5 Pro GPU vision benchmark: 37.3 ms/image, 26.9 images/sec at a 70-token budget.

## Gotchas And Best Practices

1. **Do not use fp16.** Officially, use bf16 or fp32 [S1](#s1). The Core ML RMSNorm workaround is a deliberate exception, not a blanket recommendation [S15](#s15).
2. **Match query and document prefixes.** Wrong prefixes can silently hurt retrieval [S1](#s1).
3. **Do not mix incompatible vector versions.** Model changes, media stack changes, and dimension changes invalidate indexes. DigUp version-gates its index for a reason [S6](#s6).
4. **Keep 256d as the default aggressive cut.** 128d is text-first territory; multimodal quality falls off hard [S1](#s1).
5. **Chunk long audio.** The native audio input is about 5.5 minutes max; downstream ASR projects use 0.48-sec chunks or other streaming windows [S1](#s1) [S7](#s7).
6. **Treat media and text differently when compressing.** 768d handles text and code best; aggressive multimodal truncation is not equally safe [S1](#s1).
7. **Benchmark your own domain.** Flat average MTEB does not mean flat for your corpus; code gains and local-domain wins can be large [S1](#s1) [S34](#s34).
8. **For tiny vector DBs, 1-bit plus rescoring is the interesting frontier.** Qdrant's numbers are strong, but rerank with better vectors when precision matters [S35](#s35).
9. **Prefer official QAT quantizations on edge devices.** LiteRT's int4/int8/int2 artifacts are purpose-built [S14](#s14).
10. **Check GPU/NPU completeness.** Some "EG2 port" claims mean text-only, some mean media, and a few mean approximate behavior on another stack. Read the provider card before treating it as drop-in [S4](#s4) [S15](#s15) [S16](#s16).

## What This Report Does Not Prove

The report is strong on "what exists" and weaker on "what works," and the difference matters before anyone builds on it.

1. **Mention is not use.** The 1,073-repo union is every repository that *mentions* EmbeddingGemma 2 in a name, description, README, or file. It includes infrastructure that merely lists it as a supported model (`ollama/ollama`, `huggingface/transformers`, `ggml-org/llama.cpp`, `vllm-project/vllm`). The count is evidence of attention, not of 1,073 working integrations.
2. **The sweep hit two 1,000-result caps.** GitHub returned at most 1,000 files per code query, so the true file count is higher and the set is a top-relevance sample. Treat "1,073" as a floor with a known sampling method.
3. **Star counts are a moving snapshot.** Between 2026-10-18 and 2026-10-23, DigUp moved 4,522 → 5,500, baocut 1,046 → 1,208, VectorDash 25 → 30. Any number in this report is only true on its date.
4. **X and Reddit are missing.** Nitter was offline or captcha-blocked and the Reddit API was blocked. Claims sourced to "people on X" are not auditable here.
5. **Performance numbers are self-reported.** QUAN-Transcribe, eg2.haku.sh, CPU-Max, embeddinggemma.c, LiteRT, Core ML, and DigUp numbers come from their authors. None were reproduced on this machine.
6. **"Nobody has built this" is negative evidence.** The open-lane list comes from searching a capped corpus. A project with no README, a private repo, or a different spelling would not appear. Absence of a hit is a hint, not proof.
7. **Two cited models are no longer reachable.** `Yazeedx0/embeddinggemma-cpu-max` and `mofumail/embeddinggemma-2-candle` returned HTTP 401 on 2026-10-23. Their local README copies are preserved; the live pages could not be re-checked.

## Community Vibe

The energy comes from three overlapping realizations:

1. **Local search became multimodal.** Spotlight-like apps, Windows replacements, browser search, and legal/document/code RAG all reused the same embedding model.
2. **The audio tower became a speech engine.** People did not just retrieve recordings; they turned acoustic features into ASR and cross-language speech retrieval.
3. **Tiny beat convenience.** Apache-2.0, 740M total, 270M text-only, and 768d with 128d fallback made local-first apps plausible without server accounts.

High-signal reactions include:

- HN launch thread: 439 points [S37](#s37).
- EG2 Transcribe thread: 433 points [S8](#s8).
- Simon Willison's argument that Apache-2.0 is useful even when a hosted model is stronger: you can keep a local fallback and avoid vendor lock-in [S38](#s38).
- HF discussion #5, where a Google reply states general text performance is "consistent with version 1" and frames code retrieval and multimodality as the real changes. The reply does not say the flat text score was deliberate [S5](#s5).
- HF discussion #6 asking for macOS local knowledge layers and MCP integration; the reply thread is where the Spotlight comparison shows up [S39](#s39).

Research limitation: Nitter was offline/captcha-blocked, Reddit API was blocked, and several general search engines blocked scraping. X-specific threads therefore are not fully auditable in this report. The strongest public evidence for the community work is GitHub/HF/HN, which were successfully harvested.

## Sources

<a id="s1"></a>
### S1 — Official model card
- Local file: `hf_README.md`
- URL: <https://huggingface.co/google/embeddinggemma-2>

<a id="s2"></a>
### S2 — Config file
- Local file: `hf_config.json`
- URL: <https://huggingface.co/google/embeddinggemma-2/raw/main/config.json>

<a id="s3"></a>
### S3 — Hugging Face model metadata API
- Local file: `hf_model_api.json`
- URL: <https://huggingface.co/api/models/google/embeddinggemma-2>

<a id="s4"></a>
### S4 — llama.cpp integration
- Local file: `providers.txt`, `llama_pr.json`
- URL: <https://github.com/ggml-org/llama.cpp/pull/30054>

<a id="s5"></a>
### S5 — HF discussion #5 and #9
- Local files: `discussion_5.html`, `discussion_9.html`
- URLs:
  - <https://huggingface.co/google/embeddinggemma-2/discussions/5>
  - <https://huggingface.co/google/embeddinggemma-2/discussions/9>

<a id="s6"></a>
### S6 — DigUp
- Local file: `repo_digup.json`, cloned repository `research/digup`
- URL: <https://github.com/ARahim3/DigUp>

<a id="s7"></a>
### S7 — QUAN-Transcribe
- Local file: `providers/qnguyen3__QUAN-Transcribe-1.0.md`
- URL: <https://huggingface.co/qnguyen3/QUAN-Transcribe-1.0>

<a id="s8"></a>
### S8 — EG2 Transcribe / eg2.haku.sh HN thread
- Local files: `hn_item_50069971.json`, `eg2_haku.html` (project page with the speed table and WER)
- URL: <https://news.ycombinator.com/item?id=50069971>

<a id="s9"></a>
### S9 — Turkish STT
- Local file: `providers/mstkyvz__embeddinggemma2-turkish-stt.md`
- URL: <https://huggingface.co/mstkyvz/embeddinggemma2-turkish-stt>

<a id="s10"></a>
### S10 — African speech LoRA
- Local file: `providers/naijaml__embeddinggemma-2-african-speech-lora.md`
- URL: <https://huggingface.co/naijaml/embeddinggemma-2-african-speech-lora>

<a id="s11"></a>
### S11 — Google launch blog
- Local file: `blog.html`
- URL: <https://blog.google/technology/ai/embeddinggemma-2/>

<a id="s12"></a>
### S12 — ggml-org GGUF
- Local file: `providers/ggml-org__embeddinggemma-2-GGUF.md`
- URL: <https://huggingface.co/ggml-org/embeddinggemma-2-GGUF>

<a id="s13"></a>
### S13 — Unsloth GGUF
- Local file: `providers/unsloth__embeddinggemma-2-GGUF.md`
- URL: <https://huggingface.co/unsloth/embeddinggemma-2-GGUF>

<a id="s14"></a>
### S14 — LiteRT-LM cards
- Local files: `providers/litert-community__embeddinggemma-2-740m-litert-lm.md`, `providers/litert-community__embeddinggemma-2-text-270m-litert-lm.md`, `providers/litert-community__embeddinggemma-2-text-vision-440m-litert-lm.md`
- URLs:
  - <https://huggingface.co/litert-community/embeddinggemma-2-740m-litert-lm>
  - <https://huggingface.co/litert-community/embeddinggemma-2-text-270m-litert-lm>
  - <https://huggingface.co/litert-community/embeddinggemma-2-text-vision-440m-litert-lm>

<a id="s15"></a>
### S15 — FluidInference Core ML
- Local file: `providers/FluidInference__embeddinggemma-2-coreml.md`
- URL: <https://huggingface.co/FluidInference/embeddinggemma-2-coreml>

<a id="s16"></a>
### S16 — ONNX port
- Local file: `providers/onnx-community__embeddinggemma-2-ONNX.md`
- URL: <https://huggingface.co/onnx-community/embeddinggemma-2-ONNX>

<a id="s17"></a>
### S17 — WebGPU demo
- Local files: `spaces_raw/webml-community__embeddinggemma-2-webgpu.md`, `spaces_raw/webgpu_worker.js`
- URL: <https://huggingface.co/spaces/webml-community/embeddinggemma-2-webgpu>

<a id="s18"></a>
### S18 — MLX
- Local file: `providers/mlx-community__embeddinggemma-2-bf16.md`
- URL: <https://huggingface.co/mlx-community/embeddinggemma-2-bf16>

<a id="s19"></a>
### S19 — vLLM integration
- Local file: `providers.txt`
- URL: <https://github.com/vllm-project/vllm/pull/60254>

<a id="s20"></a>
### S20 — Rust candle port
- Local file: `providers.txt`
- URL: <https://huggingface.co/mofumail/embeddinggemma-2-candle>

<a id="s21"></a>
### S21 — embeddinggemma.c
- Local file: `quixai_readme.md`
- URL: <https://github.com/QuixiAI/embeddinggemma.c>

<a id="s22"></a>
### S22 — NPU/edge sweep
- Local file: `providers.txt`
- Representative sources: `daaku/eg2npu`, `anemll/anemll-embeddinggemma-2-ane`, `wesjos/embeddinggemma-2-openvino`, `vespa-engine/embeddinggemma-2-ONNX`, Edge Impulse VENTUNO Q material
- Removed: `gh_runtime_repos.json` was cited here on 2026-10-18 but is a 3-byte empty array from a rate-limited query, so it proves nothing.

<a id="s23"></a>
### S23 — CPU-Max fork
- Local files: `yazeed_README.md`, `discussion_14.html`
- URLs:
  - <https://huggingface.co/Yazeedx0/embeddinggemma-cpu-max>
  - <https://huggingface.co/google/embeddinggemma-2/discussions/14>
- Status 2026-10-23: the model page returns HTTP 401 (removed, renamed, or made private). The local README is the surviving copy of the claims.

<a id="s24"></a>
### S24 — GitHub/HF community sweep
- Local files: `repos_table.tsv`, `gh_embeddinggemma.json`, `hf_models_search.json`, `hf_models_search_broader.json`, `hf_models_search_gemma.json`

<a id="s25"></a>
### S25 — Code-focused sweep
- Local files: `github_sweep/code_hits_all.tsv`, `github_sweep/code_hit_repos_all.txt`
- Removed: `code_repos.tsv` was cited here on 2026-10-18 but contains a single stray `200<TAB>` line, the leaked HTTP status from a failed query. The real code-hit data is in `code_hits_all.tsv`.

<a id="s26"></a>
### S26 — Quivr
- Local file: cloned repository `research/quivr`, `repo_quivr.json`
- URL: <https://github.com/The-Vibe-Company/quivr>

<a id="s27"></a>
### S27 — SCM
- Local file: `repo_scm.json`
- URL: <https://github.com/allenv0/SCM>

<a id="s28"></a>
### S28 — VectorDash
- Local file: `repo_vectordash.json`
- URL: <https://github.com/ampersandru/VectorDash>

<a id="s29"></a>
### S29 — 1,000-hour English RNNT checkpoint
- Local file: `providers/Steveeeeeeen__embeddinggemma2-en-direct-1000h-20261014-rnnt.md`
- URL: <https://huggingface.co/Steveeeeeeen/embeddinggemma2-en-direct-1000h-20261014-rnnt>

<a id="s30"></a>
### S30 — smol-audio
- Local files: `smol_audio_README.md`, `smol_audio_repo.json`

<a id="s31"></a>
### S31 — Typed decision fine-tune
- Local file: `providers/mrm8488__embeddinggemma-2-ft-typed-decision.md`
- URL: <https://huggingface.co/mrm8488/embeddinggemma-2-ft-typed-decision>

<a id="s32"></a>
### S32 — Bharat-Embed
- Local file: `providers/eulogik__bharat-embed-270m-gemma2.md`
- URL: <https://huggingface.co/eulogik/bharat-embed-270m-gemma2>

<a id="s33"></a>
### S33 — Photo anchor fine-tune
- Local file: `providers/pastel-labs__embeddinggemma-2-photo-anchor.md`
- URL: <https://huggingface.co/pastel-labs/embeddinggemma-2-photo-anchor>

<a id="s34"></a>
### S34 — EG2 versus Gemini benchmark
- Local file: `gemini_bench_README.md`
- URL: <https://github.com/shivanathd/embeddinggemma2-vs-gemini-bench>

<a id="s35"></a>
### S35 — Qdrant TurboQuant
- Local file: `qdrant_blog.md`
- URL: <https://qdrant.tech/blog/turboquant/>

<a id="s36"></a>
### S36 — Google AI Edge blog
- Local file: `edge_blog.html`
- URL: <https://developers.googleblog.com/en/embeddinggemma-2-on-device-multimodal-ai/>

<a id="s37"></a>
### S37 — HN launch thread
- Local file: `hn_item_49980487.json`
- URL: <https://news.ycombinator.com/item?id=49980487>

<a id="s38"></a>
### S38 — Simon Willison commentary
- Local file: `simonwillison.html`
- URL: <https://simonwillison.net/2026/Oct/6/embeddinggemma-2/>

<a id="s39"></a>
### S39 — HF discussion #6
- Local file: `discussion_6.html`
- URL: <https://huggingface.co/google/embeddinggemma-2/discussions/6>

<a id="s40"></a>
### S40 — Source re-verification, 2026-10-23
- Script: `verify_sources.py`
- Snapshot: `verification/sources_2026-10-23.tsv`
- Method: extract every GitHub and Hugging Face link in this report, then re-query `gh api repos/{owner}/{repo}` and the HF model API. 49 links checked, 47 resolved, 2 failed (two model pages now returning HTTP 401).
- Sweep check: `github_sweep/verify_sweep.py` recomputes 264 + 883 → 1,073 and 2,576 code rows from the manifests.
- Used to correct the star table, the Quivr default-embedder claim, the dead `omarchy-semsearch` link, and the `WinSearch` rename.
