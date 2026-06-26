#!/usr/bin/env python3
"""
Build 05_outputs_export.ipynb — Outputs and Presentation Readiness

Adımlar:
  5.0  Setup + tüm artefaktları yükle (clean veri, model, metrikler)
  5.1  Yönetici özeti tablosu (executive summary) → reports/executive_summary.csv
  5.2  MDC bazında charge özet tablosu → reports/mdc_cost_summary.csv
  5.3  Model performans kartı (tek görsel) → figures/05_model_scorecard.png
  5.4  Sunum slayt planı (15 dakika için) → reports/presentation_outline.md
  5.5  Tüm çıktıların envanteri
"""
import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).parent.parent
NB   = ROOT / "notebooks" / "05_outputs_export.ipynb"

nb    = nbf.v4.new_notebook()
cells = []

def md(text):  return nbf.v4.new_markdown_cell(text)
def code(src): return nbf.v4.new_code_cell(src)


# ──────────────────────────────────────────────────────────
# BAŞLIK
# ──────────────────────────────────────────────────────────
cells.append(md(
"""# Notebook 5 — Çıktılar ve Sunum Hazırlığı

## Bu notebook ne yapıyor?

Bu son notebook. Tüm analizimizi **sunulabilir çıktılara** dönüştürüyoruz.

Üreteceğimiz çıktılar:
1. **Yönetici özeti tablosu** — tek bakışta tüm kilit rakamlar
2. **MDC charge özet tablosu** — kategori bazında expected charge referansı
3. **Model performans kartı** — tek görselde tüm metrikler
4. **Sunum taslağı** — 15 dakikalık konuşma planı
5. **Validation pack** — leakage, baseline, segment, high-cost capture ve limitations çıktıları

**Amaç:** SJGHC mülakatında 15 dakikalık PowerPoint sunumu için hazır malzeme.
"""
))


# ──────────────────────────────────────────────────────────
# 5.0 SETUP
# ──────────────────────────────────────────────────────────
cells.append(md("---\n## 5.0 — Kurulum ve Artefakt Yükleme"))

cells.append(code(
"""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import json
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
FIGS = ROOT / "figures"
REPORTS = ROOT / "reports"

# Temiz veri
df = pd.read_parquet(ROOT / "data/processed/hcp_clean.parquet")

# Model metrikleri
with open(REPORTS / "model_metrics.json") as f:
    metrics = json.load(f)

print(f"Veri        : {df.shape[0]:,} epizod × {df.shape[1]} sütun")
print(f"Model R²    : {metrics['aud_r2']}")
print(f"Model MAE   : ${metrics['aud_mae']:,.2f}")
print("Artefaktlar yüklendi ✓")
"""
))


# ──────────────────────────────────────────────────────────
# 5.1 YÖNETİCİ ÖZETİ
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 5.1 — Yönetici Özeti Tablosu

**Yönetici özeti nedir?**  
SJGHC'deki bir yönetici 30 saniyede tüm projeyi anlamak ister.  
Bu tablo, "ne yaptık, ne bulduk" sorularını tek bakışta cevaplar.
"""
))

cells.append(code(
"""summary_rows = [
    ("Veri Seti", "Toplam Epizod", f"{len(df):,}"),
    ("Veri Seti", "Analiz Dönemi", "2023 (12 ay)"),
    ("Veri Seti", "Hastane Tipi", "Özel akut bakım (HospitalType=2)"),
    ("Hasta Profili", "Medyan Yaş", f"{df['Age'].median():.0f} yaş"),
    ("Hasta Profili", "65+ Yaş Oranı", f"%{(df['Age']>=65).mean()*100:.1f}"),
    ("Hasta Profili", "Günübirlik Oranı", f"%{(df['LOS']==0).mean()*100:.1f}"),
    ("Charge", "Medyan Fatura", f"${df['total_charge_aud'].median():,.0f}"),
    ("Charge", "Ortalama Fatura", f"${df['total_charge_aud'].mean():,.0f}"),
    ("Charge", "Maksimum Fatura", f"${df['total_charge_aud'].max():,.0f}"),
    ("En Sık MDC", "Kategori",
     f"L — Böbrek/Üriner (%{(df['MDC']=='L').mean()*100:.1f})"),
    ("Model", "Algoritma", "XGBoost Regressor"),
    ("Model", "Explained Variation (R²)", f"{metrics['aud_r2']:.3f}"),
    ("Model", "Ortalama Hata (MAE)", f"${metrics['aud_mae']:,.0f}"),
    ("Model", "Yüzde Hata (MAPE)", f"%{metrics['mape_pct']:.1f}"),
    ("Model Scope", "Kullanım Alanı", "Completed episode charge benchmarking"),
]

exec_summary = pd.DataFrame(summary_rows, columns=["Kategori", "Metrik", "Değer"])
exec_summary.to_csv(REPORTS / "executive_summary.csv", index=False)
print("✓ Kaydedildi: reports/executive_summary.csv\\n")
print(exec_summary.to_string(index=False))
"""
))


# ──────────────────────────────────────────────────────────
# 5.2 MDC ÖZET TABLOSU
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 5.2 — MDC Bazında Charge Özet Tablosu

Funding & Costing ekibinin en çok işine yarayacak tablo:  
**"Her hastalık kategorisi için tipik billed charge aralığı nedir?"**

Bu tablo contract benchmarking ve unusual charge review için referans olabilir.
"""
))

cells.append(code(
"""MDC_MAP = {
    "A":"Pre-MDC","B":"Sinir Sistemi","C":"Göz","D":"KBB & Ağız",
    "E":"Solunum","F":"Dolaşım","G":"Sindirim","H":"Karaciğer/Safra",
    "I":"Kas-İskelet","J":"Deri","K":"Endokrin","L":"Böbrek/Üriner",
    "M":"Erkek Üreme","N":"Kadın Üreme","O":"Gebelik/Doğum","P":"Yenidoğan",
    "Q":"Kan","R":"Ruhsal","S":"Madde Kullanımı","T":"Enfeksiyon",
    "U":"Yanık","V":"Sağlık Faktörleri","W":"Yaralanma","X":"Diğer",
    "Y":"HIV","Z":"Gruplandırılamayan",
}

mdc_summary = (df.groupby("MDC")
                 .agg(Epizod=("total_charge_aud", "count"),
                      Medyan=("total_charge_aud", "median"),
                      Ortalama=("total_charge_aud", "mean"),
                      Toplam=("total_charge_aud", "sum"),
                      Ort_LOS=("LOS", "mean"),
                      Ort_Yas=("Age", "mean"))
                 .reset_index())
mdc_summary["Kategori"] = mdc_summary["MDC"].map(MDC_MAP)
mdc_summary["Pay_%"] = (mdc_summary["Epizod"] / len(df) * 100).round(1)
mdc_summary = mdc_summary.sort_values("Toplam", ascending=False)

# Yuvarla
for col in ["Medyan", "Ortalama", "Toplam"]:
    mdc_summary[col] = mdc_summary[col].round(0)
mdc_summary["Ort_LOS"] = mdc_summary["Ort_LOS"].round(2)
mdc_summary["Ort_Yas"] = mdc_summary["Ort_Yas"].round(1)

# Sütun sırası
mdc_summary = mdc_summary[["MDC","Kategori","Epizod","Pay_%",
                            "Medyan","Ortalama","Toplam","Ort_LOS","Ort_Yas"]]
mdc_summary.to_csv(REPORTS / "mdc_cost_summary.csv", index=False)
print("✓ Kaydedildi: reports/mdc_cost_summary.csv\\n")

# En pahalı 10 kategoriyi göster
print("Toplam billed charge değerine göre en yüksek 10 MDC kategorisi:")
print("-" * 80)
top10 = mdc_summary.head(10).copy()
top10["Medyan"]   = top10["Medyan"].apply(lambda x: f"${x:,.0f}")
top10["Ortalama"] = top10["Ortalama"].apply(lambda x: f"${x:,.0f}")
top10["Toplam"]   = top10["Toplam"].apply(lambda x: f"${x:,.0f}")
print(top10.to_string(index=False))
"""
))


# ──────────────────────────────────────────────────────────
# 5.3 MODEL PERFORMANS KARTI
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 5.3 — Model Performans Kartı

Tek bir görselde modelin tüm performansını özetliyoruz.  
Bu, sunumda **"Modelimiz ne kadar iyi?"** slaytı olacak.
"""
))

cells.append(code(
"""fig = plt.figure(figsize=(13, 6.5))
fig.patch.set_facecolor("white")
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.3)

PRIMARY = "#1a5276"
ACCENT  = "#e74c3c"
GREEN   = "#27ae60"

# ─── Üst sıra: 3 büyük metrik kartı ───
metric_cards = [
    ("Explained Variation (R²)", f"{metrics['aud_r2']:.3f}",
     f"Test set charge variation explained: %{metrics['aud_r2']*100:.0f}", GREEN),
    ("Ortalama Hata", f"${metrics['aud_mae']:,.0f}",
     "Tahmin başına ortalama sapma", PRIMARY),
    ("Yüzde Hata", f"%{metrics['mape_pct']:.1f}",
     "Ortalama yüzde sapma (MAPE)", ACCENT),
]
for i, (title, value, sub, color) in enumerate(metric_cards):
    ax = fig.add_subplot(gs[0, i])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.05, 0.1), 0.9, 0.8,
                 facecolor=color, alpha=0.08,
                 edgecolor=color, linewidth=2, transform=ax.transAxes))
    ax.text(0.5, 0.72, title, ha="center", va="center",
            fontsize=12, color="#555", transform=ax.transAxes)
    ax.text(0.5, 0.46, value, ha="center", va="center",
            fontsize=30, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.22, sub, ha="center", va="center",
            fontsize=8.5, color="#777", transform=ax.transAxes, wrap=True)

# ─── Alt sol: CV skorları ───
ax_cv = fig.add_subplot(gs[1, 0])
cv_mean, cv_std = metrics["cv_rmse_mean"], metrics["cv_rmse_std"]
ax_cv.bar(["CV RMSE"], [cv_mean], yerr=[cv_std], color=PRIMARY,
          capsize=8, width=0.5, alpha=0.85)
ax_cv.set_title("5-Katlı Çapraz Doğrulama\\n(log ölçek)", fontsize=10, fontweight="bold")
ax_cv.set_ylabel("RMSE")
ax_cv.text(0, cv_mean/2, f"{cv_mean:.3f}\\n±{cv_std:.3f}",
           ha="center", va="center", color="white", fontweight="bold", fontsize=11)

# ─── Alt orta: Eğitim/Test bölme ───
ax_split = fig.add_subplot(gs[1, 1])
sizes = [metrics["n_train"], metrics["n_test"]]
labels = [f"Eğitim\\n{metrics['n_train']:,}", f"Test\\n{metrics['n_test']:,}"]
ax_split.pie(sizes, labels=labels, colors=[PRIMARY, ACCENT],
             autopct="%1.0f%%", startangle=90,
             textprops={"fontsize": 9, "color": "#333"},
             wedgeprops={"edgecolor": "white", "linewidth": 2})
ax_split.set_title("Veri Bölmesi", fontsize=10, fontweight="bold")

# ─── Alt sağ: Özellik bilgisi ───
ax_feat = fig.add_subplot(gs[1, 2])
ax_feat.axis("off")
feat_text = (
    f"Model: XGBoost Regressor\\n"
    f"Hedef: log(toplam billed charge)\\n"
    f"Özellik sayısı: {len(metrics['features'])}\\n"
    f"Ağaç sayısı: {metrics['best_iter']}\\n"
    f"Eğitim örneği: {metrics['n_train']:,}\\n"
    f"Test örneği: {metrics['n_test']:,}"
)
ax_feat.text(0.1, 0.5, feat_text, ha="left", va="center",
             fontsize=10, transform=ax_feat.transAxes,
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#f8f9fa",
                       edgecolor=PRIMARY, linewidth=1.5))
ax_feat.set_title("Model Yapılandırması", fontsize=10, fontweight="bold")

fig.suptitle("Completed Episode Charge Benchmarking — Performance Card",
             fontsize=16, fontweight="bold", y=0.99)
plt.savefig(FIGS / "05_model_scorecard.png", dpi=150,
            bbox_inches="tight", facecolor="white")
plt.show()
print("  ✓ Kaydedildi: 05_model_scorecard.png")
"""
))


# ──────────────────────────────────────────────────────────
# 5.4 SUNUM TASLAĞI
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 5.4 — 15 Dakikalık Sunum Taslağı

Mülakat sunumu için slayt-slayt konuşma planı.  
Her slayt için: başlık, kullanılacak görsel, konuşma noktaları.
"""
))

cells.append(code(
"""outline = f'''# SJGHC Case Study — Sunum Taslağı (15 Dakika)
## Data Scientist (Funding & Costing) — Mülakat Sunumu

---

### Slayt 1 — Başlık (30 sn)
- **Başlık:** Explainable Episode-Level Charge Benchmarking Using HCP Data
- İsim, pozisyon, tarih
- "30,615 tamamlanmış epizodu analiz ettim ve expected charge benchmarking modeli geliştirdim"

### Slayt 2 — Problem & Yaklaşım (1.5 dk)
- **Soru:** Tamamlanmış epizodlar için beklenen billed charge değerini ne kadar iyi tahmin edip olağandışı pahalı vakaları inceleyebiliriz?
- **Kapsam:** Admission-time early warning değil; completed episode benchmarking
- **Neden önemli:** Contract benchmarking, expected charge ranges, unusual charge review
- **Yaklaşım:** 6 aşamalı pipeline (veri → temizlik → EDA → model → çıktı)

### Slayt 3 — Veri Genel Bakış (1.5 dk)
- **Görsel:** figures/01_categorical_distributions.png
- 30,615 epizod, gözlenen dönem {df['AdmissionDate_dt'].min().date()}–{df['AdmissionDate_dt'].max().date()}
- %78 günübirlik, medyan yaş 67, %55 65 yaş üstü
- **Veri kalitesi notu:** whitespace-based missing values ve %100 boş sütunlar açıkça raporlandı

### Slayt 4 — Charge Dağılımı (1.5 dk)
- **Görsel:** figures/03_charge_distribution.png
- Sağa çarpık: medyan ${df['total_charge_aud'].median():,.0f}, ortalama ${df['total_charge_aud'].mean():,.0f}
- **Karar:** Target log-transform edildi; yüksek charge epizodları hata metriğini domine etmesin diye

### Slayt 5 — MDC Charge Benchmarking (2 dk)
- **Görsel:** figures/03_mdc_cost.png
- MDC'ler arasında medyan charge farkları var; grafiklerde n sayısı ve medyan/IQR ile yorumlanmalı
- Kidney/urinary epizodları daha düşük medyan charge gösterdi; bu durum yüksek same-day oranından etkilenmiş olabilir
- **Not:** DRG-level case-mix analizi olmadan nedensel açıklama yapılmaz

### Slayt 6 — EDA Bulguları (2 dk)
- **Görsel:** figures/03_los_vs_cost.png + figures/03_comorbidity_cost.png
- LOS=0 medyan ${df.loc[df['LOS']==0,'total_charge_aud'].median():,.0f} vs LOS>0 ${df.loc[df['LOS']>0,'total_charge_aud'].median():,.0f}
- Same-day status produced one of the clearest univariate charge differences in EDA
- Higher recorded comorbidity counts were associated with progressively higher median charges

### Slayt 7 — Model Performansı (2 dk)
- **Görsel:** figures/05_model_scorecard.png + figures/04_actual_vs_predicted.png
- XGBoost: MAE = ${metrics['aud_mae']:,.0f}, RMSE = ${metrics['aud_rmse']:,.0f}, R² = {metrics['aud_r2']:.3f}
- Model comparison notu: Random Forest en iyi held-out performansı verdi; XGBoost çok yakın challenger olarak SHAP ve time-split analizinde kullanıldı
- R² ifadesi: model held-out test set charge variation'ın %{metrics['aud_r2']*100:.1f}'ini açıkladı
- CV RMSE: {metrics['cv_rmse_mean']:.3f} ± {metrics['cv_rmse_std']:.3f} on log-transformed target

### Slayt 8 — Model Karşılaştırma & Leakage (2 dk)
- **Dosyalar:** reports/model_comparison.csv + reports/feature_list.csv + reports/leakage_audit.csv
- Mean/median baseline, Linear Regression, Random Forest ve XGBoost karşılaştırıldı
- Charge/benefit target component kolonları feature matrix dışında bırakıldı
- Feature availability ayrımı: At admission vs after episode completion

### Slayt 9 — Explainability & High-Cost Capture (1.5 dk)
- **Görseller:** figures/04_shap_summary.png + 3 waterfall examples
- SHAP sadece modelin feature'ları nasıl kullandığını gösterir; nedensellik iddiası değildir
- High-cost review: reports/high_cost_capture.csv üst %10 actual charge yakalama oranını verir

### Slayt 10 — Recommendations, Limitations & Questions (1.5 dk)
- High residual episodes Funding & Costing review queue için kullanılabilir
- MDC-specific expected charge ranges contract benchmarking destekleyebilir
- Same-day ve overnight epizodlar ayrı benchmark edilmelidir
- Limitations: single dataset, charge ≠ true cost, final episode features, random split caveat, no causality
- Public GitHub'a raw/processed data, row-level predictions veya model artifact koyma

---

## Olası Mülakat Soruları ve Cevaplar

**S: Neden XGBoost?**
C: Random Forest en iyi held-out performansı verdi. XGBoost ise çok yakın challenger olduğu ve SHAP/time-split analizlerini güçlü desteklediği için explainability benchmark olarak kullanıldı. Sonuçlar reports/model_comparison.csv içinde.

**S: R² 0.80 yeterli mi?**
C: "Accuracy %80" değil. Model held-out test set charge variation'ın yaklaşık %{metrics['aud_r2']*100:.1f}'ini açıkladı. MAE yaklaşık ${metrics['aud_mae']:,.0f}.

**S: Veri sızıntısı (data leakage) riski?**
C: Charge/benefit component kolonları feature olarak kullanılmadı. LOS/procedure/comorbidity/final MDC gibi feature'lar epizod tamamlandıktan sonra bilindiği için model completed episode benchmarking kapsamındadır.

**S: Eksik veriyi nasıl ele aldın?**
C: Whitespace padding'i tespit ettim, %100 boş sütunları raporladım, data-quality summary ürettim ve target charge bileşenlerini ayrıca dokümante ettim.

**S: Etik/gizlilik?**
C: Raw Excel, processed parquet, row-level worst predictions ve model artifact public GitHub'a konmamalı. Aggregate reports/figures paylaşılabilir.
'''

with open(REPORTS / "presentation_outline.md", "w") as f:
    f.write(outline)
print("✓ Kaydedildi: reports/presentation_outline.md")
print(f"  ({len(outline.splitlines())} satır sunum taslağı)")
"""
))


# ──────────────────────────────────────────────────────────
# 5.5 ENVANTER
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 5.5 — Tüm Çıktıların Envanteri

Projeyi tamamladık. İşte ürettiğimiz her şeyin listesi.
"""
))

cells.append(code(
"""print("=" * 65)
print("SJGHC CASE STUDY — PROJE ÇIKTI ENVANTERİ")
print("=" * 65)

print("\\n📓 NOTEBOOKS:")
for nb_file in sorted((ROOT / "notebooks").glob("*.ipynb")):
    print(f"   {nb_file.name}")

print("\\n📊 FIGURES (Sunum Grafikleri):")
for fig_file in sorted(FIGS.glob("*.png")):
    size_kb = fig_file.stat().st_size / 1024
    print(f"   {fig_file.name:<42} {size_kb:>6.1f} KB")

print("\\n📄 REPORTS (Tablolar & Çıktılar):")
for rep_file in sorted(REPORTS.glob("*")):
    if rep_file.is_file():
        size_kb = rep_file.stat().st_size / 1024
        print(f"   {rep_file.name:<42} {size_kb:>6.1f} KB")

print("\\n💾 DATA (gitignored — gizli):")
for data_file in sorted((ROOT / "data/processed").glob("*.parquet")):
    size_mb = data_file.stat().st_size / 1024**2
    print(f"   {data_file.name:<42} {size_mb:>6.2f} MB")

print("\\n" + "=" * 65)
print("✅ PROJE TAMAMLANDI")
print("=" * 65)
print(f'''
  6 notebook | {len(list(FIGS.glob("*.png")))} grafik | Model R² = {metrics['aud_r2']:.3f}

  Sıradaki adımlar (senin için):
  1. reports/presentation_outline.md ile slaytları hazırla
  2. figures/ klasöründeki PNG'leri slaytlara ekle
  3. Repo paylaşılacaksa önce private/clean olduğundan emin ol; gerekirse link verme
  4. 30 Haziran 09:00 AWST'den önce Stephen.Lamb@sjog.org.au'ya gönder
''')
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
