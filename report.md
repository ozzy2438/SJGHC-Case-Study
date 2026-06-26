# SJGHC HCP Case Study — Detaylı Sunum Raporu

> **Yazar:** Osman Orka  
> **Pozisyon:** Data Scientist (Funding & Costing) — St John of God Health Care  
> **Veri:** De-identified HCP (Hospital Casemix Protocol) Episode Data, 2022–2023  
> **Tarih:** 26 Haziran 2026  
> **Kod ve reproducibility artefaktları:** Talep üzerine private olarak paylaşılabilir.

> **Doküman rolü:** This document is the technical and business source pack for a separate 10-slide, 15-minute presentation. It is not intended to be presented page by page.
> **PowerPoint kullanımı:** PowerPoint üretimi için bu rapor teknik kanıt kaynağıdır; ayrı bir 10-slide presentation production brief kullanılmalı, detay tablolar appendix'e taşınmalıdır.

---

## Bu Raporu Nasıl Okumalı?

Bu rapor **iki farklı paydaş kitlesine** aynı anda hitap etmek için yazıldı.

| Eğer sen... | Şu bölümlere odaklan |
|---|---|
| **Hastane yöneticisi / iş paydaşı** isen | "Neden Önemli?", "İş Çıktısı", "Öneriler" kutuları |
| **Veri ekibi lideri / teknik paydaş** isen | "Teknik Detay", "Yöntem Seçim Gerekçesi", "Doğrulama" kutuları |

Her bölümde **aynı bilgi iki dilde anlatılıyor**: önce iş dilinde "ne yaptık ve neden iş açısından önemli", sonra teknik dilde "nasıl yaptık ve neden bu yöntemi seçtik". Hızlı bir tur isteyenler "Yönetici Özeti" ile başlayıp ardından kendi bölümüne atlayabilir.

Yapı: **Task → Situation → Action → Result → Recommendations**.

PowerPoint üretiminde bütün slayt metrikleri için aşağıdaki **Master Metrics Table** kullanılmalı. Alt bölümlerdeki teknik tablolar detay kanıtı sağlar; slayt rakamları bu tabloyla çelişmemelidir.

## Master Metrics Table — Source of Truth

Kaynaklar: `reports/final_metrics.json`, `reports/model_comparison.csv`, `reports/segment_performance.csv`, `reports/high_cost_capture.csv`, `reports/feature_ablation.csv`, `reports/data_quality_summary.csv`, `reports/feature_list.csv`.

| Metrik | Değer |
|---|---:|
| Episodes | 30,615 |
| Observation period | 2022-04-14 – 2023-06-30 |
| Total billed charge | $82,215,340 |
| Median billed charge | $650 |
| Same-day share | 78.4% |
| Same-day median billed charge | $480 |
| Overnight/multi-day median billed charge | $6,948 |
| RF random split MAE / RMSE / R² | $719.67 / $1,829.01 / 0.8118 |
| XGB random split MAE / RMSE / R² | $736.62 / $1,843.96 / 0.8087 |
| RF time split MAE / RMSE / R² | $760.69 / $2,068.20 / 0.7764 |
| XGB time split MAE / RMSE / R² | $768.92 / $2,072.88 / 0.7754 |
| High-charge top-decile recall / precision | 76.9% / 74.6% |
| Final feature count | 11 |
| Data-quality headline numbers | invalid SameDayStatus: 235; theatre charge/minutes mismatch: 43; zero total charge: 430; duplicate episode ID: 0; missing target: 0 |

---

## Yönetici Özeti (One-Pager)

**Soru:** Tamamlanmış bir hasta epizodunun expected billed charge değerini ne kadar iyi tahmin edebilir, unusually high-charge epizodları nasıl belirleyebiliriz?

**Yaklaşım:** 30,615 de-identified HCP epizodu üzerinde 6 aşamalı, baştan sona reproducible bir analitik hat (data → temizlik → keşifsel analiz → modelleme → açıklanabilirlik → çıktı) kuruldu.

**Ana sonuç:**

| Ölçüm | Değer | Anlamı |
|---|---|---|
| Held-out test R² (Random Forest) | **0.8118** | Modelimiz epizod billed charge değerlerindeki değişkenliğin yaklaşık %81'ini açıklıyor |
| Ortalama mutlak hata (MAE) | **$719.67** | Tipik bir epizod için tahmin, gerçeğe ortalama yaklaşık $720 farkla yaklaşıyor |
| High-charge yakalama (top-decile recall) | **%76.9** | En yüksek billed charge değerine sahip üst %10 epizodu yakalama oranı |
| Zaman tabanlı test R² (Random Forest) | **0.7764** | Zaman bazlı split'te performans düşüyor ama benzer seviyede kalıyor |
| Kullanılan özellik sayısı | **11** | Hepsi klinik/operasyonel; formal audit charge bileşenleriyle direct overlap bulmadı |

**İş çıktısı (3 acil kullanım alanı):**

1. **Olağandışı fatura inceleme kuyruğu:** Model, beklenenden belirgin sapan epizodları işaretler. Funding & Costing ekibi haftalık inceleme listesi olarak kullanabilir.
2. **MDC bazında beklenen charge bandı:** Kontrat müzakeresi ve bütçe planlama için her MDC kategorisinde tipik fatura aralığı.
3. **Same-day vs overnight ayrı benchmark:** Aynı klinik etiket altında günübirlik ve yatılı vakalar tamamen farklı billed-charge profiline sahip; ortalamadan değil, doğru segmentten karşılaştırılmalı.

**Sınırlama:** Bu bir "admission-time erken uyarı" modeli değildir. LOS, prosedür sayısı, final DRG gibi bazı girdiler epizod tamamlandıktan sonra netleşir. Yani modelin kullanım alanı **completed episode benchmarking**, gerçek-zamanlı tahmin değil.

---

# BÖLÜM 1 — GÖREV VE DURUM (Task & Situation)

## 1.1 Görev (Task)

> St John of God Health Care, anonimleştirilmiş HCP epizod verisinden **ticari etki** üretebilecek ve karar destek için kullanılabilecek bir analitik çıktı geliştirmemizi istedi.

Görev, açık uçlu bir case study. Tek bir "şu rakamı bul" sorusu yok; aksine şu üçünü göstermem isteniyor:

1. **Veri okuryazarlığı:** Karmaşık, eksik ve kodlanmış sağlık verisini doğru anlama.
2. **Analitik düşünme:** Bu veriden gerçek bir iş sorusunu nasıl türeteceğimi seçme.
3. **Hikâye anlatma:** Bulguları teknik olmayan paydaşlara da anlatabilme.

### Benim seçtiğim iş sorusu

> *"Tamamlanmış bir epizodun beklenen billed charge değerini klinik ve operasyonel özelliklerden ne kadar doğru tahmin edebiliriz; bu tahminleri benchmarking ve unusual charge review için nasıl kullanırız?"*

Bu soruyu özellikle seçtim çünkü Funding & Costing fonksiyonunun günlük ihtiyaçlarına en yakın olan budur. "Hastalar daha sağlıklı olabilir mi?" gibi klinik sorular bu pozisyonun kapsamı dışında; "Bu vakanın faturası beklendiği gibi mi?" sorusu ise tam içinde.

> 📦 **Neden önemli? (yönetici görüşü):** Sağlık kuruluşları için expected billed charge öngörülebilirliği = nakit akışı planlama, kontrat inceleme ve sigorta ödemelerini doğru talep etme sürecine destek demektir. Vakaların charge profili anlaşılmadan planlama yapmak çok zordur.

> 🔬 **Teknik perspektif:** Bu, **tabular supervised regression** problemine indirgeniyor. Hedef: log-dönüşümlü `total_charge_aud`. Çoğu vaka düşük billed charge değerine, az sayıda vaka çok yüksek billed charge değerine sahip (right-skewed → log-transform gerekçesi).

## 1.2 Durum (Situation)

### Veri seti ne içeriyordu?

| Boyut | Değer |
|---|---|
| Epizod sayısı | 30,615 |
| Sütun sayısı (ham) | 162 |
| Hastane tipi | Tek hastane, özel akut bakım (HospitalType = 2) |
| Dönem | Nisan 2022 – Haziran 2023 (≈ 14 ay) |
| Hasta profili | Medyan yaş 67; %54.8 65+ yaş; %78.4 günübirlik |

### Önemli veri özellikleri

- **Charge alanları sentlik tam sayı:** Tüm parasal alanlar (AccommodationCharge, TheatreCharge, ProsthesisCharge, BundledCharges vb.) cent cinsinden tam sayı olarak saklanmış. AUD'a çevirmek için ÷ 100.
- **Tarih alanları DDMMYYYY tam sayı:** Örneğin `21042023` = 21 Nisan 2023. Pandas datetime'a manuel olarak parse edildi.
- **Eksik değerler whitespace olarak saklanıyor:** `pd.NA` değil, boşluk/tab karakterleri olarak. Naif `isna()` çağrısı bu eksikleri kaçırırdı.
- **MDC-style kategori DRG prefix'inden türetildi:** Broad diagnostic category, DRG kod prefix'i üzerinden çıkarıldı ve MDC-style clinical grouping etiketlerine map edildi. Bu, resmi DRG grouper çalıştırıldığı anlamına gelmez.

### En kritik durum tespiti: "Bu basit bir tablo değil, kodlanmış bir kayıt sistemi"

Veri 162 sütun ama bunların önemli bölümü dolu görünmüyordu. Detaylı analiz sonucu:

| Doluluk Aralığı | Sütun Sayısı |
|---|---|
| %100 boş (tek bir kayıt bile yok) | 27 |
| %50–99 boş | 84 |
| %5–49 boş | 3 |
| < %5 boş | 48 |

> 📦 **İş paydaşı için anlamı:** Veri "varmış gibi görünüyor" ama büyük kısmı bu hastane için anlamlı değil. Bu **bir veri kalitesi sorunu değil**, kayıt sisteminin hastaneye özel doldurulması meselesidir. Örneğin doğum/yenidoğan alanları bu hastane için neredeyse boş; çünkü bu özel akut bakım hastanesinde doğum aktivitesi yok.

> 🔬 **Teknik karar:** İki sayı farklı threshold'ları ifade eder: 27 sütun tam olarak %100 boştu; 64 sütun ise modelleme öncesi dışlama için kullanılan daha geniş `null_pct >= 99.9` missingness eşiğine takıldı. Bu, modelleme öncesi gürültüyü temizler ve özellik mühendisliği aşamasında kafa karışıklığını azaltır. Ancak silmek yerine **dokümante edip raporladım** (`reports/null_summary.csv`). Çünkü gerçek bir prodüksiyon ortamında bu sütunlar başka hastane için dolu olabilir.

---

# BÖLÜM 2 — AKSİYONLAR (Action)

Bu bölüm projedeki tüm teknik kararları **neden öyle yaptım** açıklamasıyla birlikte sıralar. Her alt başlığın sonunda iş ve teknik perspektifler ayrılır.

## 2.1 — Pipeline Mimarisi (Notebook 0–5)

Projeyi 6 numaralandırılmış notebook'a ayırdım. Bunun nedeni reproducibility ve fault isolation: bir aşama bozulduğunda yalnız o aşama yeniden çalıştırılabilir.

| # | Notebook | Amaç | Anahtar Çıktı |
|---|---|---|---|
| 0 | `00_setup_load` | Ortam, ham veri yükleme, parquet'e çevirme, kod sözlüğü | `hcp.parquet`, `code_dictionary.json` |
| 1 | `01_data_understanding` | Boşluk haritası, kategorik dağılımlar, tarih formatı doğrulama | `null_summary.csv` |
| 2 | `02_cleaning_features` | Tarih/yaş/LOS parse, MDC eşleme, komorbidite/prosedür sayımı, target oluşturma | `hcp_clean.parquet` (109 sütun), `target_composition.csv` |
| 3 | `03_eda` | 7 sunum-kalitesinde grafik, kilit segment farkları | `figures/03_*.png` |
| 4 | `04_modeling` | Baseline → Linear → RF → XGBoost karşılaştırma, SHAP, segment validation | `model_comparison.csv`, `xgb_model.json` (local), SHAP grafikleri |
| 5 | `05_outputs_export` | Yönetici özet tabloları, model skor kartı, sunum taslağı | `executive_summary.csv`, `mdc_cost_summary.csv`, `presentation_outline.md` |

Ek olarak: **tek komutluk validation paketi üreteci** — `scripts/generate_validation_outputs.py`. Bu script, sunumdan önce her şeyi sıfırdan yeniden üretiyor (leakage kontrolü, baseline karşılaştırma, time-split, segment performans, SHAP grafikleri). Bu, sunumdan önce "her şey gerçekten çalışıyor mu?" sorusuna evet diyebilmek için yapıldı.

> 📦 **Yöneticiye anlamı:** Bu yapı sayesinde proje "tek bir kişinin kafasındaki" değil, herhangi biri tarafından (uygun veriyle) çalıştırılabilir. Yani bu çalışmanın ekipte sürdürülebilirliği vardır.

> 🔬 **Teknik gerekçe:** Notebook'lar `nbformat` ile programatik üretilir (her notebook için bir `build_nb0X.py`), `jupyter nbconvert --execute` ile çalıştırılır. Bu pattern hem versiyonlamayı (Git'te düz Python diff'i) hem reproducibility'yi sağlar. Notebook'un kendisi versiyonlanmaz; "kaynak" `build_nb0X.py` ve `generate_validation_outputs.py` versiyonlanır.

## 2.2 — Veri Temizliği ve Özellik Mühendisliği (NB2)

### Yapılan dönüşümler

| Yeni Özellik | Nasıl Hesaplandı | Neden |
|---|---|---|
| `total_charge_aud` | Tüm `*Charge` ve `*Charges` alanlarının toplamı ÷ 100 | Modelin hedefi: epizod başı toplam billed charge AUD cinsinden |
| `LOS` | `SeparationDate - AdmissionDate` (gün) | Hastanede yatış süresi; realised utilisation ve expected charge için güçlü sinyal |
| `Age` | `AdmissionDate - DateOfBirth` (doğum günü düzeltmesi dahil) | Demografik sürücü |
| `comorbidity_count` | Temizleme sonrası elde kalan tüm `AdditionalDiagnosis*` alanlarının dolu sayısı | Kaydedilmiş klinik karmaşıklık göstergesi |
| `procedure_count` | Temizleme sonrası elde kalan tüm `Procedure*` alanlarının dolu sayısı | Kaydedilmiş klinik müdahale yoğunluğu |
| `MDC` | DRG prefix'inden türetilmiş broad diagnostic category | MDC-style klinik grup |
| `adm_month` | Admission tarihinin ayı | Gözlenen dönem içindeki aylık değişim için |

> 📦 **Yöneticiye anlamı:** Ham veri "şu hastaya şu işlem yapıldı" listesi gibi. Bizim oluşturduğumuz özellikler ise "bu epizod ne kadar karmaşık, ne kadar yoğundu, hangi klinik gruba aitti" sorularına özet cevap veren değişkenler. Bunlar olmadan model klinik bağlamı anlayamaz.

> 🔬 **Teknik karar — Neden bu özellikler ve neden bunlar yeterli:** Sağlık verisi denetiminde **özellik sayısını az tutmak** anlaşılabilirliği artırır. Onlarca düşük katkı sağlayan sütun yerine 11 yüksek değerli sütun seçtim. Feature ablation testi (Bölüm 3.4) bu seçimi rakamla destekliyor.

### Hedef değişkenin tanımı — kritik bir kayıt

`total_charge_aud` hedefi, **target_composition.csv** dosyasında tüm bileşenleriyle dokümante edildi. Bileşenler:

```
AccommodationCharge + TheatreCharge + LabourWardCharge + ICU_Charge +
ProsthesisCharge + PharmacyCharge + OtherCharges + BundledCharges +
HIH_Charges + SCN_Charges + CCU_Charges
```

Bu kritik çünkü: **modelde kullanılan hiçbir özellik bu listede yok**. Formal audit, model feature'ları ile hedefi oluşturan billed-charge component'leri arasında direct overlap bulmadı. Bu hesaplama [reports/leakage_audit.csv](reports/leakage_audit.csv) içinde otomatik olarak doğrulanır. Episode-completion feature'larının kullanılması target-component leakage değildir; ancak modelin kullanım zamanını completed episode benchmarking ile sınırlar.

> 📦 **Neden bunu özellikle vurguluyorum?** Model performans rakamları (R² = 0.81) "yapay yüksek" olabilir eğer model hedefi oluşturan bir alanı feature olarak görüyorsa. Bu kontrolü yapmasaydım, model gerçek dünyada çalışmaz, sunumda sorulduğunda da cevapsız kalırdım.

## 2.3 — Keşifsel Veri Analizi (NB3)

7 sunum kalitesinde grafik üretildi (her biri `figures/03_*.png`). Burada yalnızca kilit içgörüler:

### İçgörü 1: Charge dağılımı sağa çarpık

- Medyan: $650
- Ortalama: $2,685 (medyanın 4 katı)
- Maksimum: $69,138

> 📦 **İş anlamı:** Vakaların yarısı $650 altında, ancak az sayıda high-charge episode ortalamayı yukarı çekiyor. "Ortalama episode charge" rakamı pratikte yanıltıcı; medyan ve segment bazlı bakmak daha doğru.

> 🔬 **Modelleme kararı:** Hedef değişkene `log1p()` dönüşümü uygulandı. Bu, modelin high-charge tail içindeki uç değerlerden orantısız etkilenmesini azaltır; standart bir yöntemdir.

### İçgörü 2: LOS = 0 (günübirlik) vs LOS > 0 (yatılı) arasında 14 kat fark

- Günübirlik medyan: $480
- Yatılı medyan: $6,948

> 📦 **İş anlamı:** Aynı broad clinical category altında same-day ve overnight episode'lar çok farklı billed-charge profilleri gösterebilir. **Hacim bazında** Böbrek/Üriner en kalabalık MDC-style grup (%32.7) ama **aggregate billed-charge exposure** açısından en yüksek grup değil. DRG-level case-mix analizi olmadan bunun nedenini kesinleştirmiyoruz.

> 🔬 **Modelleme anlamı:** SameDayStatus ve LOS, model özelliklerinde tutulmalı; bunlar gerçek dünyada da güçlü ayrıştırıcılar. Ancak admission-time'da bilinmedikleri için model "completed episode" kapsamında.

### İçgörü 3: MDC kategorileri arasında 25 kat fark

| MDC | Açıklama | Medyan Charge | Pay |
|---|---|---|---|
| K | Endokrin/Beslenme | $8,774 | %1.2 |
| O | Gebelik/Doğum | $6,880 | %1.7 |
| I | Kas-İskelet | $6,684 | %9.6 |
| L | Böbrek/Üriner | $357 | **%32.7** (en kalabalık) |
| R | Ruhsal | $480 | %22.8 |

> 📦 **Kontrat incelemesinde anlamı:** Her MDC-style group ayrı bir case-mix bandı gibi ele alınmalı. Sigorta şirketiyle contract-review veya case-mix discussion yapılırken tek bir ortalama rakam değil, MDC/DRG-bazlı charge benchmark'ları konuşulmalı. Bu benchmark'lar benefit ve actual cost data ile birlikte yorumlandığında daha güçlü commercial review sağlar.

### İçgörü 4: Komorbidite sayısı billed charge ile ilişkili

Kayıtlı komorbidite sayısı arttıkça medyan billed charge sistematik olarak yükseliyor. Bu beklenen bir ilişki; modelimizin bu sinyali yakaladığını doğruluyor.

> 🔬 **Teknik uyarı:** Bu bir **korelasyon**, nedensellik değil. "Daha çok komorbidite kodlanması charge'ı artırıyor" denemez; "daha karmaşık vakalar hem daha çok komorbidite ile kodlanıyor hem daha yüksek billed charge değerine sahip olabiliyor" demek doğru. Sunumda bu nüans korunmalı.

## 2.4 — Modelleme Yaklaşımı (NB4)

### Neden çoklu model karşılaştırması?

Eğer sadece "XGBoost kullandık, R² = 0.81" deseydim, panel haklı olarak şunu sorardı: "Daha basit bir modelden ne kadar iyi?" Bu sorunun cevabı olmadan tek bir model rakamı havada kalır.

Bu yüzden **5 model karşılaştırıldı**, her ikisi de **iki ayrı split** stratejisiyle:

#### Tablo: Random split (80/20)

| Model | MAE | RMSE | R² | Yorum |
|---|---|---|---|---|
| Mean baseline | $2,814 | $4,217 | ≈ 0 | "Her vakaya ortalama tahmini" — kontrol noktası |
| Median baseline | $2,231 | $4,659 | -0.22 | Sağa çarpık dağılım nedeniyle ortalamadan daha kötü |
| Linear Regression | $1,977 | $16,162 | -13.69 | Back-transform sonrası zayıf; nonlinear charge patterns ve extreme predictions'a duyarlı |
| Random Forest | **$719.67** | **$1,829.01** | **0.8118** | En iyi held-out performans |
| XGBoost | $736.62 | $1,843.96 | 0.8087 | Çok yakın challenger, SHAP/açıklanabilirlik için kullanıldı |

#### Tablo: Time split (son %20 admission date)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Random Forest | $760.69 | $2,068.20 | 0.7764 |
| XGBoost | $768.92 | $2,072.88 | 0.7754 |

> 📦 **Yönetici özeti:** "Model çalıştı" demek için tek skor yetmez. 5 farklı yöntemi yan yana koyduk. Random Forest en güçlü held-out performansı verdi; XGBoost near-equivalent challenger olarak kaldı ve açıklanabilirlik/time-split analizinde kullanıldı. Ayrıca "geçmişle eğit, gelecekteki vakalarda dene" testinde performans biraz düşüyor ama dramatik değil.

> 🔬 **Yöntem seçim gerekçesi:**
> - **Mean/Median baseline:** Her ML projesinde olmazsa olmaz. Modelin gerçekten bir şey öğrenip öğrenmediğini gösterir.
> - **Linear Regression:** The linear baseline performed poorly after back-transformation, reflecting model misspecification for nonlinear charge patterns and sensitivity to extreme predictions.
> - **Random Forest:** Tabular regression'da güçlü, hiperparametre-hassas değil, paralel eğitim hızlı.
> - **XGBoost:** Tabular benchmark; Random Forest'a çok yakın performans verdi ve **SHAP TreeExplainer** ile model-consistent açıklama üretmek için challenger olarak tutuldu.

### XGBoost hiperparametreleri

```
n_estimators=350, max_depth=5, learning_rate=0.05,
subsample=0.80, colsample_bytree=0.80,
min_child_weight=10, gamma=0.05,
reg_alpha=0.10, reg_lambda=1.0
```

> 🔬 **Neden bu değerler?** `max_depth=5` ve `min_child_weight=10` overfitting riskini azaltır; `subsample/colsample=0.80` ek stokastiklik sağlar; `reg_alpha/reg_lambda` regularization log-target üzerinde daha kararlı convergence için. Bu kombinasyon bir grid search sonucu değil, sağlık tabular verilerinde standart başlangıç noktasıdır; CV sonuçları (log-RMSE = 0.5367 ± 0.0120) gözlenen veri içinde düşük fold-to-fold varyans gösterdi.

### Çapraz doğrulama (CV)

5-katlı KFold CV, log-target üzerinde:
- **CV log-RMSE = 0.5367 ± 0.0120**

> 📦 **Anlamı:** The low variation across five folds suggests stable performance under repeated resampling of the observed dataset. Bu, dış hastanelere genellemeyi veya gelecekteki drift'i kanıtlamaz.

## 2.5 — Açıklanabilirlik: SHAP

Bir tahmin modeli sadece "ne kadar doğru" değil, "neden öyle tahmin etti" sorusuna da cevap vermeli. Bu özellikle sağlıkta önemli; çünkü kara kutu çıktı, klinik personelin güvenini kazanamaz.

### SHAP nedir, neden seçildi?

SHAP (SHapley Additive exPlanations), oyun teorisinden gelen bir yöntem; bir tahminin her bir özellikten **ne kadar katkı** aldığını hesaplar. TreeSHAP provides efficient and model-consistent explanations for tree-based predictions.

### Üretilen SHAP çıktıları

1. **Global summary plot** ([figures/04_shap_summary.png](figures/04_shap_summary.png)): Her özelliğin tahmindeki ortalama mutlak etkisi.
2. **Bar feature importance** ([figures/04_feature_importance.png](figures/04_feature_importance.png)): Aynı bilginin sade görseli.
3. **3 adet waterfall örneği**:
   - `04_shap_waterfall_low_sameday.png` — low-charge same-day episode
   - `04_shap_waterfall_typical_mid.png` — tipik orta billed-charge episode
   - `04_shap_waterfall_high_complex.png` — high-charge karmaşık episode
4. **2 adet dependence plot**: LOS ve procedure_count için tahmin üzerindeki nonlineer etki eğrisi.

### Bulgular (önem sırasıyla)

Yöntem: **Mean absolute SHAP value on the held-out test sample**. Bu sıralama final XGBoost challenger modeline aittir; tree impurity importance ile karıştırılmamalıdır.

1. **LOS (yatış süresi)** — en güçlü predicted-charge sinyali
2. **Procedure count** — yapılan müdahale sayısı
3. **MDC** — klinik kategori
4. **Comorbidity count** — klinik karmaşıklık
5. **SameDayStatus** — günübirlik mi yatılı mı
6. Geri kalanlar (Age, Sex, CareType vb.) belirgin biçimde daha düşük etki

> 📦 **İş paydaşına anlatım:** "XGBoost challenger modeli bir vakanın faturasını tahmin ederken en çok yatış süresine, sonra yapılan işlem sayısına bakıyor. Yaş ve cinsiyet gibi demografik bilgiler bu modelde daha düşük ağırlığa sahip — yani predicted charge daha çok realised utilisation ve recorded clinical activity ile ilişkili." Bu, kontrat incelemelerinde case-mix tartışmasını destekleyebilir; tek başına profitability veya actual cost kanıtı değildir.

> 🔬 **Önemli teknik nüans:** SHAP **modelin nasıl davrandığını** gösterir, dünyanın nedensel yapısını değil. Yani "yatış süresini azaltırsak charge düşer" cümlesi SHAP'tan çıkmaz; SHAP yalnızca "model predicted charge için yatış süresine büyük ağırlık veriyor" der. Bu ayrım sunumda korunmalı.

## 2.6 — Doğrulama Paketi: "Bu Sonuçları Gerçekten Savunabilir misin?"

Bu, projenin en az model kadar önemli olan kısmı. Tek komut çalıştırıldığında üretilen 10 kontrol/raporu kapsar:

```bash
python scripts/generate_validation_outputs.py
```

| Çıktı | Ne Yapar | Neden Önemli |
|---|---|---|
| `leakage_audit.csv` | Charge bileşeni feature olarak kullanılmış mı? | Direct target-component overlap olmadığını doğrular |
| `feature_list.csv` | 11 feature'ı tek tek dokümante eder | "Hangi alanlar kullanılıyor?" sorusuna kanıtlı cevap |
| `model_comparison.csv` | 5 model × 2 split | "Neden XGBoost?" sorusuna cevap |
| `segment_performance.csv` | Same-day/overnight/charge band/MDC bazlı performans | "Model bazı segmentlerde zayıf mı?" |
| `high_cost_capture.csv` | Top-decile recall/precision | "High-charge episodes için önceliklendirme sinyali var mı?" |
| `feature_ablation.csv` | Demografi only / klinik only / op only / full | "Hangi bilgi grubu en değerli?" |
| `data_quality_summary.csv` | 9 veri kalitesi kontrolü | "Veriyi incelediniz mi?" |
| `worst_predictions.csv` | En kötü 50 tahmin (local-only) | İnceleme için, public repo'da değil |
| `target_composition.csv` | Hedefin nasıl hesaplandığı | Hedef tanımı şeffaf |
| `limitations.md` | Açıkça yazılı sınırlamalar | Profesyonel dürüstlük |

> 📦 **Yönetici için:** Bu paket sayesinde herhangi bir paydaş "ama şunu kontrol ettiniz mi?" sorduğunda elimde önceden hazırlanmış bir CSV var. Soruları havada cevaplamak yerine kanıta dayalı yanıt veriyorum.

> 🔬 **Teknik için:** Bu, projenin "scientific rigor" katmanı. Bir veri ekibinin bu çalışmayı production'a almadan önce yapacağı tüm sanity check'leri zaten yapılmış halde sunuyorum.

---

# BÖLÜM 3 — SONUÇLAR (Result)

## 3.1 — Genel Performans

| Metrik | Random Forest (random split) | XGBoost (random split) | Random Forest (time split) | XGBoost (time split) |
|---|---:|---:|---:|---:|
| MAE | $719.67 | $736.62 | $760.69 | $768.92 |
| RMSE | $1,829.01 | $1,843.96 | $2,068.20 | $2,072.88 |
| R² | **0.8118** | 0.8087 | **0.7764** | 0.7754 |

> 📦 **Yöneticiye çevirisi:**
> - Random Forest tipik bir vaka için ortalama **$719.67 hata** ile tahmin yapıyor.
> - "Episode billed charge variation'ın **yaklaşık %81'ini** açıklıyor."
> - Time-split testinde de **%77.6** civarı explained variation devam ediyor.

## 3.2 — Hangi Segmentlerde İyi, Hangilerinde Zayıf?

[reports/segment_performance.csv](reports/segment_performance.csv) içinden seçili satırlar:

Not: Bu segment metrikleri yalnızca held-out test seti üzerinde hesaplandı (`n_test = 6,123`). Bu nedenle `Same-day n=4,836` ve `Overnight n=1,242` değerleri tüm veri setindeki 30,615 epizodu değil, test setindeki segmentleri ifade eder.

| Segment | n | Medyan Gerçek Charge | MAE | R² |
|---|---|---|---|---|
| Same-day | 4,836 | $480 | $324.92 | 0.591 |
| Overnight/multi-day | 1,242 | $7,057 | $2,264.53 | 0.660 |
| Low-charge (≤ train medyanı $650) | 3,266 | $357 | $54.75 | -3.93 |
| Mid-charge ($650 – $7,892) | 2,263 | $2,553 | $978.05 | 0.27 |
| High-charge (> $7,892) | 594 | $12,816 | $3,566.01 | -0.19 |

> 📦 **Önemli yorum:**
> - **Low-charge band içinde** $54.75 ortalama hata küçük görünüyor ama R² negatif. Bunun nedeni: düşük charge bandının kendi içinde çok az değişkenlik göstermesi; bu segmentte R² metriği yanıltıcı olabilir.
> - **High-charge band içinde** exact dollar calibration zayıf (R² negatif). Ancak model high-charge prioritisation için sinyal taşıyor (bkz. 3.3 — top-decile recall %76.9).
> - **Yönetici dilinde:** "Model tipik vakalarda güçlü; en uç vakalarda kesin dolar kalibrasyonu zayıf, ancak high-charge review queue önceliklendirmesini destekleyebilir."

## 3.3 — High-Charge Episode Yakalama

[reports/high_cost_capture.csv](reports/high_cost_capture.csv):

| Metrik | Değer |
|---|---|
| Top decile recall | **%76.9** |
| Top decile precision | **%74.6** |
| Gerçek high-charge episode sayısı | 594 |
| Model'in işaretlediği high-charge episode sayısı | 613 |
| Doğru işaretleme (TP) | 457 |

> 📦 **İş çıktısı:** The regression model was less reliable for exact dollar calibration within the high-charge tail, but it retained useful prioritisation value by identifying 76.9% of true top-decile episodes. Bu, manuel review queue için potansiyel olarak yararlı bir önceliklendirme sinyalidir; nihai iş kabul eşiği ayrıca belirlenmelidir.

## 3.4 — Hangi Bilgi Grubu Modele Ne Kadar Katkı Sağlıyor?

[reports/feature_ablation.csv](reports/feature_ablation.csv):

| Özellik Seti | n_feat | MAE | R² |
|---|---:|---:|---:|
| Full model | 11 | $737.57 | 0.8085 |
| Clinical only (komorbidite, prosedür, MDC, CareType, urgency) | 5 | $995.05 | 0.6933 |
| No LOS / no procedure count | 9 | $1,007.40 | 0.6753 |
| Operational only (LOS, sameday, separation, month) | 4 | $1,650.58 | 0.3700 |
| Demographics only (Age, Sex) | 2 | $2,212.00 | -0.1044 |

> 📦 **Net bulgu:** Demographics alone provided little predictive value in this dataset. The clinical-only feature set retained an R² of 0.6933 compared with 0.8085 for the full model, showing that clinical features preserved a substantial share of predictive signal. Removing LOS and procedure count provides an initial sensitivity test; it should not be presented as admission-time model performance because other fields in that feature set may still be post-episode or post-coding.

> 🔬 **Not:** Feature-ablation results were generated in a separate controlled validation run; minor metric differences from the main model-comparison table reflect the validation configuration.

## 3.5 — Veri Kalitesi Bulguları

[reports/data_quality_summary.csv](reports/data_quality_summary.csv):

| Kontrol | Etkilenen Kayıt | Yüzde |
|---|---|---|
| Negative LOS | 0 | %0.0 |
| Same-day code / date mismatch | 0 | %0.0 |
| Invalid SameDayStatus code | 235 | %0.77 |
| ICU charge ama ICU days/hours yok | 0 | %0.0 |
| Theatre charge ama theatre minutes yok | 43 | %0.14 |
| Total charge = 0 | 430 | %1.41 |
| Whitespace-based missing values (en az 1 alan) | 30,615 | %100 |
| Duplicate episode identifier | 0 | %0.0 |
| Missing target values | 0 | %0.0 |

> 📦 **İş yorumu:**
> - The selected structural validation checks identified relatively low rates of key inconsistencies.
> - **Whitespace missing %100 satırı kapsıyor** — yanıltıcı görünüyor. Açıklama: her epizotta en az bir string alanın boş olduğunu söylüyor; bu kritik alanlarda bilgi eksikliği anlamına gelmez. Anlamlı eksiklik kontrolleri zaten üstteki diğer satırlarda yapılıyor.
> - **Zero total charge (430)** — zero-charge episodes may reflect legitimate administrative or non-billable scenarios, but their status requires business validation.

### Data-quality issue treatment

| Issue | Detection | Treatment in current pipeline | Modelling impact |
|---|---:|---|---|
| Invalid SameDayStatus code | 235 | Retained as observed category value; surfaced in `data_quality_summary.csv` | XGBoost/RF can split on the value, but business validation is needed before operational use |
| TheatreCharge but TheatreMinutes = 0 | 43 | Flagged and retained | May indicate coding/timing inconsistency; low rate, not excluded in current model |
| Zero total charge | 430 | Retained in target distribution; MAPE computed only on positive-charge rows | Affects low-charge tail and should be business-validated before production rules |
| Whitespace blanks | 1,356,242 cells across all rows | Standardised through strip/null-like handling for counts and missingness summaries | Mainly affects sparse diagnosis/procedure/string fields; not treated as critical-field missingness by itself |
| Duplicate episode identifier | 0 | No action required | No duplicate-ID modelling adjustment needed |
| Missing target values | 0 | No action required | All rows had a target value |

> 🔬 **Bu bulguların önemi:** Sağlık verisi mükemmel değildir; bunu kabul etmek profesyonel duruştur. Soru "veri kötü mü?" değil, "hangi structural checks hangi sorunları yakaladı ve bunlar nasıl ele alındı?" olmalı. Bu rapor, seçili kontrollerdeki bulguları ve mevcut treatment kararlarını açıkça ayırır.

---

# BÖLÜM 4 — SINIRLAMALAR (Limitations)

Profesyonel bir sunumda **limitations slide** zayıflık değil, güçtür. Panelin tek bir gizli kontrolü vardır: "Aday kendi çalışmasının zayıf yönlerini biliyor mu?"

### 1. Bu bir admission-time modeli değildir

LOS, procedure_count, comorbidity_count, SameDayStatus, ModeOfSeparation ve final MDC — bunların hepsi epizod tamamlandıktan sonra netleşir. Yani model gerçek-zamanlı tahmin için kullanılamaz, **completed episode benchmarking** için kullanılır.

### 2. Charge ≠ Cost

Hedef değişken **billed charge**, gerçek ekonomik maliyet değil. Hastanenin sigortaya fatura ettiği rakam, gerçek operasyonel maliyetten farklı olabilir. Bu, hastane finansal verisi paylaşıldığında düzeltilebilir.

### 3. Tek hastane, kısa dönem

Sadece bir hastane (HospitalType=2) ve ~14 ay veri. Genelleme yapma yetkimiz bu kapsamla sınırlı. Başka SJGHC hastanelerine taşımadan önce o hastanelerin verisiyle yeniden eğitilmeli/doğrulanmalı.

### 4. Random split, gerçek geleceği taklit etmiyor

Random split test seti, eğitim setiyle aynı dönemden çekilmiş vakalar içerir. Gerçek dünyada model "geçmişle eğitilip gelecek vakaları" tahmin edecek. Bu yüzden ek olarak **time-based split** sonuçlarını da raporladık (Random Forest R² 0.8118 → 0.7764). Fark küçük ama var; gerçek dünyada performans bu sensitivity testine göre daha temkinli beklenmeli.

### 5. High-charge segmentte tam dolar kalibrasyonu zayıf

Top-decile vakaların **var olduğunu** yakalayabiliyoruz (recall %76.9, precision %74.6) ama exact dolar miktarını verme konusunda RMSE yüksek. Pratik anlamı: model "bu high-charge review için önceliklendirilebilir" diyebilir, ama "bu vaka tam olarak $25,000 olacak" diyemez.

### 6. SHAP nedensellik göstermez

Model davranışını gösterir. "LOS'u azaltırsak billed charge düşer" gibi nedensel önermeler bu çalışmadan çıkarılamaz; bunlar deneysel veya quasi-experimental analiz gerektirir.

### 7. Klinik kodlama uygulamaları zamanla değişebilir

Bir kurum DRG kodlama pratiğini değiştirirse (örneğin daha fazla komorbidite kodlamaya başlarsa), modelin tahmin desenleri eskir. Periyodik yeniden eğitim gerekir.

### 8. Confidentiality

Worst-prediction CSV, model artifact (`xgb_model.json`) ve patient-level çıktılar **public GitHub'a koyulmaz**. `.gitignore` bunları dışlıyor; ayrıca public paylaşım yapılmadan önce commit history dahil repository yeniden kontrol edilmelidir. En güvenli yaklaşım, kod ve reproducibility artefaktlarını private olarak paylaşmaktır.

---

# BÖLÜM 5 — ÖNERİLER (Recommendations)

Bu bölüm **özellikle yönetici paydaşlara** yönelik. Rakamdan çok karara odaklanır.

## 5.1 — Hemen Uygulanabilir 3 Kullanım Alanı

### Öneri 1: Otomatik "Olağandışı Fatura İnceleme Kuyruğu"

**Ne:** Model her hafta tamamlanan epizodlardan, beklenenden belirgin sapan vakaları listeler (örneğin tahminin %50 üstünde gerçekleşen). Funding & Costing ekibi bu listeyi haftalık review queue olarak kullanır.

**İş etkisi:**
- Manuel review zamanında tasarruf potansiyeli
- Episodes with unusually large residuals can be prioritised for analyst review
- Contract-review discussions için "bu vaka tipinde expected charge $X, actual charge $Y" gibi case-mix odaklı kanıt üretimi

**Önkoşul:** Model haftalık veriyle güncellenmeli; deployment yaklaşımı data access, governance, integration ve security requirements'a göre belirlenmelidir.

---

### Öneri 2: MDC-Spesifik "Beklenen Charge Bandı" Raporu

**Ne:** Her MDC için aylık olarak medyan, P25–P75 aralığı, P90 değerleri otomatik üretilir. Kontrat müzakerelerinde referans tablo olarak kullanılır.

**İş etkisi:**
- Sigorta ve contract-review görüşmelerinde tek bir "ortalama" rakam yerine **klinik gruba özgü charge benchmark'ları**
- "Ne kadar charge ediyoruz?" sorusuna aggregate, segment-bazlı cevap
- Benefit ve actual cost data ile birlikte yorumlandığında daha derin commercial review desteği

**Önkoşul:** Halihazırda `reports/mdc_cost_summary.csv` çıktısı bunun temelini oluşturur; production önerisi olarak Power BI/Tableau dashboard'a bağlanabilir.

---

### Öneri 3: Same-day vs Overnight Ayrı Benchmarking

**Ne:** Aynı MDC içinde same-day ve overnight vakalar tamamen farklı billed-charge profiline sahip. Performans ölçümünde, kontrat incelemesinde, klinik karşılaştırmalarda bu ayrım kullanılmalı.

**İş etkisi:**
- "Ortalamaya gömülmüş" gerçek performans farklarının ortaya çıkması
- Daha doğru klinik unit-level benchmarking

**Önkoşul:** Mevcut raporlama altyapısının segment dimension'ına bu ayrımın eklenmesi.

## 5.2 — Orta Vadeli (3–6 ay) Genişleme Önerileri

### Öneri 4: Admission-Time Sensitivity ve v2 Modeli

**Ne:** Removing LOS and procedure count provides an initial sensitivity test. A true admission-time model must be retrained using only features verified as available at admission. Bu ayrım için ayrı bir feature availability listesi kullanılmalı:
- Available at admission: Age, Sex, UrgencyOfAdmission, admission month; provisional diagnosis/MDC varsa ayrıca doğrulanmalı
- Available during episode: evolving care/activity fields
- Available after separation/coding: LOS, SameDayStatus, ModeOfSeparation, final MDC, final comorbidity count, final procedure count

**İş etkisi:**
- Yatak/kaynak planlamasında erken uyarı
- Sigorta authorisation süreçlerini hızlandırma
- ICU/theatre kaynak tahsisinde erken bilgi

**Risk:** Performansın daha düşük olması beklenir, fakat mevcut R² 0.6753 sonucu garanti edilmiş admission-time performansı değildir; post-episode alanlar hâlâ feature set içinde olabilir. Bu nedenle v2 "ön-değerlendirme" olarak konumlandırılmalı ve yeniden eğitilmelidir.

---

### Öneri 5: Gerçek Maliyet Verisi ile Yeniden Eğitim

**Ne:** Şu anda charge tahmin ediyoruz. Eğer hastanenin gerçek operasyonel maliyet verisi (personel saatleri, malzeme, overhead allocation) eklenirse, model "gerçek cost" hedefi için yeniden eğitilebilir.

**İş etkisi:**
- True cost ve profitability per episode/MDC ölçümüne yaklaşma
- Loss-making prosedürlerin tanımlanması
- Stratejik portfolio kararları (hangi vakalara genişlemeli, hangileri optimize edilmeli)

**Önkoşul:** Finans ekibiyle veri paylaşımı; veri yönetişimi anlaşması.

---

### Öneri 6: Çoklu Hastane Federasyonu

**Ne:** SJGHC'nin diğer hastanelerinin verisiyle her hastane için ayrı bir kalibre edilmiş model + hastane-üstü bir genel model. Federe/transfer learning yaklaşımı.

**İş etkisi:**
- Grup-genelinde benchmarking
- "Hangi hastane hangi tip vakada görece yüksek billed-charge profiline sahip?" sorusuna cevap
- Best-practice tespit ve transferinin kolaylaşması

**Risk:** Veri yönetişimi karmaşıklığı; her hastanenin kendi kodlama pratiği farklı olabilir.

## 5.3 — Uzun Vadeli (6–12 ay) Strateji Önerileri

### Öneri 7: Continuous Monitoring Pipeline

Modelin zamanla performansının düşmesi (model drift) doğaldır. Aylık otomatik kontrol:
- Yeni epizodlarda tahmin hatası dağılımı
- Top-decile recall korunuyor mu?
- Klinik kodlama desenlerinde değişim var mı?

Eşik aşıldığında otomatik retrain tetiklenir. Bu, "akademik proje" ile "production analytics" arasındaki farktır.

---

### Öneri 8: Veri Kalitesi Otomatik Kontrol Katmanı

[reports/data_quality_summary.csv](reports/data_quality_summary.csv) içindeki 9 kontrol, **veri yüklemesi anında** otomatik çalıştırılmalı. Anomali eşik üstünde olduğunda HCP submission durdurulmalı; manuel review tetiklenmeli. Bu, hatalı verinin Australian Government'a gitmeden yakalanmasını sağlar.

---

### Öneri 9: Power BI Açıklanabilirlik ve Monitoring Dashboard'u

Production önerisi olarak monthly Power BI dashboard; actual versus expected charge, residual review queues, high-charge flags, MDC/DRG benchmarks, same-day versus overnight comparisons and model monitoring metrics gösterebilir. Her tahmin için klinik personel veya finans ekibi SHAP açıklamasını görebilmeli: "Bu epizod için tahmin $X çünkü 1) yatış süresi şu, 2) prosedür sayısı şu, 3) MDC şu..." Bu dashboard henüz inşa edilmedi; operationalisation önerisidir.

## 5.4 — Genel Tavsiye: "Model Bir Araç, Karar Değil"

Bu rapor boyunca dikkat ettiğim şey: hiçbir yerde "model şöyle karar vermeli" demedim. Modelin görevi **kararı destekleyen sinyali sunmak**, klinik veya finansal kararı vermek değil. Funding & Costing ekibinin profesyonel yargısı, modelin tahminiyle birlikte değerlendirilmeli.

> Bu felsefe sunumda korunmalı: "Bu model uzmanı ikame etmek için değil, uzmanı daha güçlü kılmak için."

---

# EK A — Metodoloji Sözlüğü (Teknik Olmayan Paydaşlar İçin)

| Terim | Anlatım |
|---|---|
| **Epizod** | Bir hastanın hastaneye yatışından çıkışına kadar olan tek "olay". Aynı hasta birden çok epizod yaşamış olabilir. |
| **MDC** | Major Diagnostic Category. Tüm hastalıkları 26 büyük gruba ayıran sınıflandırma (sinir sistemi, kalp-damar, sindirim, vb.). |
| **DRG** | Diagnosis-Related Group. MDC'den daha ince bir sınıflandırma; aynı MDC içinde alt-tipleri ayırır. |
| **LOS** | Length of Stay. Hastanede kalış süresi (gün). |
| **HCP** | Hospital Casemix Protocol. Avustralya hükümetinin özel hastanelerden topladığı standart epizod verisi. |
| **R²** | "Modelin açıkladığı değişkenliğin oranı". 1.0 mükemmel, 0.0 hiçbir şey öğrenememiş demek. 0.81 = %81. |
| **MAE** | Mean Absolute Error. "Tipik vakada tahmin gerçekten ortalama kaç dolar uzakta?" |
| **RMSE** | Root Mean Squared Error. MAE gibi ama büyük hataları daha çok cezalandırır. |
| **SHAP** | Bir tahmin modelin "neden böyle düşündüğünü" matematiksel olarak açıklayan yöntem. |
| **Data leakage** | Model hedef hakkında doğrudan bilgi içeren bir feature kullanırsa, sahte yüksek performans ortaya çıkar. Bu çalışmada formal audit, feature'lar ile billed-charge component'leri arasında direct overlap bulmadı. |
| **Same-day** | Hastanın aynı gün geldiği ve aynı gün çıktığı epizod (LOS = 0). |

---

# EK B — Anahtar Dosya Referansları

| Sunumda Bahsedeceğin Şey | Hangi Dosyada |
|---|---|
| Yönetici özet rakamları | [reports/executive_summary.csv](reports/executive_summary.csv) |
| MDC-bazlı charge benchmark tablosu | [reports/mdc_cost_summary.csv](reports/mdc_cost_summary.csv) |
| Model karşılaştırma | [reports/model_comparison.csv](reports/model_comparison.csv) |
| Segment performansı | [reports/segment_performance.csv](reports/segment_performance.csv) |
| High-charge yakalama | [reports/high_cost_capture.csv](reports/high_cost_capture.csv) |
| Feature ablation | [reports/feature_ablation.csv](reports/feature_ablation.csv) |
| Veri kalitesi | [reports/data_quality_summary.csv](reports/data_quality_summary.csv) |
| Leakage audit | [reports/leakage_audit.csv](reports/leakage_audit.csv) |
| Feature listesi & availability | [reports/feature_list.csv](reports/feature_list.csv) |
| Final metrikler (JSON) | [reports/final_metrics.json](reports/final_metrics.json) |
| Sınırlamalar | [reports/limitations.md](reports/limitations.md) |
| Hedef tanımı | [reports/target_composition.csv](reports/target_composition.csv) |
| Sunum slayt taslağı | [reports/presentation_outline.md](reports/presentation_outline.md) |

## Sunumda Kullanılacak Anahtar Grafikler

Not: Aşağıdaki figür listesi teknik kanıt envanteridir. Hangi figürün hangi slayta gireceği ve hangi detayların appendix'e taşınacağı için ayrı 10-slide presentation production brief'e bakılmalıdır.

| Grafik | Hangi Slaytta? |
|---|---|
| `figures/01_categorical_distributions.png` | Veri genel bakış |
| `figures/03_charge_distribution.png` | Sağa çarpık dağılım |
| `figures/03_mdc_cost.png` | MDC bazlı charge farkları |
| `figures/03_los_vs_cost.png` | LOS = 0 vs LOS > 0 farkı |
| `figures/03_comorbidity_cost.png` | Komorbidite-charge ilişkisi |
| `figures/03_sameday_vs_overnight.png` | Same-day vs overnight |
| `figures/04_actual_vs_predicted.png` | Model performans (scatter + residual) |
| `figures/05_model_scorecard.png` | Tek bakışta model performans kartı |
| `figures/04_shap_summary.png` | Hangi özellikler önemli? |
| `figures/04_feature_importance.png` | Önem sıralaması bar chart |
| `figures/04_shap_waterfall_*.png` (×3) | 3 farklı vakanın açıklaması |
| `figures/04_shap_dependence_los.png` | LOS-tahmin etki eğrisi |
| `figures/04_shap_dependence_procedure_count.png` | Prosedür sayısı etki eğrisi |

---

# EK C — Sıkça Sorulması Beklenen Sorular ve Hazır Cevaplar

### S1: Neden XGBoost'u tercih ettiniz, Random Forest daha iyi değil miydi?

> Random Forest achieved the strongest held-out predictive performance (R² 0.8118). XGBoost produced near-equivalent results (R² 0.8087) and was retained as a challenger for detailed SHAP explanation and temporal robustness analysis. Ben **XGBoost'u açıklama modeli olarak** kullandım çünkü:
> 1) Performans farkı pratik olarak küçük,
> 2) XGBoost SHAP TreeExplainer ile native uyumlu; açıklanabilirlik için daha temiz çıktı veriyor,
> 3) Time-split'te iki model neredeyse eşit.
> Sonuç olarak her ikisi de viable; bu çalışmada **Random Forest = en iyi held-out performans**, **XGBoost = çok yakın challenger ve SHAP/time-split tercihi**.

### S2: R² 0.80 yeterli mi?

> Episode billed charge regression için 0.80+ güçlü bir sonuçtur. Ama dikkat: bu **R²** "accuracy %80" değil. Doğru ifade: "Held-out test setindeki charge değişkenliğinin yaklaşık %81'i model tarafından açıklanıyor." Bu, ortalamayı tahmin etmekten çok daha bilgilendirici.

### S3: Veri sızıntısı (leakage) riski yok mu?

> The formal audit found no direct overlap between model features and the billed-charge components used to construct the target. Hedef değişken 11 charge bileşeninin toplamı. Modelde kullanılan 11 feature'ın **hiçbiri** bu bileşenlerden değil. [reports/leakage_audit.csv](reports/leakage_audit.csv) bunu test ediyor; "overlap = 0". Episode-completion feature'ları target-component leakage değildir, fakat kullanım zamanını sınırlar.

### S4: Bu model gerçek-zamanlı tahmin için kullanılabilir mi?

> Hayır. LOS, procedure_count, final MDC gibi özellikler epizod tamamlandıktan sonra bilinir. Bu yüzden modelin kullanım alanı **completed episode benchmarking** ve **unusual charge review**. Admission-time tahmin için ayrı bir v2 modeli kurulabilir (öneri 4).

### S5: Veri kalitesini nasıl ele aldınız?

> 9 farklı kontrol otomatik çalıştırıldı: negative LOS, same-day/date mismatch, ICU/theatre tutarsızlığı, zero total charge, whitespace missing, duplicate ID, missing target vb. Sonuçlar [reports/data_quality_summary.csv](reports/data_quality_summary.csv) içinde. En kayda değer bulgu: HCP verisinde eksikler `NaN` değil **whitespace** olarak saklanıyor — bunu yakaladım, naif null kontrolünün eksikleri kaçıracağını gösterdim.

### S6: Etik ve gizlilik?

> Veri zaten de-identified. Buna ek olarak:
> - Raw Excel, processed parquet ve patient-level outputs `.gitignore` ile public repo'dan dışlandı.
> - `reports/worst_predictions.csv` (50 satır row-level review) lokal-only.
> - Model artifact (`xgb_model.json`) lokal-only.
> - Public paylaşım yapılmadan önce commit history dahil repository tekrar kontrol edilmeli; en güvenli yol private paylaşım.

### S7: Modeliniz neden basit bir lineer regresyondan çok iyi?

> Charge dağılımı sağa çarpık ve özellikler arası etkileşim var (örneğin "MDC=I & LOS>5 birlikte yüksek billed charge" gibi). The linear baseline performed poorly after back-transformation, reflecting model misspecification for nonlinear charge patterns and sensitivity to extreme predictions. Tablo [reports/model_comparison.csv](reports/model_comparison.csv) bu farkı rakamla gösteriyor.

### S8: Tek hastanedeki sonuçlar genelleştirilebilir mi?

> Doğrudan hayır. Bu hastanenin (HospitalType=2, özel akut bakım, gözlenen 14 ay) profili genelleme için yeterli değil. Başka SJGHC hastanelerine taşımadan önce o hastanelerin verisiyle yeniden doğrulanmalı. Bunu sınırlamalar bölümünde açıkça yazdım.

### S9: SHAP ile "X özelliğini değiştirsek charge düşer mi?" sorabilir miyim?

> Hayır. SHAP **modelin nasıl davrandığını** gösterir, dünyanın nedensel yapısını değil. Yatış süresi-charge ilişkisi SHAP'ta güçlü görünüyor, ama bu "yatış süresini kısaltırsak billed charge düşer" demek değildir; "model predicted charge için yatış süresine büyük ağırlık veriyor" demektir. Nedensel iddialar için deneysel veya quasi-experimental analiz gerekir.

### S10: Bu projeyi production'a almak için ne gerekir?

> A delivery estimate would depend on data access, governance, integration and deployment requirements. I would begin with a short discovery and validation phase. Üç katman ayrıca tasarlanmalı:
> 1. **Veri katmanı:** Aylık HCP submission akışına model girdi pipeline'ı bağlanmalı.
> 2. **Model katmanı:** Eğitim/inference ortamı ve monitoring yaklaşımı seçilmeli.
> 3. **Tüketim katmanı:** Funding & Costing ekibi için Power BI dashboard operationalisation'ı değerlendirilmeli.

---

# Kapanış Notu

Bu çalışma "tek seferlik bir analiz" değil, **tekrarlanabilir bir analitik temeldir**. Tek komutla baştan sona yeniden üretilir ([scripts/generate_validation_outputs.py](scripts/generate_validation_outputs.py)); bütün metrikler dokümantedir; bütün kararlar yazılı gerekçeyle sunulur.

Sunumda hedeflediğim mesaj üçtür:

1. **Veriyi anlıyorum.** HCP'nin tuhaflıkları, kodlama desenleri, eksik kalıpları farkındayım.
2. **Modeli savunabiliyorum.** Tek bir rakamı değil, alternatifleriyle birlikte tüm yöntem zincirini biliyorum.
3. **İşi konuşabiliyorum.** Funding & Costing ekibinin günlük diline tercüme edilmemiş hiçbir teknik ayrıntı bırakmıyorum.

Bu üçü panel karşısında doğru aktarılırsa, projenin teknik değerinden bağımsız olarak, **rol için doğru kişi olduğum** ortaya çıkar — ki sunumun gerçek amacı budur.
