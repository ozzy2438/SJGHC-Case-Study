# SJGHC Case Study — Sunum Taslağı (15 Dakika)
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
- 30,615 epizod, gözlenen dönem 2022-04-14–2023-06-30
- %78 günübirlik, medyan yaş 67, %55 65 yaş üstü
- **Veri kalitesi notu:** whitespace-based missing values ve %100 boş sütunlar açıkça raporlandı

### Slayt 4 — Charge Dağılımı (1.5 dk)
- **Görsel:** figures/03_charge_distribution.png
- Sağa çarpık: medyan $650, ortalama $2,685
- **Karar:** Target log-transform edildi; yüksek charge epizodları hata metriğini domine etmesin diye

### Slayt 5 — MDC Charge Benchmarking (2 dk)
- **Görsel:** figures/03_mdc_cost.png
- MDC'ler arasında medyan charge farkları var; grafiklerde n sayısı ve medyan/IQR ile yorumlanmalı
- Kidney/urinary epizodları daha düşük medyan charge gösterdi; bu durum yüksek same-day oranından etkilenmiş olabilir
- **Not:** DRG-level case-mix analizi olmadan nedensel açıklama yapılmaz

### Slayt 6 — EDA Bulguları (2 dk)
- **Görsel:** figures/03_los_vs_cost.png + figures/03_comorbidity_cost.png
- LOS=0 medyan $480 vs LOS>0 $6,948
- Same-day status produced one of the clearest univariate charge differences in EDA
- Higher recorded comorbidity counts were associated with progressively higher median charges

### Slayt 7 — Model Performansı (2 dk)
- **Görsel:** figures/05_model_scorecard.png + figures/04_actual_vs_predicted.png
- XGBoost: MAE = $737, RMSE = $1,844, R² = 0.809
- Model comparison notu: Random Forest en iyi held-out performansı verdi; XGBoost çok yakın challenger olarak SHAP ve time-split analizinde kullanıldı
- R² ifadesi: model held-out test set charge variation'ın %80.9'ini açıkladı
- CV RMSE: 0.537 ± 0.012 on log-transformed target

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
C: "Accuracy %80" değil. Model held-out test set charge variation'ın yaklaşık %80.9'ini açıkladı. MAE yaklaşık $737.

**S: Veri sızıntısı (data leakage) riski?**
C: Charge/benefit component kolonları feature olarak kullanılmadı. LOS/procedure/comorbidity/final MDC gibi feature'lar epizod tamamlandıktan sonra bilindiği için model completed episode benchmarking kapsamındadır.

**S: Eksik veriyi nasıl ele aldın?**
C: Whitespace padding'i tespit ettim, %100 boş sütunları raporladım, data-quality summary ürettim ve target charge bileşenlerini ayrıca dokümante ettim.

**S: Etik/gizlilik?**
C: Raw Excel, processed parquet, row-level worst predictions ve model artifact public GitHub'a konmamalı. Aggregate reports/figures paylaşılabilir.
