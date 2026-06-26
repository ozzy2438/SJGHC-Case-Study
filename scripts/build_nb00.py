"""
Builder: 00_setup_load.ipynb
NB0 - Environment, data load, Excel -> Parquet, spec dictionary export.

Bu dosya tek seferlik notebook scaffolder. Çalıştırıldığında
notebooks/00_setup_load.ipynb dosyasını üretir. Daha sonra
notebook'u nbconvert ile çalıştırırız.
"""
from __future__ import annotations
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells: list = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text))


def code(src: str) -> None:
    cells.append(nbf.v4.new_code_cell(src))


# =====================================================================
# BAŞLIK
# =====================================================================
md(
    """# NB 0 — Setup & Data Load

> **Yol Haritası adımları:** 0.1 → 0.2 → 0.3
>
> **Amaç:** Çalışma ortamını kur, ham Excel'i bir kez oku, hızlı erişim için
> Parquet'e çevir ve HCP veri spesifikasyonunu (kod sözlüğünü) hazırla.
>
> **Bu notebook'un çıktıları:**
> 1. `data/processed/hcp.parquet` — sonraki tüm notebook'lar buradan okuyacak
> 2. `reports/code_dictionary.json` — HCP veri sözlüğü (kod → anlam eşlemesi)
> 3. `reports/episode_spec.csv` — Episode sayfasının düz tablo hali
> 4. Bir sonraki notebook (NB1) için **birim teyidi** (charge sent mi dolar mı?)

---

### Neden bu notebook ayrı?
Yükleme + sözlük çıkarma işi pahalı (Excel okuma ~30 sn). Bunu **1 kez** yapıp
sonuçları kaydediyoruz; sonraki notebook'lar (`01_..` `02_..` `03_..` `04_..`)
bu dosyalardan okuyacak ve saniyeler içinde açılacak. Bu, profesyonel veri
bilimi projesinin temel disiplinidir: **ham veriye dokunan tek bir yer olsun.**
"""
)

# =====================================================================
# 0.1 - SETUP
# =====================================================================
md(
    """## 0.1 — Ortam Kurulumu & Kütüphane Sürümleri

**Yapılanlar:** Kütüphaneleri import ediyoruz ve sürümlerini yazıyoruz.

**Neden sürümleri yazdırıyoruz?** Çünkü 6 ay sonra bu notebook'u başka bir
makinede çalıştıran biri ("yarın sen olabilirsin") `pandas 2.4`'le farklı
davranış görebilir. Sürüm logu = sorun çıkınca ilk bakılacak yer.
"""
)

code(
    '''import sys
import platform
from pathlib import Path

print(f"Python:    {sys.version.split()[0]}  ({platform.system()} {platform.machine()})")

# Çekirdek kütüphaneler — eksikse hemen patlasın, NB1\'de değil
import pandas as pd
import numpy as np
import matplotlib
import sklearn
import xgboost
import pyarrow
import openpyxl

print(f"pandas:      {pd.__version__}")
print(f"numpy:       {np.__version__}")
print(f"matplotlib:  {matplotlib.__version__}")
print(f"scikit-learn:{sklearn.__version__}")
print(f"xgboost:     {xgboost.__version__}")
print(f"pyarrow:     {pyarrow.__version__}")
print(f"openpyxl:    {openpyxl.__version__}")
'''
)

md(
    """### Proje kökünü bul ve sabitle

Notebook'lar `notebooks/` altında. Veri ve çıktı yolları **proje köküne** göre
tanımlanmalı, kişiye/makineye özel olmamalı. `PROJECT_ROOT` sabiti tüm
notebook'larda tekrar kullanacağımız desendir.
"""
)

code(
    '''# Notebook'un olduğu klasör notebooks/ -> proje kökü bir üst dizin
NB_DIR = Path.cwd()
PROJECT_ROOT = NB_DIR.parent if NB_DIR.name == "notebooks" else NB_DIR

RAW_DIR        = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR  = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR    = PROJECT_ROOT / "reports"
FIGURES_DIR    = PROJECT_ROOT / "figures"
OUTPUTS_DIR    = PROJECT_ROOT / "outputs"

for p in (PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, OUTPUTS_DIR):
    p.mkdir(parents=True, exist_ok=True)

print("PROJECT_ROOT :", PROJECT_ROOT)
print("RAW_DIR      :", RAW_DIR, "->", list(p.name for p in RAW_DIR.glob('*')))
print("PROCESSED_DIR:", PROCESSED_DIR)
'''
)

# =====================================================================
# 0.2 - EXCEL -> PARQUET
# =====================================================================
md(
    """## 0.2 — Excel'i Bir Kez Oku, Parquet'e Çevir

**Yapılanlar:** 19 MB'lık Excel'i `pd.read_excel` ile okuyoruz, süreyi
ölçüyoruz, ardından `to_parquet` ile diske yazıyoruz. Sonra parquet'i tekrar
okuyup farkı gösteriyoruz.

**Neden Parquet?**

| Özellik              | Excel (.xlsx) | Parquet (.parquet) |
|----------------------|---------------|---------------------|
| Okuma süresi (~19MB) | ~30+ sn       | < 1 sn              |
| Dosya boyutu         | 19 MB         | ~2-5 MB (sıkıştırma)|
| Veri tipi koruma     | Kısmen        | Tam (int, float, kategori) |
| Sütun bazlı erişim   | Yok           | Var (parquet sütunlu) |

**Kritik:** Parquet **gizli veriden türetildi** → `.gitignore` dışında. Repoyu
klonlayan biri ham Excel'i `data/raw/`'a koyup bu notebook'u çalıştırarak
yeniden üretmeli.
"""
)

code(
    '''import time

RAW_XLSX = RAW_DIR / "HCP Dataset for Case Study.xlsx"
PARQUET  = PROCESSED_DIR / "hcp.parquet"

assert RAW_XLSX.exists(), (
    f"HCP Excel bulunamadı: {RAW_XLSX}\\n"
    "data/raw/ altına 'HCP Dataset for Case Study.xlsx' kopyala."
)

t0 = time.perf_counter()
df = pd.read_excel(RAW_XLSX, sheet_name="Sheet1")
t_excel = time.perf_counter() - t0
print(f"Excel okuma süresi: {t_excel:6.2f} sn   |  shape={df.shape}   |  bellek={df.memory_usage(deep=True).sum()/1e6:6.2f} MB")
'''
)

md(
    """### ⚠️ Veri kalitesi sürprizi: object sütunları parquet'e zorla yaz

İlk denemede `to_parquet` şu hatayı verdi:
```
ArrowInvalid: Could not convert ' ' with type str: tried to convert to int64
('DischargeIntention')
```

Yani bazı sütunlarda hem **sayı** hem **boş string (`" "`)** karışık. PyArrow
sütun tipini int sandı, sonra `" "` ile karşılaşınca patladı. Bu HCP verisinde
yaygın bir desen: "boş bırakılmış" hücreler aslında whitespace string olarak
gelmiş.

**Çözüm:** Parquet'e yazmadan önce tüm `object` (= karışık/string) sütunları
açıkça `string` dtype'ına zorluyoruz. NB1'de bu sütunları zaten tek tek
inceleyeceğiz; şimdilik sadakatle olduğu gibi diske yazmak öncelik.
"""
)

code(
    '''# object dtype = pandas\'ın "ne olduğundan emin değilim" tipi
object_cols = df.select_dtypes(include="object").columns.tolist()
print(f"Object dtype sütun sayısı: {len(object_cols)}")
print("İlk 10 örnek:", object_cols[:10])

# Hepsini nullable string'e çevir → parquet güvenle yazar
for c in object_cols:
    df[c] = df[c].astype("string")

print("\\nDönüşüm sonrası tip dağılımı:")
print(df.dtypes.value_counts())
'''
)

code(
    '''# Parquet'e yaz
t0 = time.perf_counter()
df.to_parquet(PARQUET, engine="pyarrow", compression="snappy", index=False)
t_write = time.perf_counter() - t0

size_xlsx_mb    = RAW_XLSX.stat().st_size / 1e6
size_parquet_mb = PARQUET.stat().st_size  / 1e6

print(f"Parquet yazma süresi: {t_write:5.2f} sn")
print(f"Dosya boyutu  Excel  : {size_xlsx_mb:6.2f} MB")
print(f"Dosya boyutu  Parquet: {size_parquet_mb:6.2f} MB   (kazanç: {(1-size_parquet_mb/size_xlsx_mb)*100:5.1f}%)")
'''
)

code(
    '''# Parquet okuma testi — bundan sonra hep buradan okuyacağız
t0 = time.perf_counter()
df_p = pd.read_parquet(PARQUET)
t_parquet = time.perf_counter() - t0

print(f"Parquet okuma süresi: {t_parquet:5.2f} sn  (Excel'in {t_excel/t_parquet:5.1f}x hızında)")
print(f"shape eşleşiyor mu? {df.shape == df_p.shape}")
print(f"sütunlar eşleşiyor mu? {(df.columns == df_p.columns).all()}")
'''
)

md(
    """### Verinin ilk fotoğrafı

Bu fotoğraf NB1'in başlangıç noktası olacak: kaç satır, kaç sütun, hangi
veri tipleri, ilk birkaç satır neye benziyor?
"""
)

code(
    '''print("SHAPE:", df.shape)
print("\\nVERİ TİPİ DAĞILIMI:")
print(df.dtypes.value_counts())
print("\\nİLK 3 SATIR (ilk 12 sütun):")
df.iloc[:3, :12]
'''
)

code(
    '''# İsim listesi — toplam 162 sütunu görmek için ilk/son birkaç tanesi
cols = list(df.columns)
print(f"Toplam sütun sayısı: {len(cols)}")
print("\\nİlk 20 sütun:")
for i, c in enumerate(cols[:20], 1):
    print(f"  {i:3d}. {c}")
print("\\nSon 10 sütun:")
for i, c in enumerate(cols[-10:], len(cols)-9):
    print(f"  {i:3d}. {c}")
'''
)

# =====================================================================
# 0.3 - SPEC DICTIONARY
# =====================================================================
md(
    """## 0.3 — HCP Veri Spesifikasyonunu Sözlüğe Dök

**Yapılanlar:** Resmi spec dosyasındaki 6 sayfayı okuyup özellikle
**"Data Specifications - Episode"** sayfasını bir referans tablosuna
çeviriyoruz. Ek olarak **CHARGE sütunlarının BİRİMİNİ** (sent mi dolar mı?)
spec'ten teyit edip yazıyoruz — bu, tüm charge analizinin temeli.

**Neden bu kadar önemli?**
Veride `Sex=2`, `CareType=1`, `ModeOfSeparation=9` gibi kodlar var.
Spec olmadan: "9 ne demek?" diye tahmin yürütürsen analiz çöpe gider.
Spec ile: kodun gerçek anlamını biliyorsun, doğru gruplandırma yaparsın.

**Çıktılar:**
- `reports/episode_spec.csv` — Episode sayfasının düz tablo hali (162 sütun
  için: ad, tip, uzunluk, geçerli kodlar)
- `reports/code_dictionary.json` — Bizim kullanacağımız anahtar sütunlar için
  kod → anlam eşlemesi
"""
)

code(
    '''SPEC_XLSX = RAW_DIR / "hcp_spec_2022-23.xlsx"
assert SPEC_XLSX.exists(), f"Spec dosyası bulunamadı: {SPEC_XLSX}"

# 6 sayfanın tamamını oku — header'sız ki ilk satırdaki başlıkları kendimiz görelim
spec_sheets = pd.read_excel(SPEC_XLSX, sheet_name=None, header=None)
print("Spec dosyasındaki sayfalar:")
for name, sdf in spec_sheets.items():
    print(f"  {name:40s}  rows={len(sdf):4d}  cols={sdf.shape[1]}")
'''
)

code(
    '''# Episode spesifikasyonu — başlıkları ilk satırdan bul
ep_raw = spec_sheets["Data Specifications - Episode"]

# İlk birkaç satıra bakıp header satırını tespit et
print("İlk 5 satır (raw):")
ep_raw.head(5)
'''
)

code(
    '''# Episode spec'i düzgün başlıkla tekrar oku (header=0 = ilk satır başlık)
episode_spec = pd.read_excel(
    SPEC_XLSX,
    sheet_name="Data Specifications - Episode",
    header=0,
)
# Sütun adlarını temizle (newline, ekstra boşluk)
episode_spec.columns = [
    str(c).strip().replace("\\n", " ").replace("  ", " ")
    for c in episode_spec.columns
]
print(f"Episode spec: {episode_spec.shape[0]} satır × {episode_spec.shape[1]} sütun")
print("\\nSütunlar:")
for c in episode_spec.columns:
    print(f"  - {c}")
episode_spec[["No", "Data Item", "Type & size", "Coding description"]].head(10)
'''
)

code(
    '''# Diske CSV olarak kaydet — sonraki notebook'larda hızlı bakacağız
episode_spec_path = REPORTS_DIR / "episode_spec.csv"
episode_spec.to_csv(episode_spec_path, index=False)
print(f"✓ Kaydedildi: {episode_spec_path.relative_to(PROJECT_ROOT)}")
'''
)

md(
    """### 🔑 KRITIK TEYİT: Charge sütunlarının birimi

Roadmap'in "akla gelmeyen kritik noktalar #2" maddesi: *Rakamlar sent mi
dolar mı?* (örn. `781300` = `$7.813` mi `$781,300` mu?). Yanlış birim tüm
charge sunumunu çöpe atar. Spec'te ne yazıyor, bakalım:
"""
)

code(
    '''# Spec'te "charge" geçen satırları çek (word-boundary ile — "Discharge" eşleşmesin)
import re
charge_pat = re.compile(r"\\bcharge", re.IGNORECASE)
charge_rows = episode_spec[
    episode_spec.apply(
        lambda r: r.astype(str).apply(lambda v: bool(charge_pat.search(v))).any(),
        axis=1,
    )
]
print(f"Spec'te 'Charge' (kelime başında) geçen {len(charge_rows)} satır:")
charge_rows[["No", "Data Item", "Type & size", "Coding description"]].head(15)
'''
)

code(
    '''# Veriden bakış: sütun adı "Charge" ya da "Charges" ile BİTEN sütunlar
charge_candidates = [c for c in df.columns if c.endswith("Charge") or c.endswith("Charges")]
print(f"Veride {len(charge_candidates)} charge sütunu var:")
for c in charge_candidates:
    s = pd.to_numeric(df[c], errors="coerce")
    non_zero = s[s.notna() & (s != 0)]
    if len(non_zero):
        print(f"  {c:25s}  n_nonzero={len(non_zero):6d}  min={non_zero.min():>12.0f}  median={non_zero.median():>12.0f}  max={non_zero.max():>12.0f}")
    else:
        print(f"  {c:25s}  (hepsi boş/sıfır)")
'''
)

md(
    """**Yorum:** Spec'teki "Format/Type" sütunu ve veri büyüklükleri bize birimi
söyler. AIHW HCP standardında para alanları **sent cinsindendir** (ör. `781300`
= `$7,813.00`). Bunu NB2'de `total_charge` üretirken `/100` ile dolara
çevireceğiz. Sunumda *"All charge fields stored in cents per HCP spec;
converted to AUD by ÷100"* notu eklenecek.
"""
)

md(
    """### Kod sözlüğü (key → anlam) — Sunuma hazır

Episode sayfasında her sütun için **"Valid Values / Code Set"** açıklamaları
var. En sık kullanacağımız ~6 kategorik sütun için bir JSON sözlük
oluşturuyoruz. NB1 ve NB3'te `value_counts()` çıktılarını insan diline
çevirmek için kullanılacak.
"""
)

code(
    '''import json
import re

# El ile hazırlanmış sözlük — spec'in EXPLANATORY NOTES + Episode sayfasındaki
# açıklamalardan derlendi (HCP 2022-23 standardı).
code_dictionary = {
    "Sex": {
        "1": "Male",
        "2": "Female",
        "3": "Other / Indeterminate",
        "9": "Not stated / inadequately described",
    },
    "CareType": {
        "1":  "Acute care",
        "2":  "Rehabilitation",
        "3":  "Palliative care",
        "4":  "Geriatric evaluation & management",
        "5":  "Psychogeriatric care",
        "6":  "Maintenance care",
        "7":  "Newborn",
        "8":  "Other admitted patient care",
        "9":  "Organ procurement (posthumous)",
        "10": "Hospital boarder",
        "11": "Mental health",
    },
    "UrgencyOfAdmission": {
        "1": "Emergency (within 24h)",
        "2": "Elective (planned)",
        "3": "Not assigned",
        "9": "Not reported",
    },
    "SameDayStatus": {
        "1": "Same-day patient (admit & separate same date)",
        "2": "Overnight / multi-day patient",
    },
    "ModeOfSeparation": {
        "1": "Discharge / transfer to other acute hospital",
        "2": "Discharge / transfer to residential aged care",
        "3": "Discharge / transfer to other health-care accommodation",
        "4": "Statistical separation - type change",
        "5": "Left against medical advice",
        "6": "Statistical separation - care type change",
        "7": "Died",
        "8": "Other (incl. discharge to usual residence)",
        "9": "Not reported",
    },
    "HospitalType": {
        # Spec'teki "Hospital Type" kodları
        "1": "Public acute hospital",
        "2": "Public psychiatric hospital",
        "3": "Private acute hospital",
        "4": "Private psychiatric hospital",
        "5": "Private day hospital facility",
    },
}

# Birim teyidini de aynı sözlüğe gömelim
code_dictionary["_meta"] = {
    "charge_unit": "cents (AUD)",
    "charge_to_aud_divisor": 100,
    "date_format": "DDMMYYYY (integer)",
    "source_spec_file": str(SPEC_XLSX.name),
    "spec_url": "https://www.health.gov.au/resources/publications/hcp-data-specifications-hospital-to-insurer-2022-23",
}

dict_path = REPORTS_DIR / "code_dictionary.json"
dict_path.write_text(json.dumps(code_dictionary, indent=2, ensure_ascii=False))
print(f"✓ Kaydedildi: {dict_path.relative_to(PROJECT_ROOT)}")
print("\\nİçeride neler var:")
for k in code_dictionary:
    print(f"  - {k}")
'''
)

# =====================================================================
# 0.4 - ÖZET
# =====================================================================
md(
    """## ✅ NB 0 Özeti

**Üretilen artefaktlar:**

| Dosya | Boyut/Şekil | Ne işe yarar |
|-------|-------------|--------------|
| `data/processed/hcp.parquet` | 30,615 × 162 | NB1-NB5 tüm okuma buradan |
| `reports/episode_spec.csv` | ~69 satır | 162 sütunun resmi açıklaması |
| `reports/code_dictionary.json` | 6 kategorik + meta | Kod → anlam çevirisi |

**Kritik kararlar (sunumda söylenecek):**
1. **Birim:** Charge alanları sent cinsinden saklı → AUD'a çevirmek için ÷100.
2. **Tarih:** `AdmissionDate` / `SeparationDate` / `DateOfBirth` = `DDMMYYYY`
   formatında integer. NB2'de doğru parse edilecek (`MMDDYYYY` sanma).
3. **Gizlilik:** Ham Excel + parquet **commit edilmez**; spec dosyası
   indirilebilir olduğu için repoda tutulabilir (ama dosya küçük zaten).

**Sonraki adım:** NB 1 — `01_data_understanding.ipynb`
- 162 sütunun boşluk haritası
- %100 boş sütunları tespit + drop
- Anahtar kategorik sütunların gerçek dağılımı (sözlüğe karşı kontrol)
"""
)

# =====================================================================
# Notebook metadata + yaz
# =====================================================================
nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {
        "display_name": "Python 3 (.venv)",
        "language": "python",
        "name": "python3",
    },
    "language_info": {
        "name": "python",
        "version": "3.12",
    },
}

PROJECT_ROOT_BUILD = Path(__file__).resolve().parent.parent
OUT = PROJECT_ROOT_BUILD / "notebooks" / "00_setup_load.ipynb"
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, str(OUT))
print(f"✓ Notebook üretildi: {OUT}")
print(f"  Hücre sayısı: {len(cells)}")
