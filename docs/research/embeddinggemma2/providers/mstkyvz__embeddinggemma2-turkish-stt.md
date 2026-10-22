---
language:
- tr
license: apache-2.0
base_model: google/embeddinggemma-2
pipeline_tag: automatic-speech-recognition
library_name: pytorch
tags:
- automatic-speech-recognition
- speech-to-text
- turkish
- ctc
- kenlm
- embeddinggemma
- frozen-encoder
datasets:
- google/fleurs
- wikimedia/wikipedia
metrics:
- wer
- cer
model-index:
- name: embeddinggemma2-turkish-stt
  results:
  - task:
      type: automatic-speech-recognition
      name: Speech Recognition
    dataset:
      type: google/fleurs
      name: FLEURS (tr_tr)
      config: tr_tr
      split: test
    metrics:
    - type: wer
      value: 15.5
      name: Test WER, v3 + LM + Zemberek (okunuş biçimi ref.)
    - type: wer
      value: 17.2
      name: Test WER, v3 + LM (okunuş biçimi ref.)
    - type: wer
      value: 26.3
      name: Test WER, v3 greedy (okunuş biçimi ref.)
    - type: wer
      value: 22.5
      name: Telefon simülasyonlu test WER, v3 + LM + Zemberek
---

# EmbeddingGemma 2 → Türkçe Konuşma Tanıma (STT)

**Bir gömme (embedding) modelini, ona hiç dokunmadan, Türkçe konuşma tanıma modeline çevirme denemesi.**

[`google/embeddinggemma-2`](https://huggingface.co/google/embeddinggemma-2) metni, sesi, görüntüyü ve videoyu
tek bir ortak vektör uzayına gömer. Konuşulan bir kelime, yazılı hâline yakın düşüyorsa transkripti doğrudan
bu modelin içinden okumak mümkün olmalı. Bu repo, o fikrin **Türkçe** için uygulanmış hâlidir:

- EmbeddingGemma 2 **donmuş** (ağırlıkları değişmedi).
- Üstüne yalnızca **8,3M parametrelik küçük bir okuyucu** eğitildi: modelin ses dilimlerinden (saniyede 25)
  Türkçe **harfleri** CTC ile okur.
- Türkçe Vikipedi'den kurulan bir **kelime 3-gram dil modeli** (KenLM, beam search) çıktıyı düzeltir,
  ardından **Zemberek** geçersiz kelimeleri düzeltir.
- Eğitim verisi: yalnızca **FLEURS Türkçe, 8,3 saat** + aynı seslerin **telefon simülasyonu** (8 kHz, G.711).
  Eğitim tek bir Apple M4 Pro dizüstünde yapıldı.
- **v3 (varsayılan):** telefon simülasyonu + okunuş biçimi hedefler (`normalizer-tr`: "2007" → "iki bin yedi").

> *English summary:* A frozen EmbeddingGemma 2 is turned into a Turkish speech recognizer by training only a
> tiny 8.3M-parameter character CTC reader on its per-frame (25 Hz) audio-token outputs, plus a Wikipedia
> word 3-gram LM for beam search, plus Zemberek spell-fix. Trained on 8.3 h of FLEURS Turkish (+ a simulated
> telephone copy) on a single MacBook (M4 Pro). v3: **15.5% WER on FLEURS tr test** (spoken-form refs; 22.5% on
> simulated 8 kHz telephone audio), **~72× real time** end-to-end. Small benchmark vs Whisper small (200 utts):
> 17.6% vs 16.0% WER clean, 25.3% vs 26.2% simulated telephone, with 8.3 h vs ~4,333 h of Turkish training audio.

---

## Sonuçlar

### v3 (varsayılan) — FLEURS Türkçe test, temiz ve telefon sesi

Referanslar okunuş biçiminde (sayılar yazıyla); normalizer'ın güvenilmez olduğu 14 cümle çıkarıldı → **729 kayıt**.
Aynı protokolle v1 de ölçüldü:

| Model | Çözümleme | **Temiz ses WER** | **Telefon (8 kHz sim.) WER** |
|---|---|---|---|
| v1 | greedy | %39,9 | %51,7 |
| v1 | + LM | %18,9 | %26,8 |
| v1 | + LM + Zemberek | %18,1 | — |
| **v3** | greedy | %26,3 (CER %5,5) | %37,3 (CER %8,7) |
| **v3** | + LM (`lm_spoken`) | %17,2 | %24,7 |
| **v3** | **+ LM + Zemberek** | **%15,5** | **%22,5** |

- v3 = sıfırdan, 30 epoch; eğitim: FLEURS train temiz (8,3 s) + aynısının telefon simülasyonu (8,3 s);
  hedefler okunuş biçimi. Model seçimi: temiz + telefon dev ortalaması.
- LM: okunuş biçimine çevrilmiş Vikipedi (`lm_spoken/`), alpha 0,7, beta 2,0 (dev'de seçildi).
- Telefon simülasyonu: 16→8 kHz, 300 Hz yüksek geçiren, G.711 μ-law 8 bit, ±6 dB kazanç, SNR 20–40 dB gürültü,
  tekrar 16 kHz. **Gerçek telefon kaydı değil**; gerçek çağrı seslerinde sonuç farklı olabilir.
- Zemberek yalnızca biçimbilimsel olarak geçersiz kelimelere dokunur; "olaşır" gibi geçerli-ama-yanlış kelimeleri
  düzeltmez.

### v1 — ilk sürüm (`v1/`), FLEURS orijinal referanslar

| Model | Çözümleme | Dev WER | Dev CER | **Test WER** | **Test CER** |
|---|---|---|---|---|---|
| **v1** | greedy | %39,3 | %8,0 | %37,9 | %7,7 |
| **v1** | **+ 3-gram LM** | **%16,6** | **%4,5** | **%16,1** | **%4,3** |
| v2 (`v2/`) | greedy | %33,6 | %6,8 | %32,9 | %6,7 |
| v2 (`v2/`) | + 3-gram LM | %18,6 | %4,7 | %18,8 | %4,6 |

- Test: 743 kayıt, dev: 338 kayıt. WER/CER, aşağıdaki normalizasyondan sonra hesaplandı
  (küçük harf, noktalamasız, Türkçe I/İ kuralları).
- Dil modeli ağırlıkları (alpha/beta) **sadece dev setinde** seçildi; test sadece raporlama için kullanıldı.
- **v2 neden kullanılmadı?** v2, v1'den 30 epoch daha eğitildi; tek başına (greedy) daha iyi ama dil modeliyle
  daha kötü. Muhtemel sebep: daha "emin" (sivri) olasılık dağılımları dil modelinin düzeltme alanını daraltıyor.
  Daha yüksek alpha değerleri (1,0–2,0) de denendi, iyileştirmedi.

### Hız

| Ölçüm | Değer |
|---|---|
| Uçtan uca (ham ses → metin), FLEURS test 200 kayıt, batch 16, bfloat16, Apple M4 Pro (MPS) | **72× gerçek zaman** (1 saat ses ≈ 50 sn) |
| Tek kayıt, 11–17 sn ses, dil modeliyle | ≈ 0,4–0,6 sn |
| Dil modeli beam search (743 kayıt, 4 süreç) | ≈ 3 sn toplam |

Hız ölçümü optimize edilmemiş PyTorch + sentence-transformers ön işlemesiyle yapıldı; ölçüm yöntemi farklı olduğu
için başka çalışmalardaki rakamlarla doğrudan karşılaştırılamaz.

### Parametreler

| Parça | Parametre | Durum |
|---|---|---|
| Ses kodlayıcı (EmbeddingGemma 2) | 300M | donmuş |
| Metin transformer'ı (EmbeddingGemma 2) | 130M | donmuş |
| Kelime tablosu (EmbeddingGemma 2) | 140M | donmuş, yalnız 4 özel token kullanılır |
| Görüntü kodlayıcı | 170M | **yüklenmez** |
| **Okuyucu (bu repo)** | **8,3M** | **eğitildi** |

Aynı donmuş model sesli arama / gömme için de kullanılmaya devam edebilir; STT için yalnızca ~33 MB'lık okuyucu
(ve isteğe bağlı dil modeli) eklenir.

### Örnek çıktılar (FLEURS test)

| | |
|---|---|
| **Referans** | valilik binasının dışında bir bomba patladı |
| Greedy | varlik binasının dışında bir bomba patladı |
| **+ LM** | valilik binasının dışında bir bomba patladı |
| **Referans** | del potro ikinci sette erken avantajı vardı ancak bu da 6-6'ya gelindikten sonra bir beraberlik molasını gerektirdi |
| Greedy | delpotro ikinci sete erken avantaji vardı ancak bu da a 6ya gelindiktan sonra bir beraberlik molasını gerektrdi |
| **+ LM** | delpotro ikinci sete erken avantajı vardı ancak bu da 6 aya gelindiktan sonra bir beraberlik molasını gerektirdi |
| **Referans** | melek 2006 kuruluşların daha yüksek bir performans seviyesine ulaşmasına yardımcı olarak kullanılan bir yöntem olan süreklilik yaklaşımını açıklar |
| **+ LM** | melek **parantez içinde** 2006 kuruluşların daha yüksek bir performans seviyesine ulaşmasına yardımcı olarak kullanılan bir yöntem olan süreklilik yaklaşımını açıklar |

Son örnekte konuşmacı gerçekten "parantez içinde" diyor; referans metinde yok. WER'in bir kısmı bu tür
referans farklarından gelir.

---

## Benchmark: Whisper small ile karşılaştırma

Aynı Mac'te (Apple M4 Pro, 24 GB, MPS), aynı kayıtlarla, ham sesten metne uçtan uca. `training/benchmark.py`.

| | **EmbeddingGemma 2 + okuyucu v3 (bu repo)** | **Whisper small** |
|---|---|---|
| Temiz ses WER | %17,6 (LM + Zemberek) · %19,1 (LM) · %29,0 (greedy) | **%16,0** |
| Telefon (8 kHz sim.) WER | **%25,3** (LM + Zemberek) · %27,5 (LM) · %40,5 (greedy) | %26,2 |
| Temiz ses CER | %4,7 | %4,2 |
| Hız (ham ses → metin) | ~95× gerçek zaman (LM + Zemberek) · ~110× (greedy) | ~115× gerçek zaman |
| **Türkçe eğitim sesi** | **8,3 saat** (FLEURS) + aynı 8,3 saatin telefon simülasyonu | **~4.333 saat** Türkçe (toplam 680.000 saat, 97 dil)¹ |
| Metin verisi | 20M kelime Türkçe Vikipedi (3-gram LM) | — (uçtan uca, ayrı LM yok) |
| Eğitilen parametre | **8,3M** (okuyucu) | 242M (tamamı) |
| Çıkarımda yüklü parametre | ~578M (donmuş EmbeddingGemma 2, görüntü kodlayıcısız) + 8,3M | 242M |
| Eğitim donanımı / süresi | 1 dizüstü (M4 Pro), okuyucu ~50 dk + özellik çıkarma ~25 dk | büyük ölçekli GPU kümesi (OpenAI) |
| Çözümleme | CTC (tek geçiş) + beam search | otoregresif (token token), greedy |

**Protokol:** FLEURS `tr_tr` test'ten, uzunluk dağılımını koruyan eşit aralıklı **200 kayıt (0,70 saat)**.
Referanslar ve *her iki sistemin* çıktısı aynı normalizasyondan geçer (`normalizer-tr` okunuş biçimi → küçük harf,
noktalamasız); "18" ile "on sekiz" farkı hata sayılmaz. Telefon sesi `extract.telephone` ile, kayıt adına bağlı
sabit tohumla üretildi. Whisper: `openai/whisper-small`, fp16, `language="tr"`, greedy, batch 16.
Bizim sistem: bfloat16, batch 16, LM tek süreçte. Model yükleme hariç, ısınma sonrası ölçüldü.

**Yorum ve uyarılar:**
- 200 kayıt küçük bir örneklem; birkaç puanlık farklar istatistiksel gürültü sınırında.
- **Bizim lehimize:** okuyucu FLEURS'un *kendi* train bölümüyle ve *tam bu* telefon simülasyonuyla eğitildi
  (alan içi); Whisper ikisini de görmeden (sıfır atış) çalıştı. Telefon sesindeki küçük üstünlük kısmen bundan.
- **Whisper lehine:** ~520 kat daha fazla Türkçe ses verisi ile eğitildi; noktalama ve büyük harf üretir
  (bu benchmark'ta normalizasyonla eşitlendi).
- Gerçek telefon/çağrı merkezi kaydında ölçülmedi.
- Özet: 8 saatlik veri ve 8M eğitilen parametreyle, donmuş bir *gömme* modeli Türkçe okuma konuşmasında
  Whisper small'a yakın sonuç veriyor; temiz seste geride, simüle telefonda başa baş. Asıl artı, zaten
  çalışan bir EmbeddingGemma 2'ye STT'nin ~33 MB'lık bir ek olarak gelmesi.

¹ Whisper Türkçe saat sayısı ikincil kaynaktan: [arXiv 2609.11772](https://arxiv.org/pdf/2609.11772),
Whisper makalesindeki dil tablosuna atıfla; toplam 680k saat [Whisper makalesi](https://cdn.openai.com/papers/whisper.pdf).

---

## Hızlı başlangıç

### Kurulum

```bash
pip install torch "transformers>=4.57" "sentence-transformers>=5.1" soundfile scipy pillow torchvision \
            huggingface_hub safetensors pyctcdecode "kenlm @ https://github.com/kpu/kenlm/archive/master.zip" \
            zemberek-python "setuptools>=77,<81"
```

`pillow` ve `torchvision`, EmbeddingGemma 2'nin işlemcisi (processor) tarafından sadece ses için bile istenir.
`kenlm` ve `pyctcdecode` yalnızca dil modelli çözümleme için gerekir (`--no-lm` ile atlanabilir).
`zemberek-python` isteğe bağlıdır (`--no-zemberek`); `pyctcdecode` gibi NumPy 1.x ister, `pkg_resources` için
`setuptools<81` gerekir. Kurulu değilse `stt.py` düzeltmesiz devam eder.

### Komut satırı

```bash
# repo'yu indir ve bir dosyayı yazıya dök (her formattaki ses 16 kHz mono'ya çevrilir)
python -c "from huggingface_hub import snapshot_download as s; print(s('mstkyvz/embeddinggemma2-turkish-stt'))"
python <indirilen_klasör>/stt.py kayit.wav                 # v3 + LM + Zemberek
python <indirilen_klasör>/stt.py kayit.wav --no-zemberek   # Zemberek'siz
python <indirilen_klasör>/stt.py kayit.wav --no-lm         # sadece okuyucu
python <indirilen_klasör>/stt.py kayit.wav --variant v1    # ilk sürüm
```

### Python

```python
import sys
from huggingface_hub import snapshot_download

path = snapshot_download("mstkyvz/embeddinggemma2-turkish-stt")
sys.path.insert(0, path)
from stt import TurkishSTT

stt = TurkishSTT.from_pretrained("mstkyvz/embeddinggemma2-turkish-stt")   # v3; use_lm=False → LM indirilmez
# stt = TurkishSTT.from_pretrained("mstkyvz/embeddinggemma2-turkish-stt", variant="v1")
print(stt.transcribe("kayit.wav"))
print(stt.transcribe(numpy_dizisi_16khz_mono))   # numpy float32 de kabul edilir
```

Uzun kayıtlar 30 saniyelik parçalara bölünerek işlenir (modelin tek seferlik sınırı ~327 sn).
Cihaz otomatik seçilir: CUDA → MPS → CPU. Model **bfloat16** ile çalışır (okuyucu bfloat16 özelliklerle
eğitildi; EmbeddingGemma 2 model kartı float16'yı önermiyor).

---

## Nasıl çalışır

```
ses (16 kHz mono)
  │
  ▼
EmbeddingGemma 2 ses kodlayıcı (300M, donmuş)  ──►  25 ses token'ı / sn
  │  embed_audio izdüşümü
  ▼
EmbeddingGemma 2 metin transformer'ı (24 katman, çift yönlü, donmuş)
  │  her ses token'ı için 4 katmanın çıktısı alınır:
  │    h0   giriş (ses gömmesi)          512
  │    h8   8. katman                     512
  │    h16  16. katman                    512
  │    last son katman, 768-boyutlu ortak uzay   768
  ▼  birleştir → 2304 boyut / dilim, standartlaştır
Okuyucu (8,3M, eğitilen tek parça)
  LayerNorm → Dropout → Linear(2304→384)
  ConvTranspose1d ×2 zaman açma (25 → 50 dilim/sn; Türkçe ~15 harf/sn CTC için)
  derinlemesine Conv1d (k=5) artık bağlantı
  4 × Transformer encoder (d=384, 6 kafa, FFN 1536, pre-norm, GELU)
  LayerNorm → Linear(384→45)  →  log-softmax
  ▼
CTC  (45 sembol: blank, boşluk, ', 32 harf, 10 rakam)
  ▼
greedy  veya  beam search (64) + Türkçe kelime 3-gram LM (alpha 0,5, beta 0)
```

**Neden kelime değil de harf?** Orijinal fikirde okuyucu, modelin metin uzayındaki ~229 bin kelimeden en yakınını
seçiyordu. Türkçe sondan eklemeli bir dil (*gel, geldim, gelemedim, gelemeyeceklermiş…*); sabit bir kelime listesi
çok sayıda kelime biçimini kapsamaz. Harf düzeyi CTC sözlük sorununu ortadan kaldırır, dil modeli de kelime
düzeyinde düzeltme yapar.

**Neden 4 katman?** 5 epoch'luk karşılaştırmada yalnız `last + h16` dev WER %74,5 / CER %20,4 verirken
`h0 + h8 + h16 + last` %59,2 / %13,2 verdi. Son katman anlamsal (cümle gömmesi için ortalama alınan katman),
ara katmanlar akustik ayrıntıyı daha iyi taşıyor.

---

## Adım 0: Model Türkçe konuşmayı "anlıyor" mu?

Okuyucu eğitmeden önce, EmbeddingGemma 2'nin Türkçe sesi Türkçe metne yakın gömüp gömmediği ölçüldü
(FLEURS dev, ses → metin erişimi, cümle gömmeleri, metne `title: none | text: ` öneki):

| Ses → metin | Sorgu / aday | R@1 | R@10 |
|---|---|---|---|
| Türkçe → Türkçe | 338 / 145 | **%97,9** | %99,7 |
| İngilizce → İngilizce | 394 / 150 | %100 | %100 |
| Türkçe ses → İngilizce çeviri | 338 / 150 | %93,8 | %98,8 |
| İngilizce ses → Türkçe çeviri | 381 / 145 | %99,2 | %100 |
| Rastgele | – | %0,7 | – |

Cümle gömmesi anlamı çok iyi yakalıyor, ancak ince ekleri ayırt etmiyor: aynı kayıt için
"…madalya **kazanamadı**" 0,810, "…madalya **kazandı**" 0,808 skor aldı. Bu yüzden STT için cümle gömmesi
yerine **dilim bazındaki** (zaman adımı) çıktılar kullanıldı.

---

## Eğitim detayları

### Veri

| | |
|---|---|
| Eğitim | FLEURS `tr_tr` train: 2.526 kayıt, **8,31 saat**, 747.574 dilim |
| Doğrulama | FLEURS `tr_tr` dev: 338 kayıt |
| Test | FLEURS `tr_tr` test: 743 kayıt |
| Hedef metin | FLEURS `transcription` (normalize) sütunu |

**Normalizasyon** (`reader.normalize`): Türkçe kurallı küçük harf (I→ı, İ→i), Unicode NFC, birleşik noktalı
"i̇" → "i", aksanlı harfler (â, î, û, é…) sadeleştirilir, ’ → ', kalan karakterler boşluğa, tek boşluk.

### Özellik çıkarma (`training/extract.py`)

- EmbeddingGemma 2, bfloat16, MPS. Sentence-transformers ön işlemesi, ardından `EmbeddingGemma2Model`'in
  `output_hidden_states=True` ile ileri geçişi.
- Yalnızca ses token'larının (`audio_token_id`) konumları alınır; `<bos>`, `<|audio>`, `<audio|>`, `<eos>` atılır.
- Batch ile tekil işleme arasındaki fark: kosinüs ≥ 0,99 (bf16 gürültüsü).

### Okuyucu eğitimi (`training/train.py`)

| Hiperparametre | v1 | v2 |
|---|---|---|
| Başlangıç | rastgele (seed 0) | v1 |
| Optimizasyon | AdamW, lr 1e-3, wd 0,01 | AdamW, lr 5e-4, wd 0,01 |
| Takvim | 500 adım ısınma + kosinüs (40 epoch planlı) | ısınma + kosinüs, 30 epoch |
| Batch | ~6.000 dilim | ~4.000 dilim, sabit şekilli kovalar |
| Düzenlileştirme | dropout 0,15, gradyan kırpma 1,0 | aynı |
| Artırma | SpecAugment benzeri: 2× zaman maskesi (≤%8), 2× özellik maskesi (≤%8) | aynı |
| Kayıp | CTC (blank=0, `zero_infinity`), CPU'da | aynı |
| Seçim | en iyi dev WER (greedy, 5 epoch'ta bir) | aynı |
| Süre | ~45 sn/epoch (M4 Pro) | ~49 sn/epoch |

**v1 hakkında not:** 40 epoch planlanmıştı; 22. epoch civarında MPS bellek şişmesi (değişken batch şekilleri,
süreç 26 GB'a çıktı) nedeniyle durduruldu. Kaydedilen model **20. epoch'tan** (dev WER %39,3). Bu sorun v2 için
uzunluk kovaları ve kova başına sabit batch boyutuyla çözüldü (bellek 3–7 GB'ta sabit). Yani v1'in kosinüs
takvimi tamamlanmadı.

Eğitim seyri (dev, greedy):

| Epoch | v1 WER | v1 CER |
|---|---|---|
| 5 | %59,2 | %13,2 |
| 10 | %44,0 | %9,1 |
| 15 | %40,7 | %8,4 |
| 20 | **%39,3** | **%8,0** |

v2: %39,4 (5) → %38,9 (10) → %36,3 (15) → %35,5 (20) → %34,2 (25) → **%33,6 (30)**.

### Dil modeli (`training/build_lm.py`, `training/decode.py`)

| | |
|---|---|
| Kaynak | `wikimedia/wikipedia` `20231101.tr`, ilk parquet parçası |
| Boyut | 1,7M cümle, **20M kelime**, 845 bin farklı kelime → sözlük 400 bin (+ `<unk>`) |
| Model | kelime 3-gram, interpolated Kneser-Ney (D=0,75), 1 kez görülen 3-gram'lar budandı (geri çekilme ağırlıkları yeniden normalize edildi, her bağlamda ΣP = 1 doğrulandı) |
| Dosya | `lm/tr_3gram.arpa` (381 MB, ARPA), `lm/unigrams.txt` |
| Üretim | saf Python (KenLM `lmplz` yerine); okuma KenLM Python modülü + `pyctcdecode` |
| Çözümleme | beam 64, **alpha 0,5, beta 0,0** (v1; dev'de 12'li ızgara) |

**Sızıntı kontrolü:** FLEURS dev/test cümleleriyle **5 kelimelik bir dizi bile paylaşan** Vikipedi cümleleri
dil modelinden çıkarıldı. (Kontrol: 474 dev+test cümlesinin hiçbiri Vikipedi'de birebir yok, 25'i en az bir
5-gram paylaşıyordu.) Filtreli ve filtresiz dil modeliyle sonuçlar aynı çıktı (test WER %16,1).

---

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `reader.safetensors` | **v3** okuyucu ağırlıkları + özellik ortalaması/standart sapması (`feature_mean`, `feature_std`) |
| `config.json` | v3: mimari, katmanlar, sözlük, LM ayarları, sonuçlar, temel model revizyonu |
| `reader.py` | okuyucu modeli, sözlük, normalizasyon, greedy CTC |
| `stt.py` | tek dosyalık çıkarım (`TurkishSTT`, komut satırı, `--variant`) |
| `corrector.py` | Zemberek kelime düzeltme |
| `spoken.py` | okunuş biçimine normalizasyon (`normalizer-tr`) + güvenilmez cümle filtresi |
| `lm_spoken/` | v3 dil modeli: okunuş biçimi Türkçe Vikipedi 3-gram |
| `lm/` | v1/v2 dil modeli: Türkçe Vikipedi 3-gram (rakamlar korunmuş) |
| `v1/` | v1 okuyucu (FLEURS temiz, orijinal hedefler) |
| `v2/` | v2 okuyucu (greedy'de daha iyi, LM ile daha kötü) |
| `results/` | çözümleme ızgaraları (dev/test), adım 0 sonuçları, v2 eğitim günlüğü |
| `training/` | tüm eğitim / değerlendirme kodu + Gradio arayüzü (`app.py`) |

### Yeniden üretme

```bash
cd training
uv sync                                                   # pyproject.toml
uv run probe.py                                           # adım 0 (FLEURS'u indirir)
uv run extract.py --splits train dev test                 # ~10 dk, ~4,5 GB
uv run train.py --layers h0 h8 h16 last --epochs 40 --name reader_fleurs_v1
uv run train.py --layers h0 h8 h16 last --init checkpoints/reader_fleurs_v1.pt \
               --epochs 30 --lr 5e-4 --batch-frames 4000 --name reader_fleurs_v2
# Vikipedi parquet'ini data/wiki/ altına indirin, sonra:
uv run --with "numpy>=2" --with pyarrow build_lm.py --max-words 20000000 --vocab 400000
uv run decode.py checkpoints/reader_fleurs_v1.pt --tune
uv run decode.py checkpoints/reader_fleurs_v1.pt --split test --alpha 0.5 --beta 0.0
uv run evaluate.py checkpoints/reader_fleurs_v1.pt        # test WER/CER + hız
# v3: telefon simülasyonu + okunuş biçimi
uv run spoken.py                                          # data/spoken/*.json
uv run extract.py --splits train dev test --tel           # *_tel özellikleri
uv run --with "numpy>=2" --with pyarrow build_lm.py --spoken --out lm_spoken
uv run train.py --layers h0 h8 h16 last --train-splits tr_tr_train tr_tr_train_tel \
               --dev-splits tr_tr_dev tr_tr_dev_tel --spoken --epochs 30 --batch-frames 4000 --name reader_v3_tel_spoken
uv run decode.py checkpoints/reader_v3_tel_spoken.pt --split test --suffix _tel --spoken \
               --lm-dir lm_spoken --alpha 0.7 --beta 2.0
uv run app.py                                             # http://127.0.0.1:7860
```

Ortam: Python 3.12, torch 2.14.1, transformers 5.19.0, sentence-transformers 6.1.0, macOS, Apple M4 Pro 24 GB.
`pyctcdecode` NumPy'ı 1.x'e sabitlediği için `build_lm.py` (pyarrow, NumPy 2 ister) ayrı katmanla çalıştırılır.

---

## Sınırlamalar

- **Az veri:** yalnızca 8,3 saat, okuma konuşması (FLEURS). Gündelik konuşma, gürültülü ortam, telefon sesi,
  aksanlar ve çok konuşmacılı kayıtlarda performans muhtemelen belirgin şekilde düşer; bunlar ölçülmedi.
- **Çıktı biçimi:** küçük harf, noktalamasız. v3'te sayılar yazıyla çıkar ("iki bin yedi"); rakama çevirmek için
  ayrı bir ITN adımı gerekir (bu repoda yok). v1'de sayılar tutarsızdı.
- **Telefon:** v3 yalnızca *simüle* telefon sesiyle eğitildi/ölçüldü; gerçek çağrı merkezi kayıtlarında ölçülmedi.
- **Kelime birleştirme:** sözlük dışı iki kelime bazen birleşir ("olaşır acaba" → "olaşıracaba"); bilinmeyen kelime
  cezasını düşürmek dev'de sonucu kötüleştirdi (%20,2 → %22,7), bu yüzden -10 korundu.
  Özel isimler ve yabancı kelimeler (ör. "del potro", "wifi") zayıf.
- **Dil modeli alanı:** Vikipedi ansiklopedik dildir; konuşma diline ve güncel olaylara uyumu sınırlı.
- **Uzun ses:** 30 sn'lik sabit parçalara bölünür; parça sınırına denk gelen kelimeler bozulabilir
  (örtüşmeli pencere yok).
- **Karşılaştırma:** Bu sonuçlar FLEURS dışı test setlerinde ya da diğer Türkçe STT modelleriyle aynı koşullarda
  karşılaştırılmadı.

## Sonraki adımlar

- Daha fazla veri (Common Voice Türkçe vb.) — en büyük kazanç beklentisi.
- Alt-kelime (BPE) birimleri, daha büyük okuyucu, örtüşmeli uzun ses çözümleme.
- Konuşma diline yakın metinle dil modeli; daha yüksek dereceli n-gram.

## Lisans

- Okuyucu ağırlıkları ve kod: **Apache 2.0**.
- [normalizer-tr](https://github.com/erdemtuna/normalizer-tr) (Apache 2.0) ve
  [zemberek-python](https://github.com/Loodos/zemberek-python) kullanılır, bu repoda kopyaları yok.
- Temel model [EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2): Apache 2.0 (ayrıca indirilir,
  bu repoda yok).
- Eğitim verisi [FLEURS](https://huggingface.co/datasets/google/fleurs): CC BY 4.0.
- `lm/` altındaki dil modeli Türkçe Vikipedi metninden türetilmiştir; Vikipedi içeriği **CC BY-SA 4.0** lisanslıdır,
  dil modeli dosyalarını bu koşullara uygun kullanın.

## Atıf / ilham

Fikir: EmbeddingGemma 2'yi donmuş bırakıp üstüne küçük bir okuyucu eğiterek İngilizce STT yapan
[bu paylaşım](https://x.com/TslShahir/status/2109660369429954631). Bu repo aynı yaklaşımın Türkçe uyarlamasıdır
(kelime yerine harf düzeyi CTC + dil modeli).
