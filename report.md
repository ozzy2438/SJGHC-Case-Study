# SJGHC HCP Case Study — Detaylı Sunum Raporu

> **Yazar:** Osman Orka  
> **Pozisyon:** Data Scientist (Funding & Costing) — St John of God Health Care  
> **Veri:** De-identified HCP (Hospital Casemix Protocol) Episode Data, 2022–2023  
> **Tarih:** 26 Haziran 2026  
> **Repo:** https://github.com/ozzy2438/SJGHC-Case-Study

---

## Bu Raporu Nasıl Okumalı?

Bu rapor **iki farklı paydaş kitlesine** aynı anda hitap etmek için yazıldı.

| Eğer sen... | Şu bölümlere odaklan |
|---|---|
| **Hastane yöneticisi / iş paydaşı** isen | "Neden Önemli?", "İş Çıktısı", "Öneriler" kutuları |
| **Veri ekibi lideri / teknik paydaş** isen | "Teknik Detay", "Yöntem Seçim Gerekçesi", "Doğrulama" kutuları |

Her bölümde **aynı bilgi iki dilde anlatılıyor**: önce iş dilinde "ne yaptık ve neden iş açısından önemli", sonra teknik dilde "nasıl yaptık ve neden bu yöntemi seçtik". Hızlı bir tur isteyenler "Yönetici Özeti" ile başlayıp ardından kendi bölümüne atlayabilir.

Yapı: **Task → Situation → Action → Result → Recommendations**.

---

## Yönetici Özeti (One-Pager)

**Soru:** Tamamlanmış bir hasta epizodunun beklenen faturasını ne kadar iyi tahmin edebilir, olağandışı pahalı vakaları nasıl belirleyebiliriz?

**Yaklaşım:** 30,615 de-identified HCP epizodu üzerinde 6 aşamalı, baştan sona reproducible bir analitik hat (data → temizlik → keşifsel analiz → modelleme → açıklanabilirlik → çıktı) kuruldu.

**Ana sonuç:**

| Ölçüm | Değer | Anlamı |
|---|---|---|
| Held-out test R² (Random Forest) | **0.812** | Modelimiz epizod faturalarındaki değişkenliğin yaklaşık %81'ini açıklıyor |
| Ortalama mutlak hata (MAE) | **$720** | Tipik bir epizod için tahmin, gerçeğe ortalama $720 farkla yaklaşıyor |
| Yüksek maliyet yakalama (top-decile recall) | **%77.1** | En pahalı %10 vakayı yakalama oranı |
| Zaman tabanlı test R² | **0.776** | Geleceğe genelleme de güçlü; tek seferlik şans değil |
| Kullanılan özellik sayısı | **11** | Hepsi klinik/operasyonel; charge bileşeni hiçbiri değil (sızıntı yok) |

**İş çıktısı (3 acil kullanım alanı):**

1. **Olağandışı fatura inceleme kuyruğu:** Model, beklenenden belirgin sapan epizodları işaretler. Funding & Costing ekibi haftalık inceleme listesi olarak kullanabilir.
2. **MDC bazında beklenen charge bandı:** Kontrat müzakeresi ve bütçe planlama için her MDC kategorisinde tipik fatura aralığı.
3. **Same-day vs overnight ayrı benchmark:** Aynı klinik etiket altında günübirlik ve yatılı vakalar tamamen farklı maliyet profiline sahip; ortalamadan değil, doğru segmentten karşılaştırılmalı.

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

> 📦 **Neden önemli? (yönetici görüşü):** Sağlık kuruluşları için maliyet öngörülebilirliği = nakit akışı, kontrat müzakere gücü ve sigorta ödemelerini doğru talep etme yeteneğidir. Vakaların önceden tahmin edilemediği bir ortamda planlama yapmak çok zordur.

> 🔬 **Teknik perspektif:** Bu, **tabular supervised regression** problemine indirgeniyor. Hedef: log-dönüşümlü `total_charge_aud`. Çoğu vaka düşük maliyetli, az sayıda vaka çok yüksek maliyetli (right-skewed → log-transform gerekçesi).

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
- **MDC kodları DRG'den türetiliyor:** DRG kodunun ilk harfi MDC'yi verir (A–Z), 26 kategorik klinik grup.

### En kritik durum tespiti: "Bu basit bir tablo değil, kodlanmış bir kayıt sistemi"

Veri 162 sütun ama bunların önemli bölümü dolu görünmüyordu. Detaylı analiz sonucu:

| Doluluk Aralığı | Sütun Sayısı |
|---|---|
| %100 boş (tek bir kayıt bile yok) | 27 |
| %50–99 boş | 84 |
| %5–49 boş | 3 |
| < %5 boş | 48 |

> 📦 **İş paydaşı için anlamı:** Veri "varmış gibi görünüyor" ama büyük kısmı bu hastane için anlamlı değil. Bu **bir veri kalitesi sorunu değil**, kayıt sisteminin hastaneye özel doldurulması meselesidir. Örneğin doğum/yenidoğan alanları bu hastane için neredeyse boş; çünkü bu özel akut bakım hastanesinde doğum aktivitesi yok.

> 🔬 **Teknik karar:** ≥ %99.9 boş sütunlar düşürüldü (64 sütun). Bu, modelleme öncesi gürültüyü temizler ve özellik mühendisliği aşamasında kafa karışıklığını azaltır. Ancak silmek yerine **dokümante edip raporladım** (`reports/null_summary.csv`). Çünkü gerçek bir prodüksiyon ortamında bu sütunlar başka hastane için dolu olabilir.

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
| `LOS` | `SeparationDate - AdmissionDate` (gün) | Hastanede yatış süresi; maliyetin en güçlü doğal sürücüsü |
| `Age` | `AdmissionDate - DateOfBirth` (doğum günü düzeltmesi dahil) | Demografik sürücü |
| `comorbidity_count` | `Diagnosis_2..10` dolu alanların sayısı | Klinik karmaşıklık göstergesi |
| `procedure_count` | `Procedure_1..10` dolu alanların sayısı | Yapılan klinik müdahale yoğunluğu |
| `MDC` | `DRG`'nin ilk harfi | 26 klinik kategoriye indirgenmiş tanı grubu |
| `adm_month` | Admission tarihinin ayı | Mevsimsel/dönemsel etki için |

> 📦 **Yöneticiye anlamı:** Ham veri "şu hastaya şu işlem yapıldı" listesi gibi. Bizim oluşturduğumuz özellikler ise "bu epizod ne kadar karmaşık, ne kadar yoğundu, hangi klinik gruba aitti" sorularına özet cevap veren değişkenler. Bunlar olmadan model klinik bağlamı anlayamaz.

> 🔬 **Teknik karar — Neden bu özellikler ve neden bunlar yeterli:** Sağlık verisi denetiminde **özellik sayısını az tutmak** anlaşılabilirliği artırır. Onlarca düşük katkı sağlayan sütun yerine 11 yüksek değerli sütun seçtim. Feature ablation testi (Bölüm 3.4) bu seçimi rakamla destekliyor.

### Hedef değişkenin tanımı — kritik bir kayıt

`total_charge_aud` hedefi, **target_composition.csv** dosyasında tüm bileşenleriyle dokümante edildi. Bileşenler:

```
AccommodationCharge + TheatreCharge + LabourWardCharge + ICU_Charge +
ProsthesisCharge + PharmacyCharge + OtherCharges + BundledCharges +
HIH_Charges + SCN_Charges + CCU_Charges
```

Bu kritik çünkü: **modelde kullanılan hiçbir özellik bu listede yok**. Yani bir feature'ın hedefi "kopyalamasından" doğacak veri sızıntısı (data leakage) riski sıfır. Bu hesaplama [reports/leakage_audit.csv](reports/leakage_audit.csv) içinde otomatik olarak doğrulanır.

> 📦 **Neden bunu özellikle vurguluyorum?** Model performans rakamları (R² = 0.81) "yapay yüksek" olabilir eğer model hedefi oluşturan bir alanı feature olarak görüyorsa. Bu kontrolü yapmasaydım, model gerçek dünyada çalışmaz, sunumda sorulduğunda da cevapsız kalırdım.

## 2.3 — Keşifsel Veri Analizi (NB3)

7 sunum kalitesinde grafik üretildi (her biri `figures/03_*.png`). Burada yalnızca kilit içgörüler:

### İçgörü 1: Charge dağılımı sağa çarpık

- Medyan: $650
- Ortalama: $2,685 (medyanın 4 katı)
- Maksimum: $69,138

> 📦 **İş anlamı:** Vakaların yarısı $650 altında, ancak az sayıda yüksek maliyetli vaka ortalamayı yukarı çekiyor. "Ortalama vaka maliyeti" rakamı pratikte yanıltıcı; medyan ve segment bazlı bakmak daha doğru.

> 🔬 **Modelleme kararı:** Hedef değişkene `log1p()` dönüşümü uygulandı. Bu, modelin yüksek-maliyet vakalardan orantısız etkilenmemesini sağlar; standart bir yöntemdir.

### İçgörü 2: LOS = 0 (günübirlik) vs LOS > 0 (yatılı) arasında 14 kat fark

- Günübirlik medyan: $480
- Yatılı medyan: $6,948

> 📦 **İş anlamı:** Aynı klinik etiketle (örneğin "L = Böbrek/Üriner") gelen iki vakadan biri günübirlik diyaliz, diğeri yatılı tedavi olabilir. **Hacim bazında** Böbrek/Üriner en kalabalık MDC (%32.7) ama **maliyet bazında** öyle değil. Yöneticilere bunu vurgulamak: "kalabalık ≠ pahalı".

> 🔬 **Modelleme anlamı:** SameDayStatus ve LOS, model özelliklerinde tutulmalı; bunlar gerçek dünyada da güçlü ayrıştırıcılar. Ancak admission-time'da bilinmedikleri için model "completed episode" kapsamında.

### İçgörü 3: MDC kategorileri arasında 25 kat fark

| MDC | Açıklama | Medyan Charge | Pay |
|---|---|---|---|
| K | Endokrin/Beslenme | $8,764 | %2.3 |
| O | Gebelik/Doğum | $6,970 | %3.2 |
| I | Kas-İskelet | $6,329 | %20.2 |
| L | Böbrek/Üriner | $357 | **%32.7** (en kalabalık) |
| R | Ruhsal | $480 | %22.8 |

> 📦 **Kontrat müzakeresinde anlamı:** Her MDC ayrı bir "ürün". Sigorta şirketiyle kontrat müzakere ederken tek bir ortalama rakam değil, MDC-bazlı bantlar konuşulmalı. Bizim oluşturduğumuz [reports/mdc_cost_summary.csv](reports/mdc_cost_summary.csv) tam bu amaçla.

### İçgörü 4: Komorbidite sayısı maliyetle birlikte artıyor

Kayıtlı komorbidite sayısı arttıkça medyan fatura sistematik olarak yükseliyor. Bu beklenen bir ilişki; modelimizin bu sinyali yakaladığını doğruluyor.

> 🔬 **Teknik uyarı:** Bu bir **korelasyon**, nedensellik değil. "Daha çok komorbidite kodlanması maliyeti artırıyor" denemez; "daha karmaşık vakalar hem daha çok komorbidite ile kodlanıyor hem daha pahalı oluyor" demek doğru. Sunumda bu nüans korundu.

## 2.4 — Modelleme Yaklaşımı (NB4)

### Neden çoklu model karşılaştırması?

Eğer sadece "XGBoost kullandık, R² = 0.81" deseydim, panel haklı olarak şunu sorardı: "Daha basit bir modelden ne kadar iyi?" Bu sorunun cevabı olmadan tek bir model rakamı havada kalır.

Bu yüzden **5 model karşılaştırıldı**, her ikisi de **iki ayrı split** stratejisiyle:

#### Tablo: Random split (80/20)

| Model | MAE | RMSE | R² | Yorum |
|---|---|---|---|---|
| Mean baseline | $2,814 | $4,217 | ≈ 0 | "Her vakaya ortalama tahmini" — kontrol noktası |
| Median baseline | $2,231 | $4,659 | -0.22 | Sağa çarpık dağılım nedeniyle ortalamadan daha kötü |
| Linear Regression | $1,977 | $16,162 | -13.69 | Log dönüşüm sonrası back-transform doğrusal modelde patladı — beklenen davranış |
| Random Forest | **$720** | **$1,829** | **0.812** | En iyi held-out performans |
| XGBoost | $741 | $1,852 | 0.807 | Çok yakın challenger, SHAP/açıklanabilirlik için tercih edildi |

#### Tablo: Time split (son %20 admission date)

| Model | MAE | RMSE | R² |
|---|---|---|---|
| Random Forest | $761 | $2,068 | 0.776 |
| XGBoost | $768 | $2,071 | 0.776 |

> 📦 **Yönetici özeti:** "Model çalıştı" demek için tek skor yetmez. 5 farklı yöntemi yan yana koyduk; bizim yöntem hepsinden iyi çıktı. Ayrıca "geçmişle eğit, gelecekteki vakalarda dene" testinde de tutarlı: performans biraz düşüyor ama dramatik değil. Yani model bir mevsim tutmasıyla ortaya çıkmış bir tesadüf değil.

> 🔬 **Yöntem seçim gerekçesi:**
> - **Mean/Median baseline:** Her ML projesinde olmazsa olmaz. Modelin gerçekten bir şey öğrenip öğrenmediğini gösterir.
> - **Linear Regression:** Sağa çarpık, etkileşimli verilerde doğrusal modellerin yetersizliğini göstermek için referans. Sonuç bu beklentiyi doğruladı.
> - **Random Forest:** Tabular regression'da güçlü, hiperparametre-hassas değil, paralel eğitim hızlı.
> - **XGBoost:** Tabular state-of-the-art benchmark; ayrıca **SHAP TreeExplainer** ile native uyumlu olduğu için açıklanabilirlik tarafında belirgin avantaj.

### XGBoost hiperparametreleri

```
n_estimators=350, max_depth=5, learning_rate=0.05,
subsample=0.80, colsample_bytree=0.80,
min_child_weight=10, gamma=0.05,
reg_alpha=0.10, reg_lambda=1.0
```

> 🔬 **Neden bu değerler?** `max_depth=5` ve `min_child_weight=10` overfitting'i önler; `subsample/colsample=0.80` ek stokastiklik sağlar; `reg_alpha/reg_lambda` regularization log-target üzerinde daha kararlı convergence için. Bu kombinasyon bir grid search sonucu değil, sağlık tabular verilerinde standart başlangıç noktasıdır; CV sonuçları (RMSE = 0.539 ± 0.011) düşük varyans gösterdiği için ek tuning'in iş etkisi marjinal olurdu.

### Çapraz doğrulama (CV)

5-katlı KFold CV, log-target üzerinde:
- **CV log-RMSE = 0.5388 ± 0.0112**

> 📦 **Anlamı:** "Bu performans şanstan değil"in matematiksel kanıtı. 5 farklı veri ayrımında benzer performans alıyoruz.

## 2.5 — Açıklanabilirlik: SHAP

Bir tahmin modeli sadece "ne kadar doğru" değil, "neden öyle tahmin etti" sorusuna da cevap vermeli. Bu özellikle sağlıkta önemli; çünkü kara kutu çıktı, klinik personelin güvenini kazanamaz.

### SHAP nedir, neden seçildi?

SHAP (SHapley Additive exPlanations), oyun teorisinden gelen bir yöntem; bir tahminin her bir özellikten **ne kadar katkı** aldığını matematiksel olarak hesaplar. Tree-based modellerde (RF, XGBoost) `TreeExplainer` ile O(TLD²) sürede tam çözüm verir.

### Üretilen SHAP çıktıları

1. **Global summary plot** ([figures/04_shap_summary.png](figures/04_shap_summary.png)): Her özelliğin tahmindeki ortalama mutlak etkisi.
2. **Bar feature importance** ([figures/04_feature_importance.png](figures/04_feature_importance.png)): Aynı bilginin sade görseli.
3. **3 adet waterfall örneği**:
   - `04_shap_waterfall_low_sameday.png` — düşük maliyetli günübirlik
   - `04_shap_waterfall_typical_mid.png` — tipik orta maliyetli vaka
   - `04_shap_waterfall_high_complex.png` — yüksek maliyetli karmaşık vaka
4. **2 adet dependence plot**: LOS ve procedure_count için tahmin üzerindeki nonlineer etki eğrisi.

### Bulgular (önem sırasıyla)

1. **LOS (yatış süresi)** — en güçlü tahmin sürücüsü
2. **Procedure count** — yapılan müdahale sayısı
3. **MDC** — klinik kategori
4. **Comorbidity count** — klinik karmaşıklık
5. **SameDayStatus** — günübirlik mi yatılı mı
6. Geri kalanlar (Age, Sex, CareType vb.) belirgin biçimde daha düşük etki

> 📦 **İş paydaşına anlatım:** "Modelimiz bir vakanın faturasını tahmin ederken en çok yatış süresine, sonra yapılan işlem sayısına bakıyor. Yaş ve cinsiyet gibi demografik bilgiler beklenenden daha az ağırlığa sahip — yani vaka karmaşıklığı temel sürücü, hasta profili değil." Bu, kontrat müzakerelerinde önemli bir argüman: "Bizim hasta profilimiz pahalı değil, vakalarımız karmaşık."

> 🔬 **Önemli teknik nüans:** SHAP **modelin nasıl davrandığını** gösterir, dünyanın nedensel yapısını değil. Yani "yatış süresini azaltırsak maliyet düşer" cümlesi SHAP'tan çıkmaz; SHAP yalnızca "model yatış süresine büyük ağırlık veriyor" der. Bu ayrım sunumda korundu.

## 2.6 — Doğrulama Paketi: "Bu Sonuçları Gerçekten Savunabilir misin?"

Bu, projenin en az model kadar önemli olan kısmı. Tek komut çalıştırıldığında üretilen 10 kontrol/raporu kapsar:

```bash
python scripts/generate_validation_outputs.py
```

| Çıktı | Ne Yapar | Neden Önemli |
|---|---|---|
| `leakage_audit.csv` | Charge bileşeni feature olarak kullanılmış mı? | Sızıntı olmadığını kanıtlar |
| `feature_list.csv` | 11 feature'ı tek tek dokümante eder | "Hangi alanlar kullanılıyor?" sorusuna kanıtlı cevap |
| `model_comparison.csv` | 5 model × 2 split | "Neden XGBoost?" sorusuna cevap |
| `segment_performance.csv` | Same-day/overnight/cost band/MDC bazlı performans | "Model bazı segmentlerde zayıf mı?" |
| `high_cost_capture.csv` | Top-decile recall/precision | "En pahalı vakaları yakalayabiliyor musunuz?" |
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

| Metrik | Random Forest (random split) | XGBoost (random split) | XGBoost (time split) |
|---|---|---|---|
| MAE | $719.66 | $740.86 | $768.23 |
| RMSE | $1,828.93 | $1,851.89 | $2,071.45 |
| R² | **0.812** | 0.807 | 0.776 |

> 📦 **Yöneticiye çevirisi:**
> - Modelimiz tipik bir vaka için ortalama **$720 hata** ile tahmin yapıyor.
> - "Vakaların maliyetindeki değişkenliğin **yaklaşık %81'ini** açıklıyor."
> - Gelecekteki dönemde de (time-split testi) **%78** civarı performans devam ediyor.

## 3.2 — Hangi Segmentlerde İyi, Hangilerinde Zayıf?

[reports/segment_performance.csv](reports/segment_performance.csv) içinden seçili satırlar:

| Segment | n | Medyan Gerçek Charge | MAE | R² |
|---|---|---|---|---|
| Same-day | 4,836 | $480 | $324 | 0.59 |
| Overnight/multi-day | 1,242 | $7,057 | $2,287 | 0.66 |
| Low-cost (≤ train medyanı $650) | 3,266 | $357 | $55 | -3.85 |
| Mid-cost ($650 – $7,892) | 2,263 | $2,553 | $984 | 0.26 |
| High-cost (> $7,892) | 594 | $12,816 | $3,588 | -0.20 |

> 📦 **Önemli yorum:**
> - **Düşük maliyetli vakalarda** $55 ortalama hata "az gibi görünüyor" ama R² negatif. Bunun nedeni: düşük maliyetli vakaların kendi içlerinde çok az değişkenlik var (medyan $357), o yüzden R² metriği bu segmentte yanıltıcı. Pratikte $55 hata = çok iyi.
> - **Yüksek maliyetli vakalarda** model exact rakam vermede zorlanıyor (R² negatif), ama bu vakaların **var olduğunu** yakalayabiliyor (bkz. 3.3 — top-decile recall %77).
> - **Yönetici dilinde:** "Model 'tipik' vakaları çok iyi tahmin ediyor; en uç vakaların kesin dolar miktarını yakalamak zor, ama bu vakaların pahalı olacağını fark edebiliyor — ki review queue için bu yeterli."

## 3.3 — Yüksek Maliyetli Vaka Yakalama

[reports/high_cost_capture.csv](reports/high_cost_capture.csv):

| Metrik | Değer |
|---|---|
| Top decile recall | **%77.1** |
| Top decile precision | **%74.7** |
| Gerçek high-cost vaka sayısı | 594 |
| Model'in işaretlediği high-cost sayısı | 613 |
| Doğru işaretleme (TP) | 458 |

> 📦 **İş çıktısı:** Eğer Funding & Costing ekibi haftada en yüksek maliyetli %10 vakayı manuel inceliyorsa, model bu listenin **dörtte üçünü** doğru olarak işaretleyebilir. Bu, "manuel inceleme listesi otomatik üretme" use case'i için yeterli güçtür.

## 3.4 — Hangi Bilgi Grubu Modele Ne Kadar Katkı Sağlıyor?

[reports/feature_ablation.csv](reports/feature_ablation.csv):

| Özellik Seti | n_feat | MAE | R² | Tam modele oran |
|---|---|---|---|---|
| Full model | 11 | $744 | 0.806 | %100 |
| Clinical only (komorbidite, prosedür, MDC, CareType, urgency) | 5 | $992 | 0.696 | %86 |
| No LOS / no procedure count | 9 | $1,008 | 0.676 | %84 |
| Operational only (LOS, sameday, separation, month) | 4 | $1,650 | 0.370 | %46 |
| Demographics only (Age, Sex) | 2 | $2,212 | -0.10 | %0 |

> 📦 **Net bulgu:** Yaş ve cinsiyet tek başına neredeyse hiç bilgi vermiyor. Klinik bilgi tek başına modelin %86'sını sağlıyor. LOS ve prosedür sayısı çıkarıldığında %84'e düşüyor. Yani bunlar değerli sinyaller, ama vazgeçilemez değiller — gelecekte **admission-time modeli** kurulacaksa, klinik özelliklerden bile fena olmayan bir model kurulabileceğini gösteriyor.

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
> - **%99'un üzerinde temiz veri.** Tutarsızlıklar mevcut ama küçük.
> - **Whitespace missing %100 satırı kapsıyor** — yanıltıcı görünüyor. Açıklama: her epizotta en az bir string alanın boş olduğunu söylüyor; bu kritik alanlarda bilgi eksikliği anlamına gelmez. Anlamlı eksiklik kontrolleri zaten üstteki diğer satırlarda yapılıyor.
> - **Zero total charge (430)** — bu hastane için meşru olabilir (örneğin advance vakalar, iptal edilmiş episodes). Sunumda bu vakalar açıkça belirtildi.

> 🔬 **Bu bulguların önemi:** Sağlık verisi mükemmel değildir; bunu kabul etmek profesyonel duruştur. Soru "veri kötü mü?" değil, "veri kalitesi sorunları modelimi etkiliyor mu?" Cevap: marjinal etkiliyor (etkilenen toplam ≈ %2.3), bu da kabul edilebilir seviyede.

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

Random split test seti, eğitim setiyle aynı dönemden çekilmiş vakalar içerir. Gerçek dünyada model "geçmişle eğitilip gelecek vakaları" tahmin edecek. Bu yüzden ek olarak **time-based split** sonuçlarını da raporladık (R² 0.812 → 0.776). Fark küçük ama var; gerçek dünyada performans yaklaşık bu seviyede beklenmeli.

### 5. Yüksek maliyetli segmentte tam dolar kalibrasyonu zayıf

Top-decile vakaların **var olduğunu** yakalayabiliyoruz (recall %77) ama exact dolar miktarını verme konusunda RMSE yüksek. Pratik anlamı: model "bu pahalı bir vaka" diyebilir, ama "bu vaka tam olarak $25,000 olacak" diyemez.

### 6. SHAP nedensellik göstermez

Model davranışını gösterir. "LOS'u azaltırsak maliyet düşer" gibi nedensel önermeler bu çalışmadan çıkarılamaz; bunlar deneysel veya quasi-experimental analiz gerektirir.

### 7. Klinik kodlama uygulamaları zamanla değişebilir

Bir kurum DRG kodlama pratiğini değiştirirse (örneğin daha fazla komorbidite kodlamaya başlarsa), modelin tahmin desenleri eskir. Periyodik yeniden eğitim gerekir.

### 8. Confidentiality

Worst-prediction CSV, model artifact (`xgb_model.json`) ve patient-level çıktılar **public GitHub'a koyulmaz**. `.gitignore` bunları dışlıyor; ayrıca repository'de sadece aggregate sonuçlar görünüyor.

---

# BÖLÜM 5 — ÖNERİLER (Recommendations)

Bu bölüm **özellikle yönetici paydaşlara** yönelik. Rakamdan çok karara odaklanır.

## 5.1 — Hemen Uygulanabilir 3 Kullanım Alanı

### Öneri 1: Otomatik "Olağandışı Fatura İnceleme Kuyruğu"

**Ne:** Model her hafta tamamlanan epizodlardan, beklenenden belirgin sapan vakaları listeler (örneğin tahminin %50 üstünde gerçekleşen). Funding & Costing ekibi bu listeyi haftalık review queue olarak kullanır.

**İş etkisi:**
- Manuel review zamanında tasarruf
- Kaçırılan fatura hatalarının yakalanması
- Sigorta müzakerelerinde kanıta dayalı argüman ("bu vaka tipinde tipik fatura $X, biz $Y aldık")

**Önkoşul:** Model haftalık veriyle güncellenmeli; basit bir Python script + zamanlanmış görev yeterli.

---

### Öneri 2: MDC-Spesifik "Beklenen Charge Bandı" Raporu

**Ne:** Her MDC için aylık olarak medyan, P25–P75 aralığı, P90 değerleri otomatik üretilir. Kontrat müzakerelerinde referans tablo olarak kullanılır.

**İş etkisi:**
- Sigorta müzakerelerinde tek bir "ortalama" rakam yerine **klinik gruba özgü bantlar**
- "Ne kadar charge ediyoruz?" sorusunun şeffaf cevabı
- İç bütçeleme için MDC-bazlı planlama desteği

**Önkoşul:** Halihazırda `reports/mdc_cost_summary.csv` çıktısı bunun temelini oluşturur; dashboard'a (PowerBI/Tableau) bağlanır.

---

### Öneri 3: Same-day vs Overnight Ayrı Benchmarking

**Ne:** Aynı MDC içinde same-day ve overnight vakalar tamamen farklı maliyet profiline sahip. Performans ölçümünde, kontrat müzakerelerinde, klinik karşılaştırmalarda bu ayrım zorunlu olmalı.

**İş etkisi:**
- "Ortalamaya gömülmüş" gerçek performans farklarının ortaya çıkması
- Daha doğru klinik unit-level benchmarking

**Önkoşul:** Mevcut raporlama altyapısının segment dimension'ına bu ayrımın eklenmesi.

## 5.2 — Orta Vadeli (3–6 ay) Genişleme Önerileri

### Öneri 4: Admission-Time Erken Tahmin Modeli (v2)

**Ne:** Bu çalışmadaki feature ablation gösterdi ki LOS/procedure_count olmadan da model R² ≈ 0.68 veriyor. Admission-time'da bilinen feature'larla (Age, Sex, Urgency, provisional MDC) bir v2 modeli kurulabilir.

**İş etkisi:**
- Yatak/kaynak planlamasında erken uyarı
- Sigorta authorisation süreçlerini hızlandırma
- ICU/theatre kaynak tahsisinde erken bilgi

**Risk:** Performans daha düşük olacak (R² ≈ 0.68 beklentisi). Bu nedenle "tahmin" değil "ön-değerlendirme" olarak konumlandırılmalı.

---

### Öneri 5: Gerçek Maliyet Verisi ile Yeniden Eğitim

**Ne:** Şu anda charge tahmin ediyoruz. Eğer hastanenin gerçek operasyonel maliyet verisi (personel saatleri, malzeme, overhead allocation) eklenirse, model "gerçek cost" hedefi için yeniden eğitilebilir.

**İş etkisi:**
- True profitability per episode/MDC ölçümü
- Loss-making prosedürlerin tanımlanması
- Stratejik portfolio kararları (hangi vakalara genişlemeli, hangileri optimize edilmeli)

**Önkoşul:** Finans ekibiyle veri paylaşımı; veri yönetişimi anlaşması.

---

### Öneri 6: Çoklu Hastane Federasyonu

**Ne:** SJGHC'nin diğer hastanelerinin verisiyle her hastane için ayrı bir kalibre edilmiş model + hastane-üstü bir genel model. Federe/transfer learning yaklaşımı.

**İş etkisi:**
- Grup-genelinde benchmarking
- "Hangi hastane hangi tip vakada görece pahalı?" sorusuna cevap
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

### Öneri 9: Açıklanabilirlik Dashboard'u

Her tahmin için klinik personel veya finans ekibi SHAP açıklamasını görebilmeli: "Bu epizod için tahmin $X çünkü 1) yatış süresi şu, 2) prosedür sayısı şu, 3) MDC şu..." Bu, modeli kara kutu olmaktan çıkarır ve kullanıcı güvenini artırır.

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
| **Data leakage** | Model hedef hakkında doğrudan bilgi içeren bir feature kullanırsa, sahte yüksek performans ortaya çıkar. Bu çalışmada test edildi, sorun yok. |
| **Same-day** | Hastanın aynı gün geldiği ve aynı gün çıktığı epizod (LOS = 0). Tipik örnek: diyaliz, küçük cerrahi. |

---

# EK B — Anahtar Dosya Referansları

| Sunumda Bahsedeceğin Şey | Hangi Dosyada |
|---|---|
| Yönetici özet rakamları | [reports/executive_summary.csv](reports/executive_summary.csv) |
| MDC-bazlı maliyet tablosu | [reports/mdc_cost_summary.csv](reports/mdc_cost_summary.csv) |
| Model karşılaştırma | [reports/model_comparison.csv](reports/model_comparison.csv) |
| Segment performansı | [reports/segment_performance.csv](reports/segment_performance.csv) |
| High-cost yakalama | [reports/high_cost_capture.csv](reports/high_cost_capture.csv) |
| Feature ablation | [reports/feature_ablation.csv](reports/feature_ablation.csv) |
| Veri kalitesi | [reports/data_quality_summary.csv](reports/data_quality_summary.csv) |
| Leakage audit | [reports/leakage_audit.csv](reports/leakage_audit.csv) |
| Feature listesi & availability | [reports/feature_list.csv](reports/feature_list.csv) |
| Final metrikler (JSON) | [reports/final_metrics.json](reports/final_metrics.json) |
| Sınırlamalar | [reports/limitations.md](reports/limitations.md) |
| Hedef tanımı | [reports/target_composition.csv](reports/target_composition.csv) |
| Sunum slayt taslağı | [reports/presentation_outline.md](reports/presentation_outline.md) |

## Sunumda Kullanılacak Anahtar Grafikler

| Grafik | Hangi Slaytta? |
|---|---|
| `figures/01_categorical_distributions.png` | Veri genel bakış |
| `figures/03_charge_distribution.png` | Sağa çarpık dağılım |
| `figures/03_mdc_cost.png` | MDC bazlı maliyet farkları |
| `figures/03_los_vs_cost.png` | LOS = 0 vs LOS > 0 farkı |
| `figures/03_comorbidity_cost.png` | Komorbidite-maliyet ilişkisi |
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

> Random Forest random split'te marjinal olarak daha iyi (R² 0.812 vs 0.807). Ben **XGBoost'u** seçtim çünkü:
> 1) Performans farkı pratik anlamda nötr (~%0.5),
> 2) XGBoost SHAP TreeExplainer ile native uyumlu; açıklanabilirlik için daha temiz çıktı veriyor,
> 3) Time-split'te iki model neredeyse eşit.
> Sonuç olarak her ikisi de viable; bu çalışmada **Random Forest = en iyi held-out performans**, **XGBoost = çok yakın challenger ve SHAP/time-split tercihi**.

### S2: R² 0.80 yeterli mi?

> Sağlık maliyet tahmininde 0.80+ iyi bir performansa karşılık gelir. Ama dikkat: bu **R²** "accuracy %80" değil. Doğru ifade: "Held-out test setindeki charge değişkenliğinin yaklaşık %81'i model tarafından açıklanıyor." Bu, ortalamayı tahmin etmekten çok daha bilgilendirici.

### S3: Veri sızıntısı (leakage) riski yok mu?

> Yok, ve bu otomatik olarak doğrulandı. Hedef değişken 11 charge bileşeninin toplamı. Modelde kullanılan 11 feature'ın **hiçbiri** bu bileşenlerden değil. [reports/leakage_audit.csv](reports/leakage_audit.csv) bunu test ediyor; "overlap = 0".

### S4: Bu model gerçek-zamanlı tahmin için kullanılabilir mi?

> Hayır. LOS, procedure_count, final MDC gibi özellikler epizod tamamlandıktan sonra bilinir. Bu yüzden modelin kullanım alanı **completed episode benchmarking** ve **unusual charge review**. Admission-time tahmin için ayrı bir v2 modeli kurulabilir (öneri 4).

### S5: Veri kalitesini nasıl ele aldınız?

> 9 farklı kontrol otomatik çalıştırıldı: negative LOS, same-day/date mismatch, ICU/theatre tutarsızlığı, zero total charge, whitespace missing, duplicate ID, missing target vb. Sonuçlar [reports/data_quality_summary.csv](reports/data_quality_summary.csv) içinde. En kayda değer bulgu: HCP verisinde eksikler `NaN` değil **whitespace** olarak saklanıyor — bunu yakaladım, naif null kontrolünün eksikleri kaçıracağını gösterdim.

### S6: Etik ve gizlilik?

> Veri zaten de-identified. Buna ek olarak:
> - Raw Excel, processed parquet ve patient-level outputs `.gitignore` ile public repo'dan dışlandı.
> - `reports/worst_predictions.csv` (50 satır row-level review) lokal-only.
> - Model artifact (`xgb_model.json`) lokal-only.
> - Repoda sadece aggregate sonuçlar/grafikler var.

### S7: Modeliniz neden basit bir lineer regresyondan çok iyi?

> Charge dağılımı sağa çarpık ve özellikler arası etkileşim var (örneğin "MDC=I & LOS>5 birlikte yüksek maliyet" gibi). Lineer model bu nonlinear etkileşimleri yakalayamaz. Tree-based modeller (RF, XGBoost) doğası gereği yakalar. Tablo [reports/model_comparison.csv](reports/model_comparison.csv) bu farkı rakamla gösteriyor.

### S8: Tek hastanedeki sonuçlar genelleştirilebilir mi?

> Doğrudan hayır. Bu hastanenin (HospitalType=2, özel akut bakım, gözlenen 14 ay) profili genelleme için yeterli değil. Başka SJGHC hastanelerine taşımadan önce o hastanelerin verisiyle yeniden doğrulanmalı. Bunu sınırlamalar bölümünde açıkça yazdım.

### S9: SHAP ile "X özelliğini değiştirsek maliyet düşer mi?" sorabilir miyim?

> Hayır. SHAP **modelin nasıl davrandığını** gösterir, dünyanın nedensel yapısını değil. Yatış süresi-maliyet ilişkisi SHAP'ta güçlü görünüyor, ama bu "yatış süresini kısaltırsak maliyet düşer" demek değildir; "model maliyet tahmininde yatış süresine büyük ağırlık veriyor" demektir. Nedensel iddialar için deneysel veya quasi-experimental analiz gerekir.

### S10: Bu projeyi production'a almak için ne gerekir?

> Üç katman:
> 1. **Veri katmanı:** Aylık HCP submission akışına model girdi pipeline'ı bağlanmalı.
> 2. **Model katmanı:** Eğitim/inference ortamı (basit MLflow + scheduler yeter).
> 3. **Tüketim katmanı:** Funding & Costing ekibi için dashboard (PowerBI ile entegre).
> Tahmini efor: 4–6 hafta, bir veri mühendisi + bir analist desteğiyle.

---

# Kapanış Notu

Bu çalışma "tek seferlik bir analiz" değil, **tekrarlanabilir bir analitik temeldir**. Tek komutla baştan sona yeniden üretilir ([scripts/generate_validation_outputs.py](scripts/generate_validation_outputs.py)); bütün metrikler dokümantedir; bütün kararlar yazılı gerekçeyle sunulur.

Sunumda hedeflediğim mesaj üçtür:

1. **Veriyi anlıyorum.** HCP'nin tuhaflıkları, kodlama desenleri, eksik kalıpları farkındayım.
2. **Modeli savunabiliyorum.** Tek bir rakamı değil, alternatifleriyle birlikte tüm yöntem zincirini biliyorum.
3. **İşi konuşabiliyorum.** Funding & Costing ekibinin günlük diline tercüme edilmemiş hiçbir teknik ayrıntı bırakmıyorum.

Bu üçü panel karşısında doğru aktarılırsa, projenin teknik değerinden bağımsız olarak, **rol için doğru kişi olduğum** ortaya çıkar — ki sunumun gerçek amacı budur.
