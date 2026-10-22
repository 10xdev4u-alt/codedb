---
license: apache-2.0
base_model: google/embeddinggemma-2
library_name: coreml
pipeline_tag: feature-extraction
language:
- multilingual
tags:
- coreml
- apple-neural-engine
- on-device
- embeddings
- sentence-similarity
- gemma
---

# EmbeddingGemma 2 (text + audio + image) — Core ML

The text, audio and vision encoders of [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2)
converted to Core ML: text runs entirely on the Apple Neural Engine, audio and images on the GPU. Weights are the original ones (stored fp16 in the model; the token table is
the original bf16). All three encoders are included (see Audio and Images); video uses the image encoder on frames.

Output: the same 768-d, L2-normalized embedding as `SentenceTransformer("google/embeddinggemma-2").encode(...)`
(mean pooling over tokens, then normalization). Matryoshka truncation to 512/256/128 works as in the original: keep
the first N values and re-normalize.

**Audio** (added): `EmbeddingGemma2Audio.mlpackage` turns 10 s of 16 kHz audio into 250 tokens in the text model's
space; the text functions then embed them, so audio and text share one space (search audio with a text query).

## Files

| File | What |
|---|---|
| `EmbeddingGemma2Text.mlpackage` | ML Program, fp16, 7 functions sharing one set of weights (271 MB) |
| `embeddings.bf16` | token embedding table, 262,144 × 512 raw bfloat16 (256 MB); look up rows, multiply by √512 |
| `tokenizer.json` | the original Gemma tokenizer, unchanged |
| `EmbeddingGemma2Audio.mlpackage` | audio encoder (Gemma 4 USM conformer, 12 layers) + projection, fp16, log-mel in-graph (561 MB) |
| `EmbeddingGemma2Vision.mlpackage` | vision encoder (Gemma 4 ViT, 16 layers, 2-D RoPE) + 3x3 pooling + projection, fp16, functions `vision_70` / `vision_140` / `vision_280` (292 MB) |
| `position_embeddings.f16` | the vision patch embedder's x / y position tables, rows 0–1023, fp16 (3 MB) |
| `config.json` | shapes, function list, token ids, task prefixes, audio window and image patch layout |

## Functions

Every function has fixed shapes, which is what keeps it on the Neural Engine. Variable-length (enumerated) shapes
put the whole graph on the CPU.

| Function | Inputs | Output |
|---|---|---|
| `embed_32` … `embed_512` | `inputs_embeds` [1, S, 512] fp16, `attention_mask` [1, S] fp16 (1 = token, right padding) | `embedding` [1, 768] |
| `pack_256` | `inputs_embeds` [1, 256, 512], `attention_bias` [1, 1, 256, 256] (0 within a text, −1e4 elsewhere), `positions` [256, 1] (restart at 0 per text), `pool` [8, 256] (1/len over each text's tokens) | `embedding` [8, 768] |

S ∈ {32, 48, 64, 128, 256, 512}. Inputs longer than 512 tokens must be truncated; on our test set capping at 512
tokens changed nothing measurable. At ≤ 512 tokens every sliding-window layer sees the whole sequence, so a padding
mask is all the model needs.

`pack_256` runs up to eight short texts in one call. Short calls are bound by streaming the weights from memory, so
one 256-token call with eight texts costs about the same as two single calls.

## Audio

`EmbeddingGemma2Audio.mlpackage`: `waveform` [1, 160160] fp32 (160 zero samples, then up to 10 s of 16 kHz mono,
zero-padded) and `frame_mask` [1, 1000] (frame i valid when `i*160 + 321 <= 160 + samples`) → `audio_tokens`
[1, 250, 512]; token k is valid when `frame_mask[4k]` is. Build `<bos> <|audio> tokens <audio|> <eos>` (special
tokens from `embeddings.bf16` × √512, audio tokens as they are) and run `embed_256`. Log-mel (Gemma 4 feature
extractor: 20 ms Hann frames, 10 ms hop, 128 HTK mel bins, log(mag + 1e-3)) is computed inside the model.

Run it on the **GPU** (`cpuAndGPU`): the chunked local attention's 5-D blocks fall back to the CPU on the Neural
Engine (46 ms per window there vs 13.6 ms on the GPU). fp16 drifts from fp32 on a few quiet tokens (window embedding
cos ≥ 0.977, mean 0.9993); on a 1-hour earnings-call index, the top hit matched fp32 for 15/15 text queries and the
top-5 overlap was 95%.

| 1 hour of audio, M5 Pro | Time |
|---|---|
| audio model (GPU, fp16) | 5.8 s (617× real time) |
| audio model + text model, one window after another | 10.2 s (353×) |
| fp32 audio model (exact to PyTorch, token cos 1.0000) | 13.2 s (272×) |

## Images

`EmbeddingGemma2Vision.mlpackage` has one fixed-shape function per soft-token budget: `vision_70` (630 patches),
`vision_140` (1,260) and `vision_280` (2,520, the model's default). Resize the image keeping its aspect ratio so the
sides are multiples of 48 px and it has at most 9 × budget patches of 16 px (HF `Gemma4ImageProcessor`), scale RGB to
[0, 1], cut it into patches row by row (each patch `[16 rows][16 cols][RGB]`) and pad to the function's patch count.
Inputs: `patches` [1, N, 768], `positions` [1, N, 2] (x, y; −1 for padding), `position_embeddings` [1, N, 768]
(`table[0][x] + table[1][y]` from `position_embeddings.f16`), `valid` [1, N] and `pool` [T, N] (1/9 for each patch in
its 3 × 3 group). Output `image_tokens` [1, T, 512]; embed `<bos> <|image> tokens <image|> <eos>` with the text model.

| Budget | Zero-shot Oxford Pets (370 photos, 37 breeds) | GPU, M5 Pro | Neural Engine |
|---|---|---|---|
| 70 tokens | 87.0% | 14.6 ms (68 images/s) | 37 ms |
| 140 tokens | 88.4% | 34 ms (30 images/s) | 102 ms |
| 280 tokens | 89.5% | 64–177 ms | 341 ms |

Every op runs on the Neural Engine, but its time grows with the square of the patch count (full attention over all
patches), so the GPU is faster at every budget. fp32 wrapper vs sentence-transformers: cosine 1.000000; fp16 token
cosine ≥ 0.997 at 70/140 tokens.

## Use

1. Prepend the task prefix (e.g. `title: none | text: ` for documents, `task: search result | query: ` for queries;
   all in `config.json`).
2. Tokenize with `tokenizer.json`: `<bos>` (2), tokens, `<eos>` (1).
3. Look up each id's row in `embeddings.bf16` (bf16 → float: shift the 16 bits left by 16), multiply by √512 ≈
   22.627417, pass as fp16.
4. Call the smallest `embed_S` that fits, or pack several texts into `pack_256`.

A Swift implementation (tokenizer, table lookup, packing, downloads) is in
[FluidUse](https://github.com/FluidInference/FluidUse): `EmbeddingGemma2Manager`.

Requires macOS 15 / iOS 18 (multifunction models). The first load on a device compiles all seven functions for the
Neural Engine, which takes several minutes once; Core ML caches the result.

## Numbers (M5 Pro, macOS 27)

| | Result |
|---|---|
| Neural Engine placement | 3,862 / 3,862 ops (100%) in every function |
| Latency, one text | 32 tokens 2.6 ms · 64 tokens 3.2 ms · 128 tokens 5.6 ms · 256 tokens 11.3 ms · 512 tokens 27.4 ms |
| Throughput, short posts (`pack_256`, Swift) | 644 texts/s (one text per call: 307/s) |
| vs PyTorch fp32 (sentence-transformers) | cosine ≥ 0.9984, mean 0.99996 over 562 posts |

The model card warns against fp16: activations reach ~2,000, so squaring them inside RMSNorm overflows fp16. Every
RMSNorm here divides by the row's max-abs value first, which keeps the math in range (plain fp16 RMSNorm: cosine
0.95 to the reference; this conversion: 0.9996). The final normalization is rescaled the same way.

## Demos ([FluidUse](https://github.com/FluidInference/FluidUse), M5 Pro)

| Demo | What it shows |
|---|---|
| `TopicSortDemo` | 10,080 posts sorted into topics live (~600 posts/s); split any topic into subtopics |
| `AudioSearchDemo` | 4.5 h of audio indexed in 38 s (431× real time, audio on the GPU + text on the Neural Engine at once); eight text searches each return the right three clips (sound files under random names); ~710 searches/s |
| `CodeSearchDemo` | 5,617 FluidAudio functions indexed in 16 s; plain-English questions find the right function where an exact-phrase grep finds nothing; ~700 searches/s |

Each runs as a short show: `Sources/<Demo>/demo.sh`, then Play.

License: Apache 2.0, same as the source model.
