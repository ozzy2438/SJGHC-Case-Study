#!/usr/bin/env python3
"""
Build 02_cleaning_features.ipynb

Roadmap adımları:
  2.0  hcp.parquet yükle + null_summary'den 27 boş sütunu drop et (162→135)
  2.1  Tarih parse (DDMMYYYY int→datetime) + tarih hatası bayrağı
  2.2  LOS (yatış günü) + Age (yatış anındaki yaş) türet
  2.3  comorbidity_count + procedure_count
  2.4  total_charge_aud (kuruş→AUD ÷100)
  2.5  MDC — DRG'nin ilk harfinden Ana Tanı Kategorisi
  2.6  hcp_clean.parquet kaydet + özet
"""
import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).parent.parent
NB   = ROOT / "notebooks" / "02_cleaning_features.ipynb"

nb    = nbf.v4.new_notebook()
cells = []

def md(text):   return nbf.v4.new_markdown_cell(text)
def code(src):  return nbf.v4.new_code_cell(src)


# ──────────────────────────────────────────────────────────
# BAŞLIK
# ──────────────────────────────────────────────────────────
cells.append(md(
"""# Notebook 2 — Veri Temizleme ve Özellik Türetme

## Bu notebook ne yapıyor?

NB1'de veriyi *tanıdık*. Şimdi onu *kullanışlı* hale getireceğiz.

Ham verinin sorunları:
1. **27 sütun tamamen boş** → silinecek (162 → 135 sütun)
2. **Tarihler sayı formatında** (`1012023` gibi) → gerçek tarihe çevrilecek
3. **"Hasta kaç gün yattı?", "Toplam fatura ne kadar?"** → henüz yok → türetilecek

**Bu notebook'un çıktısı:** `data/processed/hcp_clean.parquet`  
NB3 (görsel analiz) ve NB4 (makine öğrenmesi modeli) bu dosyayı kullanacak.
"""
))


# ──────────────────────────────────────────────────────────
# 2.0  YÜKLEME + SÜTUN TEMİZLİĞİ
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.0 — Veri Yükleme ve Boş Sütun Temizliği

**Analoji:** Masanızda 162 klasör var. NB1 size "27 tanesi tamamen boş" dedi.  
İlk iş: o boş klasörleri çöpe atmak. Masa temizlenir, çalışmak kolaylaşır.

NB1'in ürettiği `null_summary.csv`'yi okuyup, `null_pct == 100` olan sütunları drop ediyoruz.  
Bu sayede hangi sütunları neden sildiğimiz kayıt altında — kararımız **belgelenmiş**.
"""
))

cells.append(code(
"""import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

# Ham veriyi yükle
df = pd.read_parquet(ROOT / "data/processed/hcp.parquet")
print(f"Ham veri: {df.shape[0]:,} satır × {df.shape[1]} sütun")
"""
))

cells.append(code(
"""# NB1'in ürettiği null_summary.csv'den %100 boş sütunları al
null_summary = pd.read_csv(ROOT / "reports/null_summary.csv")
drop_cols = null_summary.loc[null_summary["null_pct"] >= 99.9, "column"].tolist()

df = df.drop(columns=[c for c in drop_cols if c in df.columns])
print(f"Çıkarılan sütun sayısı : {len(drop_cols)}")
print(f"Kalan                  : {df.shape[0]:,} satır × {df.shape[1]} sütun")
print(f"\\nÇıkarılan sütunlar (tümü):")
for i, c in enumerate(drop_cols, 1):
    print(f"  {i:2d}. {c}")
"""
))


# ──────────────────────────────────────────────────────────
# 2.1  TARİH PARSE
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.1 — Tarihleri Parse Et (DDMMYYYY → datetime)

**Problem:** `AdmissionDate` sütununda `1012023` gibi sayılar var.  
Bu aslında **01/01/2023** (1 Ocak 2023) demek — ama Python bunu bilmiyor.

**HCP format kuralı (DDMMYYYY):**
```
1012023  →  DD=01  MM=01  YYYY=2023  →  2023-01-01
31122023 →  DD=31  MM=12  YYYY=2023  →  2023-12-31
```

Formülü elle yapalım:
```
gün  = n ÷ 1,000,000          (tam bölme)
ay   = (n ÷ 10,000) mod 100
yıl  = n mod 10,000
```

**Neden bu dönüşüm önemli?**  
Sayılarla `1012023 - 6012023` diyemezsiniz; bu anlamsız.  
Ama datetime ile `SeparationDate - AdmissionDate` = kaç gün yattı sorusu tek satırda cevaplanır.

**Hata bayrağı:** Çıkış tarihi giriş tarihinden önce gelen satırlar → `date_error = True`  
Bu satırları silmiyoruz; modelde gürültü yaratır ama şeffaflık için bayrağı koyuyoruz.
"""
))

cells.append(code(
"""def parse_hcp_date(series: pd.Series) -> pd.Series:
    \"\"\"
    DDMMYYYY formatındaki integer sütununu datetime'a çevirir.

    Örnek:
        1012023  → gün=1,  ay=01, yıl=2023 → 2023-01-01
        31122023 → gün=31, ay=12, yıl=2023 → 2023-12-31
        12061955 → gün=12, ay=06, yıl=1955 → 1955-06-12
    \"\"\"
    s = pd.to_numeric(series, errors="coerce")

    day  = (s // 1_000_000).astype("Int64")
    mon  = (s // 10_000 % 100).astype("Int64")
    yr   = (s % 10_000).astype("Int64")

    # "2023-01-01" formatına dönüştür, pandas bunu parse eder
    date_str = (
        yr.astype(str).str.zfill(4) + "-"
        + mon.astype(str).str.zfill(2) + "-"
        + day.astype(str).str.zfill(2)
    )
    return pd.to_datetime(date_str, format="%Y-%m-%d", errors="coerce")


df["AdmissionDate_dt"]  = parse_hcp_date(df["AdmissionDate"])
df["SeparationDate_dt"] = parse_hcp_date(df["SeparationDate"])
df["DateOfBirth_dt"]    = parse_hcp_date(df["DateOfBirth"])

# Tarih hatası bayrağı: çıkış tarihi < giriş tarihi
df["date_error"] = df["SeparationDate_dt"] < df["AdmissionDate_dt"]

print("Tarih parse sonuçları:")
for col in ["AdmissionDate_dt", "SeparationDate_dt", "DateOfBirth_dt"]:
    valid = df[col].notna().sum()
    print(f"  {col:<22}: {valid:,} geçerli / {len(df):,} toplam"
          f"  ({valid/len(df)*100:.1f}%)")
print(f"\\n  date_error (sep < adm): {df['date_error'].sum():,} satır"
      f"  ({df['date_error'].mean()*100:.2f}%)")

# Görsel kontrol: ilk 4 satır
print("\\nÖrnek dönüşümler:")
sample = df[["AdmissionDate","AdmissionDate_dt",
             "SeparationDate","SeparationDate_dt"]].head(4)
print(sample.to_string(index=False))
"""
))


# ──────────────────────────────────────────────────────────
# 2.2  LOS + AGE
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.2 — LOS ve Age Hesapla

### LOS (Length of Stay — Yatış Süresi)

```
LOS = SeparationDate − AdmissionDate  (gün cinsinden)
```

- **LOS = 0** → günübirlik hasta (same-day) — hata **değil**, normaldir!  
  Bu hastanenin %78'i günübirlik, yani LOS=0 en yaygın değer.
- **LOS > 30** → uzun yatış; palyatif bakım / komplikasyon olabilir.

### Age (Yatış Anındaki Yaş)

```
Age = AdmissionDate.yıl − DateOfBirth.yıl
```

Ama dikkat: doğum günü o yıl henüz geçmediyse yaş 1 eksiğidir.  
→ Ay ve günü de kontrol ederek **tam yaş** düzeltmesi yapıyoruz.

Örnek: Doğum 15 Haziran 1980, Yatış 10 Mart 2023  
→ Ham hesap: 2023 - 1980 = 43  
→ Haziran henüz gelmedi → gerçek yaş = **42**
"""
))

cells.append(code(
"""# LOS (gün)
df["LOS"] = (df["SeparationDate_dt"] - df["AdmissionDate_dt"]).dt.days

# Özet istatistikler
los_neg    = (df["LOS"] < 0).sum()
los_zero   = (df["LOS"] == 0).sum()
los_1_7    = ((df["LOS"] >= 1)  & (df["LOS"] <= 7)).sum()
los_8_30   = ((df["LOS"] >= 8)  & (df["LOS"] <= 30)).sum()
los_gt30   = (df["LOS"] > 30).sum()

print("LOS (Yatış Günü) Dağılımı:")
print(f"  Negatif  (<0, veri hatası)  : {los_neg:,}  ({los_neg/len(df)*100:.1f}%)")
print(f"  Günübirlik (=0)             : {los_zero:,}  ({los_zero/len(df)*100:.1f}%)")
print(f"  Kısa yatış (1–7 gün)        : {los_1_7:,}  ({los_1_7/len(df)*100:.1f}%)")
print(f"  Orta yatış (8–30 gün)       : {los_8_30:,}  ({los_8_30/len(df)*100:.1f}%)")
print(f"  Uzun yatış (>30 gün)        : {los_gt30:,}  ({los_gt30/len(df)*100:.1f}%)")
print(f"\\n  Ortalama LOS : {df['LOS'].mean():.2f} gün")
print(f"  Medyan LOS   : {df['LOS'].median():.0f} gün")
print(f"  Max LOS      : {df['LOS'].max():.0f} gün")
"""
))

cells.append(code(
"""# Age (yatış anındaki yaş)
adm_y, adm_m, adm_d = (df["AdmissionDate_dt"].dt.year,
                        df["AdmissionDate_dt"].dt.month,
                        df["AdmissionDate_dt"].dt.day)
dob_y, dob_m, dob_d = (df["DateOfBirth_dt"].dt.year,
                        df["DateOfBirth_dt"].dt.month,
                        df["DateOfBirth_dt"].dt.day)

df["Age"] = adm_y - dob_y  # ham yaş

# Doğum günü o yıl henüz geçmediyse 1 çıkar
birthday_passed = (adm_m > dob_m) | ((adm_m == dob_m) & (adm_d >= dob_d))
df["Age"] = df["Age"].where(birthday_passed, df["Age"] - 1)

# Özet
age_groups = {
    "Yenidoğan (0)"       : (df["Age"] == 0).sum(),
    "Çocuk (1–17)"        : ((df["Age"] >= 1) & (df["Age"] <= 17)).sum(),
    "Genç yetişkin (18–44)": ((df["Age"] >= 18) & (df["Age"] <= 44)).sum(),
    "Orta yaş (45–64)"    : ((df["Age"] >= 45) & (df["Age"] <= 64)).sum(),
    "Yaşlı (65+)"         : (df["Age"] >= 65).sum(),
    "Hata (<0 veya >120)" : ((df["Age"] < 0) | (df["Age"] > 120)).sum(),
}
print("Age (Yatış Anındaki Yaş) Dağılımı:")
for label, n in age_groups.items():
    print(f"  {label:<28}: {n:,}  ({n/len(df)*100:.1f}%)")

print(f"\\n  Ortalama yaş : {df['Age'].mean():.1f}")
print(f"  Medyan yaş   : {df['Age'].median():.0f}")
print(f"  Min / Max    : {df['Age'].min()} / {df['Age'].max()}")
"""
))


# ──────────────────────────────────────────────────────────
# 2.3  comorbidity_count + procedure_count
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.3 — Komorbidite ve Prosedür Sayısı

### Komorbidite nedir?

Hastanın ana hastalığına ek, **eşlik eden diğer hastalıkları** komorbidite denir.

Örnek: Kalp ameliyatı için yatan bir hasta aynı zamanda:
- Diyabetliyse → 1 komorbidite  
- Hem diyabetli hem hipertansifse → 2 komorbidite

HCP'de `AdditionalDiagnosis1` ... `AdditionalDiagnosis41` sütunları var.  
Her dolu sütun = 1 ek tanı.

**Neden önemli?**  
Komorbidite sayısı ↑ → Bakım karmaşıklığı ↑ → Maliyet ↑  
Bu, modelimizin en güçlü tahmin özelliklerinden biri olacak.

### Prosedür sayısı

`Procedure1` ... `Procedure32` sütunları.  
Her dolu sütun = hastaya uygulanan 1 cerrahi/tıbbi işlem.
"""
))

cells.append(code(
"""# Boşluk tespiti (NB1'deki aynı mantık)
NULL_LIKE = {"", "nan", "none", "na", "<na>", "nat", "null"}

def is_filled(series: pd.Series) -> "pd.Series[bool]":
    \"\"\"True = sütun gerçekten dolu, False = boş/whitespace/NaN\"\"\"
    s = series.astype(str).str.strip().str.lower()
    return ~s.isin(NULL_LIKE)


# Kalan tanı ve prosedür sütunlarını bul
diag_cols = sorted([c for c in df.columns if c.startswith("AdditionalDiagnosis")])
proc_cols  = sorted([c for c in df.columns if c.startswith("Procedure")])

print(f"Tanı sütunları    : {len(diag_cols)} adet  "
      f"({diag_cols[0]} → {diag_cols[-1]})")
print(f"Prosedür sütunları: {len(proc_cols)} adet  "
      f"({proc_cols[0]} → {proc_cols[-1]})")
"""
))

cells.append(code(
"""# Sayım: her satır için kaç tanesi dolu?
# np.stack → (n_rows, n_cols) boolean matris → .sum(axis=1) = satır toplamı
diag_matrix = np.stack(
    [is_filled(df[c]).to_numpy(dtype=bool, na_value=False) for c in diag_cols],
    axis=1
)
proc_matrix = np.stack(
    [is_filled(df[c]).to_numpy(dtype=bool, na_value=False) for c in proc_cols],
    axis=1
)

df["comorbidity_count"] = diag_matrix.sum(axis=1)
df["procedure_count"]   = proc_matrix.sum(axis=1)

print("Komorbidite Sayısı (değer → kaç hasta):")
print(df["comorbidity_count"].value_counts().sort_index().head(12).to_string())

print("\\nProsedür Sayısı (değer → kaç hasta):")
print(df["procedure_count"].value_counts().sort_index().head(12).to_string())

print(f"\\nKomorbidite — Ort: {df['comorbidity_count'].mean():.2f}"
      f"  Medyan: {df['comorbidity_count'].median():.0f}"
      f"  Max: {df['comorbidity_count'].max()}")
print(f"Prosedür      — Ort: {df['procedure_count'].mean():.2f}"
      f"  Medyan: {df['procedure_count'].median():.0f}"
      f"  Max: {df['procedure_count'].max()}")
"""
))


# ──────────────────────────────────────────────────────────
# 2.4  total_charge_aud
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.4 — Toplam Ücret ($AUD)

### HCP'de ücretler nasıl saklanıyor?

**Kuruş (cent) cinsinden tam sayı** olarak.

```
AccommodationCharge = 35710  →  $357.10 AUD
PharmacyCharge      =  4250  →   $42.50 AUD
```

Neden kuruş? Çünkü `35710` (integer) `357.10` (float)'dan daha az yer tutar ve  
kayan nokta hatası olmaz. Bu hastane veri tabanlarında yaygın bir yaklaşımdır.

**Dönüşüm:** `÷ 100`

**Hedef değişken:** `total_charge_aud` — tüm charge sütunlarının toplamının AUD cinsinden karşılığı.  
NB4'teki modelimiz bu değeri **tahmin etmeye** çalışacak.
"""
))

cells.append(code(
"""# 'Charge' içeren sütunları bul
charge_cols = [c for c in df.columns if "Charge" in c]
print(f"Ücret sütunları ({len(charge_cols)} adet):")
print("-" * 55)
for c in charge_cols:
    median_cents = df[c].median()
    print(f"  {c:<28}: medyan {median_cents:>8,.0f} kuruş"
          f" = ${median_cents/100:>8,.2f} AUD")
"""
))

cells.append(code(
"""# Toplam ücret: tüm charge sütunlarını topla, kuruş → AUD
df["total_charge_aud"] = df[charge_cols].sum(axis=1) / 100

tc = df["total_charge_aud"]
print("total_charge_aud İstatistikleri:")
print(f"  Ortalama : ${tc.mean():>10,.2f}")
print(f"  Medyan   : ${tc.median():>10,.2f}")
print(f"  Std      : ${tc.std():>10,.2f}")
print(f"  Min      : ${tc.min():>10,.2f}")
print(f"  %25      : ${tc.quantile(0.25):>10,.2f}")
print(f"  %75      : ${tc.quantile(0.75):>10,.2f}")
print(f"  %95      : ${tc.quantile(0.95):>10,.2f}")
print(f"  Max      : ${tc.max():>10,.2f}")
print(f"\\n  Sıfır ücretli epizod: {(tc == 0).sum():,}"
      f"  ({(tc==0).mean()*100:.1f}%)")
"""
))


# ──────────────────────────────────────────────────────────
# 2.5  MDC
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.5 — MDC (Ana Tanı Kategorisi)

### DRG nedir?

DRG = Diagnosis-Related Group (Tanıya İlişkin Grup).  
Her epizoda, hangi kaynakları tükettiğini özetleyen bir DRG kodu atanır.

```
D12B  →  MDC = D  =  Kulak, Burun, Boğaz
F06A  →  MDC = F  =  Dolaşım Sistemi
I03B  →  MDC = I  =  Kas-İskelet Sistemi
```

**Neden MDC'ye indirgiyoruz?**  
DRG'de 500+ farklı kod var; modelde çok fazla kategori analizi zorlaştırır.  
MDC ile bunları **26 ana gruba** düşürüyoruz.
"""
))

cells.append(code(
"""# AR-DRG v10 MDC eşleştirme tablosu (Australian Refined DRG)
MDC_MAP = {
    "A": "Pre-MDC (Nakil / Trakeostomi / ECMO)",
    "B": "Sinir Sistemi Hastalıkları",
    "C": "Göz Hastalıkları",
    "D": "Kulak, Burun, Boğaz ve Ağız",
    "E": "Solunum Sistemi Hastalıkları",
    "F": "Dolaşım Sistemi Hastalıkları",
    "G": "Sindirim Sistemi Hastalıkları",
    "H": "Karaciğer, Safra Kesesi ve Pankreas",
    "I": "Kas-İskelet Sistemi Hastalıkları",
    "J": "Deri ve Deri Altı Doku",
    "K": "Endokrin, Beslenme ve Metabolizma",
    "L": "Böbrek ve Üriner Sistem",
    "M": "Erkek Üreme Sistemi",
    "N": "Kadın Üreme Sistemi",
    "O": "Gebelik, Doğum ve Lohusalık",
    "P": "Yenidoğan",
    "Q": "Kan ve Kan Yapıcı Organ Hastalıkları",
    "R": "Ruhsal Hastalıklar",
    "S": "Madde Kullanımı ve Bağımlılık",
    "T": "Enfeksiyöz ve Parazitik Hastalıklar",
    "U": "Yanıklar",
    "V": "Sağlık Durumunu Etkileyen Faktörler",
    "W": "Yaralanma, Zehirlenme ve Toksik Etkiler",
    "X": "Diğer Faktörler",
    "Y": "HIV Enfeksiyonları",
    "Z": "Gruplandırılamayan",
}

df["DRG"]       = df["DRG"].astype(str).str.strip()
df["MDC"]       = df["DRG"].str[0].str.upper()
df["MDC_label"] = df["MDC"].map(MDC_MAP).fillna("Bilinmiyor")

mdc_dist = (df.groupby(["MDC", "MDC_label"])
              .size()
              .reset_index(name="count")
              .assign(pct=lambda d: d["count"] / len(df) * 100)
              .sort_values("count", ascending=False))

print(f"MDC Dağılımı (toplam {df['MDC'].nunique()} kategori, en sık 12):")
print("-" * 72)
print(f"{'MDC':<4}  {'Kategori':<40}  {'Sayı':>6}  {'%':>5}")
print("-" * 72)
for _, row in mdc_dist.head(12).iterrows():
    print(f"  {row['MDC']:<3}  {row['MDC_label']:<40}  "
          f"{row['count']:>6,}  {row['pct']:>5.1f}%")
"""
))


# ──────────────────────────────────────────────────────────
# 2.6  KAYDET
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 2.6 — Temiz Veriyi Kaydet

Tüm dönüşümleri tamamladık. Şimdi hcp_clean.parquet'i kaydediyoruz.

**Eklenen yeni sütunlar (11 adet):**

| Sütun | Tip | Açıklama |
|---|---|---|
| `AdmissionDate_dt` | datetime | Giriş tarihi |
| `SeparationDate_dt` | datetime | Çıkış tarihi |
| `DateOfBirth_dt` | datetime | Doğum tarihi |
| `date_error` | bool | `sep < adm` ise True |
| `LOS` | int | Yatış süresi (gün) |
| `Age` | int | Yatış anındaki yaş |
| `comorbidity_count` | int | Ek tanı sayısı (0–41) |
| `procedure_count` | int | Prosedür sayısı (0–32) |
| `total_charge_aud` | float | Toplam fatura ($AUD) |
| `MDC` | str | Ana tanı kategorisi harfi |
| `MDC_label` | str | MDC Türkçe açıklaması |
"""
))

cells.append(code(
"""out_path = ROOT / "data/processed/hcp_clean.parquet"
df.to_parquet(out_path, index=False)

import os
size_mb = os.path.getsize(out_path) / 1024**2
print(f"✓ Kaydedildi : {out_path}")
print(f"  Boyut      : {size_mb:.2f} MB")
print(f"  Şekil      : {df.shape[0]:,} satır × {df.shape[1]} sütun")

new_cols = [
    "AdmissionDate_dt","SeparationDate_dt","DateOfBirth_dt",
    "date_error","LOS","Age","comorbidity_count","procedure_count",
    "total_charge_aud","MDC","MDC_label"
]
print(f"  Yeni sütun : {len(new_cols)} adet → {new_cols}")
"""
))

cells.append(code(
"""# Nihai özet — model için önemli sütunların kontrol tablosu
print("=" * 60)
print("NB2 TAMAMLANDI — MODEL ÖNCESİ KONTROL")
print("=" * 60)

checks = [
    ("Hedef (y)",         f"total_charge_aud — Ort: ${df['total_charge_aud'].mean():,.0f}"),
    ("LOS",               f"Ort: {df['LOS'].mean():.1f} gün  Medyan: {df['LOS'].median():.0f}"),
    ("Age",               f"Ort: {df['Age'].mean():.1f}  Medyan: {df['Age'].median():.0f}"),
    ("Komorbidite",       f"Ort: {df['comorbidity_count'].mean():.2f}  Max: {df['comorbidity_count'].max()}"),
    ("Prosedür",          f"Ort: {df['procedure_count'].mean():.2f}  Max: {df['procedure_count'].max()}"),
    ("MDC kategorisi",    f"{df['MDC'].nunique()} farklı  En sık: {df['MDC'].value_counts().idxmax()}"),
    ("Tarih hatası",      f"{df['date_error'].sum():,} satır  ({df['date_error'].mean()*100:.2f}%)"),
    ("Toplam satır",      f"{len(df):,}"),
    ("Toplam sütun",      f"{df.shape[1]}"),
]
for k, v in checks:
    print(f"  {k:<22}: {v}")
print("=" * 60)
print("\\n→ Sıradaki: NB3 (Keşifsel Veri Analizi + Sunum Grafikleri)")
"""
))


# ──────────────────────────────────────────────────────────
# YAZ
# ──────────────────────────────────────────────────────────
nb.cells = cells
NB.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, NB)
print(f"✓ Notebook üretildi: {NB}")
print(f"  Hücre sayısı: {len(cells)}")
