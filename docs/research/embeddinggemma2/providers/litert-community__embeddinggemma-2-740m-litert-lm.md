---
license: apache-2.0
base_model:
- google/embeddinggemma-2
tags:
  - litert-lm
---

# litert-community/embeddinggemma-2-740m-litert-lm

Main Model Card: [google/embeddinggemma-2](https://huggingface.co/google/embeddinggemma-2)

EmbeddingGemma 2 740M is the full, natively multimodal variant of the EmbeddingGemma 2 family, packaged for low-latency, on-device inference using LiteRT. Integrating the 270M parameter text backbone with modular vision (170M) and audio (300M) encoders, this 740M parameter model maps text, code, images, video, and audio into a single, shared 768-dimensional vector space. It enables robust cross-modal semantics and supports interleaved multimodal inputs within a single 8,192-token context window. Built for ultimate flexibility, it allows developers to run full multimodal search, speech retrieval, and complex cross-media semantic similarity pipelines directly on consumer hardware.

## Try EmbeddingGemma 2 with LiteRT-LM

<div align="center">

| [<svg xmlns="http://www.w3.org/2000/svg" height="72px" viewBox="0 -960 960 960" width="72px" fill="currentColor"><path d="M40-240q9-107 65.5-197T256-580l-74-128q-6-9-3-19t13-15q8-5 18-2t16 12l74 128q86-36 180-36t180 36l74-128q6-9 16-12t18 2q10 5 13 15t-3 19l-74 128q94 53 150.5 143T920-240H40Zm275.5-124.5Q330-379 330-400t-14.5-35.5Q301-450 280-450t-35.5 14.5Q230-421 230-400t14.5 35.5Q259-350 280-350t35.5-14.5Zm400 0Q730-379 730-400t-14.5-35.5Q701-450 680-450t-35.5 14.5Q630-421 630-400t14.5 35.5Q659-350 680-350t35.5-14.5Z"/></svg>](https://play.google.com/store/apps/details?id=com.google.ai.edge.gallery&pli=1) | [<svg xmlns="http://www.w3.org/2000/svg" height="84px" viewBox="0 -960 960 960" width="84px" fill="currentColor"><path d="M160-615v-60h60v60h-60Zm0 335v-275h60v275h-60Zm292 0H347q-24.75 0-42.37-17.63Q287-315.25 287-340v-280q0-24.75 17.63-42.38Q322.25-680 347-680h105q24.75 0 42.38 17.62Q512-644.75 512-620v280q0 24.75-17.62 42.37Q476.75-280 452-280Zm-105-60h105v-280H347v280Zm228 60v-60h165v-114H635q-24.75 0-42.37-17.63Q575-489.25 575-514v-106q0-24.75 17.63-42.38Q610.25-680 635-680h165v60H635v106h105q24.75 0 42.38 17.62Q800-478.75 800-454v114q0 24.75-17.62 42.37Q764.75-280 740-280H575Z"/></svg>](https://apps.apple.com/us/app/google-ai-edge-gallery/id6749645337) | [<svg xmlns="http://www.w3.org/2000/svg" height="72px" viewBox="0 -960 960 960" width="72px" fill="currentColor"><path d="M320-120v-40l80-80H160q-33 0-56.5-23.5T80-320v-440q0-33 23.5-56.5T160-840h640q33 0 56.5 23.5T880-760v440q0 33-23.5 56.5T800-240H560l80 80v40H320ZM160-440h640v-320H160v320Zm0 0v-320 320Z"/></svg>](https://developers.google.com/edge/foresight) | [<svg xmlns="http://www.w3.org/2000/svg" height="72px" viewBox="0 -960 960 960" width="72px" fill="currentColor"><path d="M838-79 710-207v103h-60v-206h206v60H752l128 128-42 43Zm-358-1q-83 0-156-31.5T197-197q-54-54-85.5-126.36T80-478q0-83.49 31.5-156.93Q143-708.36 197-762.68 251-817 324-848.5 397-880 480-880t156 31.5q73 31.5 127 85.82 54 54.32 85.5 127.75Q880-561.49 880-478q0 23-2 44.5t-7 43.5h-63q6-21.67 9-43.33 3-21.67 3-44.47 0-22.8-2.95-45.6-2.94-22.8-8.83-45.6H648q2 23 4 45.5t2 45q0 22.5-1.25 44.5T649-390h-61q3-22 4.5-44t1.5-44q0-22.75-1.5-45.5T588-569H373.42q-3.42 23-4.92 45.5t-1.5 45q0 22.5 1.5 44.5t4.5 44h197v60H384q14 53 34 104t62 86q23 0 45-2.5t45-7.5v60q-23 5-45 7.5T480-80ZM151.78-390H312q-2.5-22-3.75-44T307-478q0-22.75 1-45.5t3-45.5H151.71q-5.85 22.8-8.78 45.6-2.93 22.8-2.93 45.6t2.95 44.47q2.94 21.66 8.83 43.33ZM172-629h149.59q11.41-48 28.91-93.5T395-810q-71 24-129.5 69.5T172-629Zm222 478q-26-41-43.5-86T323-330H172q33 67 91 114t131 65Zm-10-478h193q-13-54-36-104t-61-89q-38 40-61 89.5T384-629Zm255.34 0H788q-35-66-93-112t-129-68q27 41 44.5 86.5t28.84 93.5Z"/></svg>](https://google-ai-edge.github.io/LiteRT-LM/web_demos/embedding_search/index.html) |
| :---: | :---: | :---: | :---: |
| <div align="center">[Android](https://play.google.com/store/apps/details?id=com.google.ai.edge.gallery&pli=1)</div> | <div align="center">[iOS](https://apps.apple.com/us/app/google-ai-edge-gallery/id6749645337)</div> | <div align="center">[macOS](https://developers.google.com/edge/foresight)</div> | <div align="center">[Web](https://google-ai-edge.github.io/LiteRT-LM/web_demos/embedding_search/index.html)</div> |
</div>

Ready to integrate this into your product? Get started [here](https://developers.google.com/edge/litert-lm/overview).

## Try EmbeddingGemma 2 with MediaPipe

MediaPipe uses EmbeddingGemma 2 and LiteRT-LM to enable high-level, cross-platform tasks which you can experience firsthand with the following interactive web demos:
* [Semantic image search](https://google-ai-edge.github.io/mediapipe-samples-web/#/retrieval/semantic_retriever) powered by MediaPipe Universal Embedder and Semantic Retriever task.
* [Decision making](https://google-ai-edge.github.io/mediapipe-samples-web/#/decision/decision_maker) powered by MediaPipe Decision Maker.

## Model Specifications

| | EmbeddingGemma 2<br>Text 270M | EmbeddingGemma 2<br>Text Vision 440M | EmbeddingGemma 2<br>740M |
|---|---|---|---|
| **Supported Modalities** | Text | Text, Images | Text, Images, Video, Audio |
| **Parameters** | *Total:* 270M<br>*Transformer:* 130M<br>*Embeddings:* 140M | *Total:* 440M<br>*Transformer:* 130M<br>*Embeddings:* 140M<br>*Vision Encoder:* 170M | *Total:* 740M<br>*Transformer:* 130M<br>*Embeddings:* 140M<br>*Vision Encoder:* 170M<br>*Audio Encoder:* 300M |
| **Quantization Scheme** | *Transformer:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT)<br>*Embeddings:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT) | *Transformer:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT)<br>*Embeddings:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT)<br>*Vision Encoder:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int8 per-channel (QAT) | *Transformer:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT)<br>*Embeddings:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int4 per-channel (QAT)<br>*Vision Encoder:* <br>&nbsp;&nbsp;&nbsp;&nbsp;int8 per-channel (QAT)<br>*Audio Encoder:* <br>&nbsp;&nbsp;&nbsp;&nbsp;mixed int2/int4/int8 <br>&nbsp;&nbsp;&nbsp;&nbsp;per-channel (QAT) |
| **Download Size**  (CPU/GPU file) | 165 MB | 388 MB | 485 MB |
| **On-Demand Modality Loading** | - | Yes | Yes |
| **Supported Input Sizes** | *Text tokens:* 128, 256, 512, <br>&nbsp;&nbsp;&nbsp;&nbsp;1024, 2048, 8192 | *Text tokens:* 128, 256, 512, <br>&nbsp;&nbsp;&nbsp;&nbsp;1024, 2048, 8192<br>*Image soft tokens:* 70, 140 | *Text tokens:* 128, 256, 512, <br>&nbsp;&nbsp;&nbsp;&nbsp;1024, 2048, 8192<br>*Image soft tokens:* 70, 140<br>*Audio soft tokens:* 12 |
| **Supported Output Sizes** | 128 <small>(512 bytes)</small><br> 256 <small>(1024 bytes)</small><br> 512 <small>(2048 bytes)</small><br> 768 <small>(3072 bytes)</small> | 128 <small>(512 bytes)</small><br> 256 <small>(1024 bytes)</small><br> 512 <small>(2048 bytes)</small><br> 768 <small>(3072 bytes)</small> | 128 <small>(512 bytes)</small><br> 256 <small>(1024 bytes)</small><br> 512 <small>(2048 bytes)</small><br> 768 <small>(3072 bytes)</small> |
| **Link** | [litert-community/embeddinggemma-2-text-270m-litert-lm](https://huggingface.co/litert-community/embeddinggemma-2-text-270m-litert-lm) | [litert-community/embeddinggemma-2-text-vision-440m-litert-lm](https://huggingface.co/litert-community/embeddinggemma-2-text-vision-440m-litert-lm) | [litert-community/embeddinggemma-2-740m-litert-lm](https://huggingface.co/litert-community/embeddinggemma-2-740m-litert-lm) |

Additional Notes:
* LiteRT-LM automatically scales and patchifies images of any size to fit EmbeddingGemma 2's vision encoder model.
* LiteRT-LM supports EmbeddingGemma 2's streamed audio allowing a variety of different audio lengths.

## EmbeddingGemma 2 Performance on LiteRT-LM

The text performance was measured by loading and running the 128 text signature. For vision benchmarking, the vision encoder used the 70 signature. The audio file for the `Text + Audio` run was 10 seconds long while the file for `Text + Audio + Vision` was 5 seconds. The latency reported is the average of 5 iterations.

Memory was measured with each platform's native metrics and is *not* directly comparable across operating systems. CPU memory was measured using, `rusage::ru_maxrss` on Android, Linux and IOT, `task_vm_info::phys_footprint` on iOS and MacBook, and `process_memory_counters::PrivateUsage` on Windows. With the exception of `task_vm_info::phys_footprint`, accelerator (GPU/NPU/TPU) memory is not included. Memory measurements were taken from the second load which reads from loading caches. Memory usage on the first load may vary.


**Android**


| Device  | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Google Pixel 11 Pro | TPU | 8.3 ms | 49 ms | 193.5 ms | 149 ms |
| S26 Ultra | CPU | 27.1 ms | 175 ms | 305 ms | 322 ms |
| S26 Ultra | GPU | 25.9  ms | 119 ms | 350 ms | 324 ms |

| Device  | Backend | Text CPU&nbsp;memory | Text + Vision CPU&nbsp;memory | Text + Audio CPU&nbsp;memory | Text + Vision + Audio CPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Google Pixel 11 Pro | TPU | 112 MB | 125 MB | 121 MB | 127.5 MB |
| S26 Ultra | CPU | 334 MB | 694 MB | 465 MB | 811 MB |
| S26 Ultra | GPU | 333 MB | 427 MB | 407 MB | 493 MB |

**iOS**

| Device | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| iPhone 18 Pro | CPU | 41.8 ms | 191 ms | 445 ms | 400 ms |
| iPhone 18 Pro | GPU | 11.6 ms | 69.8 ms | 165 ms | 150 ms |

| Device  | Backend | Text CPU/GPU&nbsp;memory | Text + Vision CPU/GPU&nbsp;memory | Text + Audio CPU/GPU&nbsp;memory | Text + Vision + Audio CPU/GPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| iPhone 18 Pro | CPU | 84 MB | 196 MB | 98 MB | 196 MB |
| iPhone 18 Pro | GPU | 85 MB | 196 MB | 96 MB | 226 MB |

**Linux**

| Device | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Arm 2.3 & 2.8GHz | CPU | 105 ms | 825 ms | 947 ms | 1251 ms |
| NVIDIA GeForce RTX 4090 | GPU | 7.6 ms | 23.9 ms | 169 ms | 112 ms |

| Device | Backend | Text CPU&nbsp;memory | Text + Vision CPU&nbsp;memory | Text + Audio CPU&nbsp;memory | Text + Vision + Audio CPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Arm 2.3 & 2.8GHz | CPU | 310 MB | 647 MB | 431 MB | 764 MB |
| NVIDIA GeForce RTX 4090 | GPU | 528 MB | 678 MB | 654 MB | 811 MB |

**macOS**

| Device  | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| MacBook Pro M5 | CPU | 31.3 ms | 151 ms | 314 ms | 432 ms |
| MacBook Pro M5 | GPU | 9.5 ms | 37.3 ms | 195 ms | 131 ms |

| Device  | Backend | Text CPU/GPU&nbsp;memory | Text + Vision CPU/GPU&nbsp;memory | Text + Audio CPU/GPU&nbsp;memory | Text + Vision + Audio CPU/GPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| MacBook Pro M5 | CPU | 165 MB | 310 MB | 201 MB | 336 MB |
| MacBook Pro M5 | GPU | 233 MB | 403 MB | 320 MB | 478 MB |

**Windows**

| Device  | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Dell XPS 16 (Intel Core Ultra Series 3) | CPU | 71.7 ms | 338 ms | 813 ms | 708 ms |
| Dell XPS 16 (Intel Core Ultra Series 3) | GPU | 19.2 ms | 62.5 ms | 284 ms | 205 ms |
| Dell XPS 16 (Intel Core Ultra Series 3) | Running Intel OpenVINO NPU | 13.3 ms | 49.8 ms | 124.3 ms | 108.6 ms |

| Device | Backend | Text CPU&nbsp;memory | Text + Vision CPU&nbsp;memory | Text + Audio CPU&nbsp;memory | Text + Vision + Audio CPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Dell XPS 16 (Intel Core Ultra Series 3) | CPU | 211 MB | 342 MB | 242 MB | 369 MB |
| Dell XPS 16 (Intel Core Ultra Series 3) | GPU | 822 MB | 1769 MB | 1047 MB | 1962 MB |
| Dell XPS 16 (Intel Core Ultra Series 3) | Running Intel OpenVINO NPU | 201 MB | 394 MB | 288 MB | 503 MB |

**Web**

| Device | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| MacBook Pro M5 | GPU | 21.8 ms | 107 ms | 228 ms | 226 ms |

**IoT**

| Device | Backend | Text latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Text + Vision + Audio latency &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Raspberry Pi 5 16GB | CPU | 161 ms | 1761 ms | 946 ms | 2304 ms |
| Jetson Orin Nano | CPU | 207 ms | 1741 ms | 1659 ms | 2507 ms |
| Jetson Orin Nano | GPU | 88 ms | 485 ms | 1195 ms | 1069 ms |
| Arduino VENTUNO Q | NPU | 13.6 ms | 135 ms | - \* | - \* |

| Device  | Backend | Text CPU&nbsp;memory | Text + Vision CPU&nbsp;memory | Text + Audio CPU&nbsp;memory | Text + Vision + Audio CPU&nbsp;memory |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Raspberry Pi 5 16GB | CPU | 282 MB | 619 MB | 408 MB | 736 MB |
| Jetson Orin Nano | CPU | 302 MB | 627 MB | 417 MB | 741 MB |
| Jetson Orin Nano | GPU | 523 MB | 1103 MB | 755 MB | 1228 MB |
| Arduino VENTUNO Q | NPU | 206 MB | 460 MB | - \* | - \* |

<small>
* Audio modality is not supported on the IQ-8275 NPU so this metric is omited.
</small>