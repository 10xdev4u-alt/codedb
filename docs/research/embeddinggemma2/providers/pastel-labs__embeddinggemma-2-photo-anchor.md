---
license: cc-by-4.0
tags:
- embeddinggemma
- embeddings
- quantization
- binary-quantization
- image-retrieval
base_model: google/embeddinggemma-2
---

# EmbeddingGemma 2 photo anchor

Published by Pastel Labs, the public research side of Pastel-Cloud OÜ ([pastel-labs.com](https://pastel-labs.com)).

This repository holds an average photo vector (the anchor) for [EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2), Google's embedding model, and 4-bit calibration tables built around it. Subtract the anchor from photo vectors before storing them at 1 or 4 bits per number. In our COCO test at 768 numbers per photo, 4 bits kept 0.997 of full-precision search quality, and 1 bit kept 0.954, or 0.998 after re-ranking the top 20. At 768 numbers per photo, 1 bit is 96 bytes and 4 bits is 384 bytes, against 3,072 bytes for 32-bit floats.

Files cover vector sizes 768, 512, 256 and 128.

## Files

| path | contents |
|---|---|
| `anchors/half-precision-model/photo_anchor_{d}.f32.bin` | anchor for size d, 32-bit floats, little-endian, no header |
| `anchors/half-precision-model/photo_anchor_{d}.f16.bin` | the same anchor as 16-bit floats |
| `anchors/half-precision-model/*.npy`, `photo_anchor.json` | the same values as NumPy arrays and JSON |
| `calibration-4bit/half-precision-model/quant4_{d}.f32.bin` | 4-bit table: d offsets, then d scales, 32-bit floats |
| `calibration-4bit/half-precision-model/quant4_{d}.json` | the same table as JSON, with the encode and decode rule |
| `manifest.json` | model revisions, method, photo counts and SHA-256 checksums of every file |
| `data/anchor_image_ids.json`, `data/heldout_image_ids.json` | COCO image ids used for the anchor and held out for testing |
| `data/photo_credits.csv` | Flickr URL and license of each anchor photo |
| `data/*.json` | full test results |
| `scripts/compute_anchor.py`, `scripts/quant4.py` | the averaging code and the 4-bit encode and decode code |

## Quick start

Embed photos with no text prefix. Embed search text with the prefix `task: search result | query: `. For size d, keep the first d numbers and rescale to length 1. Subtract the same anchor from photos and queries. Keep the query as 32-bit floats.

Python, 1 bit and 4 bits:

```python
import numpy as np

d = 768
anchor = np.fromfile("anchors/half-precision-model/photo_anchor_768.f32.bin", dtype="<f4")
table = np.fromfile("calibration-4bit/half-precision-model/quant4_768.f32.bin", dtype="<f4")
offset, scale = table[:d], table[d:]

def unit(v):
    v = np.asarray(v, np.float32)[:d]
    return v / np.linalg.norm(v)

# 1 bit: 96 bytes per photo. The first number is the highest bit of byte 0.
def photo_bits(photo_vec):
    return np.packbits(unit(photo_vec) - anchor > 0)

def scores_1bit(query_vec, bits):                     # bits: [n_photos, d // 8] uint8
    q = unit(query_vec) - anchor
    signs = np.unpackbits(bits, axis=1)[:, :d].astype(np.float32) * 2 - 1
    return signs @ q                                  # higher is better

# 4 bits: 384 bytes per photo. Two codes per byte, the first number in the high half.
def photo_codes(photo_vec):
    c = np.clip(unit(photo_vec) - anchor, offset, offset + 15 * scale)
    codes = np.clip(np.rint((c - offset) / scale), 0, 15).astype(np.uint8)
    return (codes[0::2] << 4) | codes[1::2]

def scores_4bit(query_vec, packed):                   # packed: [n_photos, d // 2] uint8
    codes = np.empty((len(packed), d), np.float32)
    codes[:, 0::2] = packed >> 4
    codes[:, 1::2] = packed & 15
    return (anchor + offset + codes * scale) @ unit(query_vec)
```

JavaScript, 1 bit:

```js
const d = 768;
const anchor = new Float32Array(await (await fetch("anchors/half-precision-model/photo_anchor_768.f32.bin")).arrayBuffer());

function centered(vec) {                // vec: Float32Array with at least d numbers
  let n = 0;
  for (let i = 0; i < d; i++) n += vec[i] * vec[i];
  n = Math.sqrt(n);
  const out = new Float32Array(d);
  for (let i = 0; i < d; i++) out[i] = vec[i] / n - anchor[i];
  return out;
}

function photoBits(vec) {               // returns 96 bytes for d = 768
  const c = centered(vec), bits = new Uint8Array(d / 8);
  for (let i = 0; i < d; i++) if (c[i] > 0) bits[i >> 3] |= 0x80 >> (i & 7);
  return bits;
}

function score(queryVec, bits) {        // higher is better
  const q = centered(queryVec);
  let s = 0;
  for (let i = 0; i < d; i++) s += (bits[i >> 3] & (0x80 >> (i & 7))) ? q[i] : -q[i];
  return s;
}
```

Which setting to use: the default is size 768 at 4 bits (384 bytes per photo). It scored 0.997 of full precision on 10,000 photos and 0.995 on 100,000 photos without re-ranking. Size 256 at 4 bits (128 bytes per photo) scored 0.985 on 10,000 photos but 0.964 on 100,000, so we recommend it only for libraries up to about 10,000 photos. The same anchor works for the half-precision model and the 4-bit on-device model (see "One anchor for both models").

To speed up 1-bit search, precompute for each group of 8 query numbers a 256-entry table of partial sums. Each photo then costs d / 8 table lookups. For collections of thousands of photos or more, keep full vectors on disk and re-rank the top 20.

## How we did it

### The problem

EmbeddingGemma 2 turns a photo into a list of 768 numbers (a vector) of length 1. Photos with similar content get vectors that point in similar directions. To fit many photos on a phone, you can keep only the sign of each number. That is 1 bit per number, or 96 bytes per photo.

EmbeddingGemma 2 photo vectors all point roughly the same way. Across 10,000 COCO (Common Objects in Context) photos, the average cosine similarity between two different photos is 0.60. Across 1,000 Flickr8k photos it is 0.63. Many of the numbers have the same sign for almost every photo, so those bits carry little information about which photo is which.

### Centering

We subtract a typical photo vector (the anchor) from every photo vector before taking signs. After that, each number is positive for some photos and negative for others, and the bits separate photos better. The search text is centered on the same anchor. A collection could compute its own average, but it needs photos first, and every device that searches the collection must use the same value. A fixed public anchor works from the first photo and is the same everywhere.

### Building the anchor

We used COCO 2017 train (118,287 photos). With `numpy.random.default_rng(42)` we set aside 10,000 photos for testing. The anchor does not include them. Of the rest, we used only the 18,232 photos whose Flickr license is CC BY 2.0 (Creative Commons Attribution, 17,805 photos) or "No known copyright restrictions" (427 photos).

We ran `google/embeddinggemma-2` at revision `914f7f89142e33e77833254d9c9b90c3cef7303b` through Sentence Transformers with half-precision (float16) weights on a graphics processor (GPU), giving one 768-number vector per photo. For each size d (768, 512, 256, 128) we kept the first d numbers, scaled the result back to length 1, and averaged over the photos. We did not rescale the average. Its length is 0.777 at 768, 0.781 at 512, 0.790 at 256 and 0.865 at 128.

An anchor built from all 108,287 non-test photos, with any license, points the same way (cosine similarity 0.9999) and scored within 0.006 of the CC BY anchor in our tests.

### Storage formats tested

Each photo vector x (length 1, size d) is stored in one of three ways. The search text q stays as 32-bit floats in every case.

With 1 bit per number, we store 1 where x minus the anchor is above 0, else 0. The score is the sum of (q minus anchor) over the 1 bits, minus the same sum over the 0 bits.

With 4 bits per number, we compute c = x minus anchor. For each position i, clip c to a range [offset_i, offset_i + 15 * scale_i] and round to one of 16 evenly spaced levels: code = round((c - offset_i) / scale_i), from 0 to 15. To score, rebuild x as anchor + offset + code * scale and take the dot product with q. The offsets and scales come from the 18,232 anchor photos only. offset_i is the 0.5th percentile of c at position i and offset_i + 15 * scale_i is the 99.5th percentile. We picked the 0.5th percentile from the candidates 0.1, 0.25, 0.5, 1 and 2 because it gave the smallest mean squared reconstruction error on the anchor photos. The test photos and queries played no part in this choice. The tables are in `calibration-4bit/`.

With 16 bits per number, we store x as half-precision floats (the IEEE 754 binary16 format) and score with the dot product.

To re-rank, we take the top k photos by the stored-code score, then reorder those k by full-precision cosine similarity. This needs the full vectors stored somewhere, for example on disk.

### Test setup

We searched the 10,000 held-out COCO photos with 1,000 queries. The queries are the first COCO captions of 1,000 of those photos, chosen with seed 42, prefixed `task: search result | query: `. The correct answer is the photo the caption describes.

The score is normalized discounted cumulative gain at 10 (nDCG@10). With one correct photo per query, a query scores 1 if that photo ranks first, 1/log2(r + 1) if it ranks r-th within the top 10, and 0 below. We report it as a share of the score from full-precision cosine search on the same photos and queries. Recall@1 and Recall@10 are the share of queries whose photo ranks first or within the top 10. Ties go to the photo with the lower index. A share above 1.000 means the compressed search happened to rank the correct photo higher than full precision did on a few queries.

As a second collection, we used 1,000 Flickr8k photos with 100 caption queries, encoded twice: with the half-precision model above and with the 4-bit on-device model `onnx-community/embeddinggemma-2-ONNX` (Open Neural Network Exchange format, q4 files, revision `daa72c51243991dfcaf9f9137d2c573d8f7790c0`) run in Transformers.js on a regular processor (CPU). The anchor and 4-bit tables come from the half-precision model in both cases.

### Results

In every table, score means nDCG@10 (a top-10 ranking score) as a share of full-precision search on the same photos and queries.

#### COCO, 10,000 photos, 1,000 queries, half-precision model

| size | storage | bytes per photo | stored codes only: score / Recall@1 / Recall@10 | re-rank top 20: score / Recall@1 / Recall@10 | re-rank top 10 | re-rank top 50 |
|---|---|---|---|---|---|---|
| 768 | full precision (32-bit floats) | 3,072 | 1.000 / 0.468 / 0.796 | | | |
| 768 | 1 bit | 96 | 0.954 / 0.440 / 0.770 | 0.998 / 0.468 / 0.794 | 0.983 | 1.001 |
| 768 | 4 bits | 384 | 0.997 / 0.469 / 0.796 | 1.000 / 0.468 / 0.796 | 1.000 | 1.000 |
| 768 | 16 bits (half precision) | 1,536 | 0.999 / 0.467 / 0.795 | 1.000 / 0.468 / 0.796 | 1.000 | 1.000 |
| 768 | 1 bit, no centering | 96 | 0.939 / 0.428 / 0.763 | 0.995 / 0.466 / 0.790 | 0.985 | 1.000 |
| 256 | full precision (32-bit floats) | 1,024 | 1.000 / 0.455 / 0.772 | | | |
| 256 | 1 bit | 32 | 0.842 / 0.351 / 0.688 | 0.975 / 0.454 / 0.736 | 0.941 | 0.994 |
| 256 | 4 bits | 128 | 0.985 / 0.447 / 0.761 | 1.000 / 0.455 / 0.772 | 0.995 | 1.000 |
| 256 | 16 bits (half precision) | 512 | 1.000 / 0.455 / 0.772 | 1.000 / 0.455 / 0.772 | 1.000 | 1.000 |
| 256 | 1 bit, no centering | 32 | 0.813 / 0.343 / 0.659 | 0.975 / 0.456 / 0.727 | 0.916 | 0.989 |

#### Flickr8k, 1,000 photos, 100 queries, size 768

| storage (768) | half-precision model: stored codes only | half-precision model: re-rank top 20 | 4-bit model: stored codes only | 4-bit model: re-rank top 20 |
|---|---|---|---|---|
| 1 bit | 0.990 | 0.996 | 0.972 | 1.000 |
| 4 bits | 1.001 | 1.000 | 1.006 | 1.000 |
| 16 bits (half precision) | 1.000 | 1.000 | 1.000 | 1.000 |
| 1 bit, no centering | 0.986 | 0.996 | 0.979 | 1.000 |

At 256, 1 bit scores 0.917 with the half-precision model and 0.935 with the 4-bit model; 4 bits score 0.989 and 1.011.

#### Narrow collections

To get closer to a personal photo library, we grouped held-out COCO photos by their object labels and searched each group with 100 of its own captions. Size 768, 1 bit, no re-ranking.

| collection | photos | public anchor | the collection's own average | own average of 20 photos |
|---|---|---|---|---|
| dogs or cats | 676 | 0.968 | 0.939 | 0.950 |
| food | 1,394 | 0.957 | 0.962 | 0.956 |
| home interiors without people | 1,330 | 0.943 | 0.960 | 0.957 |
| street scenes with vehicles | 2,337 | 0.978 | 0.986 | 0.968 |
| people | 5,477 | 0.936 | 0.944 | 0.899 |
| sports | 2,003 | 0.961 | 0.914 | 0.916 |

#### COCO, 100,000 photos, 1,000 queries, half-precision model

We added 90,000 more COCO train photos to the 10,000 test photos and ran the same 1,000 queries. 15,134 of the added photos are also anchor photos. Full-precision Recall@1 drops to 0.266 at 768 and 0.242 at 256, because each query now has 10 times as many wrong photos to rank above the right one.

| size | storage | bytes per photo | stored codes only: score / Recall@1 / Recall@10 | re-rank top 20: score / Recall@1 / Recall@10 |
|---|---|---|---|---|
| 768 | full precision (32-bit floats) | 3,072 | 1.000 / 0.266 / 0.528 | |
| 768 | 1 bit | 96 | 0.895 / 0.214 / 0.500 | 0.999 / 0.266 / 0.529 |
| 768 | 4 bits | 384 | 0.995 / 0.261 / 0.532 | 1.000 / 0.266 / 0.528 |
| 256 | 4 bits | 128 | 0.964 / 0.231 / 0.490 | 0.998 / 0.242 / 0.502 |

#### COCO, 10,000 photos encoded with the 4-bit model

These are the same 10,000 test photos, encoded with the 4-bit on-device model at 280 image tokens. The queries come from the half-precision model, so queries and photos come from different model precisions. The anchor and 4-bit tables come from the half-precision model. "Phone-made queries" below repeats the main settings with queries from the 4-bit model.

| size | storage | stored codes only | re-rank top 20 |
|---|---|---|---|
| 768 | 1 bit | 0.955 | 1.000 |
| 768 | 4 bits | 0.995 | 1.000 |
| 768 | 16 bits (half precision) | 1.000 | 1.000 |
| 768 | 1 bit, no centering | 0.930 | 0.995 |
| 256 | 1 bit | 0.859 | 0.985 |
| 256 | 4 bits | 0.988 | 1.000 |
| 256 | 16 bits (half precision) | 1.000 | 1.000 |
| 256 | 1 bit, no centering | 0.817 | 0.978 |

#### Phone-made queries

We encoded the same 1,000 COCO caption queries with the 4-bit text model (`onnx-community/embeddinggemma-2-ONNX`, q4 files) in Transformers.js on a regular processor, with the same `task: search result | query: ` prefix. Their cosine similarity to the half-precision-model queries averages 0.992 (lowest 0.978). The table searches the 10,000 test photos at size 768 with the published anchor and 4-bit table. Each score is a share of full-precision search with the same queries and photos. The first row is fully phone-made: photos and queries both come from the 4-bit model.

| photos | queries | full precision Recall@1 | 4 bits | 1 bit | 1 bit, re-rank top 20 |
|---|---|---|---|---|---|
| 4-bit model | 4-bit model | 0.461 | 1.000 | 0.963 | 0.998 |
| 4-bit model | half-precision model | 0.463 | 0.995 | 0.955 | 1.000 |
| half-precision model | 4-bit model | 0.468 | 0.996 | 0.949 | 0.999 |
| half-precision model | half-precision model | 0.468 | 0.997 | 0.954 | 0.998 |

These scores show what each storage setting costs on the same model setup. They do not compare the two models. For that, read the full-precision Recall@1 column: fully phone-made search puts the right photo first 46.1% of the time, and the half-precision model does so 46.8% of the time.

#### One anchor for both models

We checked whether the 4-bit on-device model needs its own anchor. We lost our 4-bit-model encode of the 18,232 anchor photos, so we used a split of the 10,000 held-out photos instead. With seed 42, we put the 1,000 query photos and 4,000 other held-out photos in a search set, and averaged the remaining 5,000 photos (4-bit-model vectors, 280 image tokens) into a test anchor. We then searched the 5,000-photo search set with that test anchor and with the published anchor. Both runs use the published 4-bit table, which was fitted to half-precision-model vectors. The queries come from the half-precision model.

The two anchors have cosine similarity 0.9929 at 768 and 0.9947 at 256.

| size | storage | re-rank | 4-bit-model anchor: score / Recall@1 / Recall@10 | half-precision-model anchor: score / Recall@1 / Recall@10 | difference |
|---|---|---|---|---|---|
| 768 | 1 bit | none | 0.952 / 0.498 / 0.836 | 0.963 / 0.510 / 0.843 | -0.010 |
| 768 | 1 bit | top 20 | 0.997 / 0.548 / 0.846 | 0.999 / 0.548 / 0.849 | -0.002 |
| 768 | 4 bits | none | 0.997 / 0.546 / 0.851 | 0.995 / 0.543 / 0.851 | +0.002 |
| 768 | 4 bits | top 20 | 1.000 / 0.548 / 0.852 | 1.000 / 0.548 / 0.853 | +0.000 |
| 256 | 1 bit | none | 0.865 / 0.416 / 0.752 | 0.877 / 0.426 / 0.756 | -0.012 |
| 256 | 1 bit | top 20 | 0.983 / 0.511 / 0.802 | 0.981 / 0.511 / 0.803 | +0.002 |
| 256 | 4 bits | none | 0.982 / 0.502 / 0.818 | 0.989 / 0.510 / 0.820 | -0.007 |
| 256 | 4 bits | top 20 | 1.000 / 0.513 / 0.833 | 1.000 / 0.513 / 0.833 | +0.000 |

At 768 the test anchor is at most +0.002 better than the published one, which is within our threshold of 0.005. One anchor serves both models, and this repository ships no separate 4-bit-model anchor files.

#### Smaller photo input

The image encoder can take a photo as 70 image tokens instead of 280, which is faster to run. With full-precision vectors from the 4-bit model on the 10,000 COCO held-out photos and the same 1,000 queries, 70 tokens reached 0.946 of the 280-token score (Recall@1 0.441 against 0.463). That is below our bar of 0.98. 70 tokens is faster but lower quality, and we do not recommend it. The queries come from the half-precision model.

#### What we take from this

At 768, 4 bits per number (384 bytes per photo) scored 0.997 of full precision on COCO with no re-ranking. 1 bit (96 bytes) scored 0.954 without re-ranking and 0.998 after re-ranking the top 20 with full vectors. Without centering, 1 bit scored 0.939. At 256, 1 bit loses more (0.842), and 4 bits scored 0.985.

### Limits

- We encoded the anchor photos with float16 weights. The EmbeddingGemma 2 model card advises bfloat16 or float32 because float16 can give missing values or less accurate vectors without any error. We found no missing values and every vector had length 1, but we did not compare against a bfloat16 or float32 run.
- Each narrow collection has 100 queries, so differences of about 0.02 are within noise.
- We tested up to 100,000 photos, and at that size only with the half-precision model. Larger collections may need 1-bit re-ranking deeper than the top 20.
- On Flickr8k with the 4-bit model, 1 bit with the anchor scored 0.972 against 0.979 with no centering. With 100 queries, that gap is within noise.
- We tested photos only. Screenshots, documents, video frames and audio may have a different average.
- The anchor and 4-bit tables belong to one model revision. Rebuild them if the model weights change.

## License and credits

The anchor files, calibration tables and test results in this repository are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) by Pastel-Cloud OÜ.

- The 18,232 photos come from the [COCO dataset](https://cocodataset.org/), taken by Flickr photographers and licensed under [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) or marked "No known copyright restrictions" ([Flickr Commons](https://www.flickr.com/commons/usage/)). `data/photo_credits.csv` lists the Flickr URL and license of each photo. COCO's metadata does not name the photographers. This repository contains no images, only an average of their vectors.
- The COCO captions and annotations are by the COCO Consortium, [CC BY 4.0](https://cocodataset.org/#termsofuse). Lin et al., "Microsoft COCO: Common Objects in Context", ECCV 2014.
- EmbeddingGemma 2 is by Google and is used under the [Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0) (see [Google's model card](https://huggingface.co/google/embeddinggemma-2)). The anchor and tables come from the model's outputs. Use of the model itself must follow the [Gemma Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy).
- The Flickr8k images and captions (Hodosh, Young and Hockenmaier, 2013) were used for testing only and are not included.
