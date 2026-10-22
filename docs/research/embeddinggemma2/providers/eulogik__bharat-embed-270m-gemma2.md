---
library_name: sentence-transformers
pipeline_tag: sentence-similarity
license: apache-2.0
base_model: google/embeddinggemma-2
language:
- hi
- en
tags:
- hinglish
- indic-rag
- on-device
- onnx
- gguf
- mrl
- matryoshka
- qdrant
- hindi
datasets:
- eulogik/bharat-embed-triplets-40k
---

# Bharat-Embed 270M

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
![Parameters 270M](https://img.shields.io/badge/Parameters-270M-green)
![Hindi NDCG 0.7324](https://img.shields.io/badge/Hindi%20NDCG%4010-0.7324-orange)
![ONNX parity ok](https://img.shields.io/badge/ONNX%20parity-pass-brightgreen)
![Built by Eulogik](https://img.shields.io/badge/Built%20by-Eulogik-7c3aed)

![Bharat-Embed overview](assets/hero.png)

## Direct answer

**Bharat-Embed 270M is a 270M text only EmbeddingGemma-2 fork for Hinglish and Hindi retrieval RAG.** It loads without vision or audio, runs on CPU and ONNX INT8, truncates to 128d, and is Apache-2.0. Pair it with [eulogik/flashrank-pro-base](https://huggingface.co/eulogik/flashrank-pro-base) as reranker. Built by [Eulogik](https://github.com/eulogik).

Find with: `embeddinggemma2 hindi hinglish indic rag on-device onnx gguf qdrant mrl apache 2.0`.

## Measured numbers

All numbers below were measured on a Mac mini M4, 2026-10-08/09. No estimates.

| Check | Base text only | Bharat-Embed | Delta |
|---|---|---:|---:|
| Hindi IndicQA NDCG@10, 768d | 0.7279 | 0.7324 | +0.0045 |
| Hindi cross lingual STS spearman | 0.6430 | 0.6423 | -0.0007 (tie) |
| Train loss start to end | 0.586 | 0.236 | learned |
| Torch vs ONNX INT8 mean drift | - | 0.0066 | under 1e-2 gate |
| Reload check | MISSING keys | clean, 168 adapters merged | fixed |

Note: the mteb runs use the default mteb encoding path, same both sides. The +0.03 stretch gate was not met. This card reports the miss plainly. v1.1 retrains on diverse real Hindi.

![Truncation chart](assets/truncation.png)

### Truncation cost on Hindi retrieval (measured NDCG@10)

| Dims | Score | vs 768d |
|---|---:|---:|
| 768 | 0.7324 | - |
| 512 | 0.7247 | -0.008 |
| 256 | 0.7023 | -0.030 |
| 128 | 0.6294 | -0.103 |

Plain read: 512d is near lossless. 256d costs 0.03. 128d costs 0.10 on Hindi, steeper than the base card multilingual average. Pick 512 for quality, 256 for the cost balance. 128d only for tight budgets with eyes open.

## How it was built

![Architecture](assets/architecture.png)

| Fact | Value |
|---|---|
| Base | `google/embeddinggemma-2`, text only (`vision_config` None, `audio_config` None) |
| Method | LoRA r16 on attention plus MLP, merged to clean keys |
| Data | 40k frozen triplets (15k Hinglish synth, 5k Banking77, 10k legal synth, 10k near-miss hard), SHA pinned |
| Train | 3 epochs, batch 8, len 256, AdamW 2e-5, fp32, Mac mini M4 |
| License note | FLORES eval only (CC-BY-SA). MS MARCO excluded (non-commercial terms). Train pack is Banking77 plus ours. |

## Quickstart

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "eulogik/bharat-embed-270m-gemma2",
    config_kwargs={"vision_config": None, "audio_config": None},
    model_kwargs={"torch_dtype": "bfloat16"},
)
q = model.encode("GST refund kaise claim karein?", prompt_name="SearchQuery",
                 truncate_dim=256, normalize_embeddings=True)
d = model.encode("title: GST refund | text: apply through portal with invoice proof",
                 truncate_dim=256, normalize_embeddings=True)
print(model.similarity(q, d))
```

Rules: queries and docs share one dim. Always normalize after truncate. fp16 never (base warns NaN).

## ONNX serve

```bash
pip install onnxruntime qdrant-client
python scripts/encode_onnx.py --model onnx/int8 --queries queries.txt --truncate 256
```

## Limits

- Text only. No image, video, or audio.
- Hindi and Hinglish first. Tamil and Telugu unmeasured.
- Trained at 256 tokens. Long doc behavior unmeasured.
- Scores rank, they do not calibrate. Pair with a reranker for decisions.

## Eulogik family

- Reranker: [eulogik/flashrank-pro-base](https://huggingface.co/eulogik/flashrank-pro-base) (149M, Apache-2.0)
- Code: [github.com/eulogik/Bharat-Embed](https://github.com/eulogik/Bharat-Embed)
- Org: [huggingface.co/eulogik](https://huggingface.co/eulogik)

## Keywords

embeddinggemma2 hindi embedding, hinglish embedding, indic rag embedding, on-device embedding, onnx embedding, gguf embedding ollama, qdrant hindi search, mrl matryoshka embedding, uae law embedding, difc rag
