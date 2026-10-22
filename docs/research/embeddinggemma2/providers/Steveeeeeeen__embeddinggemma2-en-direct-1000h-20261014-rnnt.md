---
pipeline_tag: "automatic-speech-recognition"
language: ["en"]
base_model: ["google/embeddinggemma-2", "nvidia/parakeet-rnnt-0.6b"]
license: "other"
license_name: "apache-2.0-and-cc-by-4.0"
license_link: "https://huggingface.co/Steveeeeeeen/embeddinggemma2-en-direct-1000h-20261014-rnnt/blob/main/README.md"
---

# EmbeddingGemma ASR: rnnt

Checkpoint from the 1,000-hour English experiment. Completion and evaluation are recorded in metrics.json.

- [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2/blob/914f7f89142e33e77833254d9c9b90c3cef7303b/README.md) at `914f7f89142e33e77833254d9c9b90c3cef7303b`
- [nvidia/parakeet-rnnt-0.6b](https://huggingface.co/nvidia/parakeet-rnnt-0.6b/blob/1b6b548f70b93d2410c3d13cc0654cab300f06ef/README.md) at `1b6b548f70b93d2410c3d13cc0654cab300f06ef`

Changes: added a learned projection and an ASR head, then fine-tuned on English YODAS/Granary.

Google DeepMind audio encoder: Apache 2.0 (see [LICENSE](LICENSE)). NVIDIA NeMo and Suno.ai pretrained ASR head: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Load with `embeddinggemma_asr.experiment.load_checkpoint` from the [smol-audio](https://github.com/Deep-unlearning/smol-audio) example.
