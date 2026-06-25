# SJGHC Case Study — Sunum Taslağı (15 Dakika)
## Data Scientist (Funding & Costing) — Mülakat Sunumu

---

### Slayt 1 — Başlık (30 sn)
- **Başlık:** Hastane Epizod Maliyet Tahmini — HCP Veri Analizi
- İsim, pozisyon, tarih
- "30,615 hasta epizodunu analiz ettim ve maliyet tahmin modeli geliştirdim"

### Slayt 2 — Problem & Yaklaşım (1.5 dk)
- **Soru:** Bir hastanın maliyetini taburculuk öncesi tahmin edebilir miyiz?
- **Neden önemli:** Bütçe planlaması, kaynak tahsisi, fiyatlandırma
- **Yaklaşım:** 6 aşamalı pipeline (veri → temizlik → EDA → model → çıktı)

### Slayt 3 — Veri Genel Bakış (1.5 dk)
- **Görsel:** figures/01_categorical_distributions.png
- 30,615 epizod, 2023, özel akut hastane
- %78 günübirlik, medyan yaş 67, %55 65 yaş üstü
- **Veri kalitesi notu:** 27 sütun tamamen boştu (whitespace padding keşfi)

### Slayt 4 — Maliyet Dağılımı (1.5 dk)
- **Görsel:** figures/03_charge_distribution.png
- Sağa çarpık: medyan $650, ortalama $2,685
- **Karar:** Modeli log ölçekte eğittim → aykırı vakaların etkisini azalttım

### Slayt 5 — Kilit Bulgu: MDC Maliyet Farkı (2 dk)
- **Görsel:** figures/03_mdc_cost.png
- Kategoriler arası 25 kat fark
- Böbrek/Üriner (en sık) aslında en ucuz → diyaliz günübirlik
- **Funding içgörüsü:** Hacim ≠ maliyet

### Slayt 6 — Maliyet Sürücüleri (2 dk)
- **Görsel:** figures/03_los_vs_cost.png + figures/03_comorbidity_cost.png
- LOS=0 medyan $480 vs LOS>0 $6,948
- Komorbidite arttıkça maliyet doğrusal artıyor

### Slayt 7 — Model Performansı (2 dk)
- **Görsel:** figures/05_model_scorecard.png + figures/04_actual_vs_predicted.png
- XGBoost, R² = 0.805, MAE = $751
- 5-katlı CV ile doğrulandı (kararlı: ±0.011)

### Slayt 8 — Model Yorumlanabilirliği: SHAP (2 dk)
- **Görsel:** figures/04_shap_summary.png
- En güçlü sürücüler: Prosedür sayısı, MDC, LOS
- **Önemli:** Model genç diyaliz hastalarının ucuz olduğunu kendi öğrendi
- "Kara kutu değil — her tahmini açıklayabiliyoruz"

### Slayt 9 — İş Etkisi & Sonraki Adımlar (1.5 dk)
- Bütçe tahmini, anomali tespiti (beklenenden pahalı vakalar)
- Sonraki adım: gerçek maliyet (charge değil) verisiyle eğitim
- Daha fazla özellik: spesifik tanı kodları, doktor, koğuş

### Slayt 10 — Teşekkür & Sorular (30 sn)
- GitHub repo linki
- Sorular

---

## Olası Mülakat Soruları ve Cevaplar

**S: Neden XGBoost?**
C: Çarpık, karma (kategorik+sayısal) tıbbi veride en iyi performans. SHAP ile yorumlanabilir.

**S: R² 0.80 yeterli mi?**
C: Sağlık maliyet tahmininde iyi bir sonuç. Charge verisi gerçek maliyet değil; gerçek maliyet verisiyle daha da iyileşir.

**S: Veri sızıntısı (data leakage) riski?**
C: LOS taburculukta belli olur — modelim taburculuk-sonrası tahmin için. Gerçek-zamanlı tahmin için LOS çıkarılmalı.

**S: Eksik veriyi nasıl ele aldın?**
C: Whitespace padding'i tespit ettim (pd.NA değil), %100 boş 27 sütunu çıkardım, kalan boşlukları sayım özelliğine çevirdim.

**S: Etik/gizlilik?**
C: Veri de-identified. Confidential dosyalar .gitignore ile dışlandı, repoda asla yer almadı.
