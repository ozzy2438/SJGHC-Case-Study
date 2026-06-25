# SJGHC HCP Case Study — Data Scientist (Funding & Costing)

> **Adayın Adı:** Osman Orka  
> **Pozisyon:** Data Scientist (Funding & Costing) — St John of God Health Care  
> **Teslim Tarihi:** 30 Haziran 2026, 09:00 AWST  
> **Veri:** HCP (Hospital Casemix Protocol) De-identified Episode Data, 2022–23

---

## 🎯 Projenin Amacı

De-identified HCP epizod verisinden (~30.6K kayıt × 162 sütun) **ticari etki odaklı** bir analiz çıkarmak ve bir **makine öğrenmesi modeli** ile bunu desteklemek. Çıktı: 15 dakikalık yönetim sunumu.

Ana iş sorusu:
> *"Bir hasta epizodunun toplam maliyetini, hasta ve klinik özelliklerinden ne kadar doğru tahmin edebiliriz; bu tahminden hangi ticari kararı çıkarırız?"*

---

## 📁 Klasör Yapısı

```
SJGHC-Case-Study/
├── notebooks/                # 5 ayrı .ipynb (her faz tek dosya)
│   ├── 00_setup_load.ipynb
│   ├── 01_data_understanding.ipynb
│   ├── 02_cleaning_features.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_modeling.ipynb
│   └── 05_outputs_export.ipynb
├── data/
│   ├── raw/                  # ham Excel (gitignored)
│   └── processed/            # parquet (gitignored)
├── figures/                  # sunum için PNG çıktıları
├── outputs/                  # özet tablo CSV'leri
├── reports/                  # spec özetleri, kod sözlüğü
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Kurulum (Sıfırdan Kim Klonlasa Çalıştırabilir)

```bash
# 1) Repoyu klonla
git clone https://github.com/ozzy2438/SJGHC-Case-Study.git
cd SJGHC-Case-Study

# 2) Sanal ortam
python3 -m venv .venv
source .venv/bin/activate         # macOS / Linux
# .venv\Scripts\activate          # Windows

# 3) Bağımlılıklar
pip install -r requirements.txt

# 4) Veriyi yerleştir (DİKKAT: confidential — repoda yok)
#    HCP Dataset for Case Study.xlsx  →  data/raw/  altına kopyala

# 5) Jupyter / VS Code'da notebook'ları sırayla aç ve çalıştır
```

---

## 🗺️ Yol Haritası (Notebook'a göre)

| Notebook | Amaç | Çıktı |
|----------|------|-------|
| `00_setup_load` | Ortam, veri yükleme, parquet, spec sözlüğü | `hcp.parquet`, `code_dictionary.json` |
| `01_data_understanding` | Boşluk haritası, veri tipleri, kod dağılımları | `data_quality_report.md` |
| `02_cleaning_features` | Tarih parse, LOS, Age, komorbidite sayısı, total_charge, MDC | Temizlenmiş parquet |
| `03_eda` | Univariate / bivariate / Pareto / korelasyon | `figures/*.png` |
| `04_modeling` | Hipotez → baseline (Linear) → XGBoost → SHAP | `model_metrics.csv` |
| `05_outputs_export` | Sunum için PNG + özet tablo export | `figures/`, `outputs/` |

---

## 🔒 Veri Etiği

- HCP verisi de-identified olsa da hastane kayıtlarıdır → **repoya commit edilmez**.
- `.gitignore` veri dosyalarını ve türetilmiş parquet'leri dışarıda tutar.
- Sunum/grafiklerde **aggregate** rakamlar gösterilir, ham satır gösterilmez.

---

## 📚 Referanslar

- [HCP Data Specifications 2022–23 (Australian Government)](https://www.health.gov.au/resources/publications/hcp-data-specifications-hospital-to-insurer-2022-23)
- AR-DRG v10.0 sınıflandırması (MDC haritası için)
