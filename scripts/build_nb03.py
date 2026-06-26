#!/usr/bin/env python3
"""
Build 03_eda.ipynb — Keşifsel Veri Analizi + 7 Sunum Grafiği

Grafik listesi:
  3.1  Charge dağılımı — histogram (ham + log) → sağa çarpıklık hikayesi
  3.2  MDC bazında medyan charge — kategori benchmarkları
  3.3  Yaş grubu vs ortalama charge — demografik profil
  3.4  LOS vs charge — yatış süresi-charge ilişkisi
  3.5  Komorbidite sayısı vs medyan charge — karmaşıklık ilişkisi
  3.6  Günübirlik vs yatışlı charge kutusu — portföy karşılaştırması
  3.7  Aylık hacim + ortalama charge trendi
"""
import nbformat as nbf
from pathlib import Path

ROOT = Path(__file__).parent.parent
NB   = ROOT / "notebooks" / "03_eda.ipynb"

nb    = nbf.v4.new_notebook()
cells = []

def md(text):  return nbf.v4.new_markdown_cell(text)
def code(src): return nbf.v4.new_code_cell(src)


# ──────────────────────────────────────────────────────────
# BAŞLIK
# ──────────────────────────────────────────────────────────
cells.append(md(
"""# Notebook 3 — Keşifsel Veri Analizi (EDA)

## Bu notebook ne yapıyor?

NB2'de verimizi temizledik ve yeni özellikler türettik.  
Şimdi **"veri bize ne anlatıyor?"** sorusunu grafiklere döküyoruz.

Bu notebook 7 grafik üretiyor. Her biri:
1. **Bir soruyu cevaplar** (ör. "Yaş grupları arasında billed charge farkı var mı?")
2. **Sunumda kullanılacak** — `figures/` klasörüne yüksek kaliteli PNG olarak kaydedilir
3. **Mülakat sorusuna hazırlık** sağlar (ör. "Veriyi nasıl anladınız?")

**Hedef kitle:** SJGHC Funding & Costing ekibi  
**Amaç:** Episode-level billed charge yapısını ve tahmin modelinin motivasyonunu görsel olarak açıklamak
"""
))


# ──────────────────────────────────────────────────────────
# 3.0 SETUP
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## 3.0 — Kurulum ve Stil Ayarları

Tüm grafiklerde **tutarlı bir renk paleti ve yazı boyutu** kullanacağız.  
Bu, profesyonel görünüm için kritik — PowerPoint'e taşındığında da temiz duracak.
"""
))

cells.append(code(
"""import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ─── Dizinler ───
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
FIGS = ROOT / "figures"
FIGS.mkdir(exist_ok=True)

# ─── Veri ───
df = pd.read_parquet(ROOT / "data/processed/hcp_clean.parquet")
print(f"Veri yüklendi: {df.shape[0]:,} satır × {df.shape[1]} sütun")

# ─── Grafik stili ───
PALETTE_MAIN  = "#1a5276"    # koyu mavi (birincil)
PALETTE_ACC   = "#e74c3c"    # kırmızı (vurgu)
PALETTE_LIGHT = "#aed6f1"    # açık mavi (arka plan / grid)
PALETTE_SEQ   = "Blues_r"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "#f8f9fa",
    "axes.grid":        True,
    "grid.color":       "white",
    "grid.linewidth":   1.0,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "font.size":        12,
    "axes.titlesize":   15,
    "axes.labelsize":   12,
    "xtick.labelsize":  11,
    "ytick.labelsize":  11,
    "legend.fontsize":  11,
})

# ─── Yardımcı ─────────────────────────────────────
def save(name: str, fig=None):
    \"\"\"Grafiği figures/ klasörüne kaydet ve kapat.\"\"\"
    path = FIGS / name
    (fig or plt).savefig(path, dpi=150, bbox_inches="tight",
                         facecolor="white")
    plt.close("all")
    print(f"  ✓ Kaydedildi: {path.name}")

print("Stil ayarları uygulandı.")
"""
))


# ──────────────────────────────────────────────────────────
# 3.1 MALİYET DAĞILIMI
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 1 — Charge Dağılımı: Ham ve Log Ölçek

**Soru:** Toplam fatura nasıl dağılıyor?

**Ham dağılım:** Büyük çoğunluk düşük billed charge seviyesinde, ama bazı epizodlar $50,000+ charge değerine sahip.  
Buna "**sağa çarpık dağılım**" deniyor (çan eğrisi sola dayanıyor, kuyruğu sağa uzuyor).

**Log ölçek ne işe yarıyor?**  
`log($650) ≈ 6.5`, `log($50,000) ≈ 10.8` — artık iki değer görsel olarak yakın.  
Bu, modelin eğitiminde de uygulanacak: XGBoost `log(total_charge_aud)` tahmin edecek,  
sonra `exp()` ile gerçek AUD değerine dönüştüreceğiz.
"""
))

cells.append(code(
"""fig, axes = plt.subplots(1, 2, figsize=(14, 5))

tc = df["total_charge_aud"].clip(upper=df["total_charge_aud"].quantile(0.99))

# Sol: Ham dağılım
axes[0].hist(tc, bins=80, color=PALETTE_MAIN, edgecolor="white", linewidth=0.4)
axes[0].set_title("Ham Charge Dağılımı\\n(sağa çarpık)", fontweight="bold")
axes[0].set_xlabel("Toplam Fatura ($AUD)")
axes[0].set_ylabel("Epizod Sayısı")
axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"${x:,.0f}"))
med = df["total_charge_aud"].median()
axes[0].axvline(med, color=PALETTE_ACC, lw=2, linestyle="--",
                label=f"Medyan: ${med:,.0f}")
axes[0].legend()

# Sağ: Log ölçek
log_tc = np.log1p(df["total_charge_aud"].clip(lower=0))
axes[1].hist(log_tc, bins=60, color="#2980b9", edgecolor="white", linewidth=0.4)
axes[1].set_title("Log Ölçek Charge Dağılımı\\n(daha dengeli)", fontweight="bold")
axes[1].set_xlabel("log(1 + Toplam Fatura)")
axes[1].set_ylabel("Epizod Sayısı")
log_med = np.log1p(df["total_charge_aud"].median())
axes[1].axvline(log_med, color=PALETTE_ACC, lw=2, linestyle="--",
                label=f"Medyan: {log_med:.2f}")
axes[1].legend()

fig.suptitle("Toplam Fatura Dağılımı — $AUD (n=30,615)",
             fontsize=16, fontweight="bold", y=1.01)
plt.tight_layout()
save("03_charge_distribution.png")
print(f"  Orijinal: {df['total_charge_aud'].skew():.2f} çarpıklık")
print(f"  Log sonrası: {log_tc.skew():.2f} çarpıklık (0'a yakın = daha normal)")
"""
))


# ──────────────────────────────────────────────────────────
# 3.2 MDC MALİYET
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 2 — MDC Bazında Medyan Charge

**Soru:** Hangi hastalık kategorisinde tipik billed charge daha yüksek?

Medyan kullanıyoruz çünkü "ortalama" aykırı değerlerden etkileniyor.  
Medyan: "Tam ortadaki hastanın faturası ne kadar?" → daha güvenilir.

Bu grafik sunumda şu soruyu doğurur:  
**"Bu kategori farkları hangi case-mix, same-day oranı, LOS ve prosedür profilleriyle ilişkili?"**  
DRG-level analiz olmadan nedensel açıklama yapmıyoruz.
"""
))

cells.append(code(
"""# MDC'ler için kısaltılmış etiket (grafik için)
MDC_SHORT = {
    "A": "Pre-MDC (Nakil)",
    "B": "Sinir Sistemi",
    "C": "Göz",
    "D": "KBB & Ağız",
    "E": "Solunum",
    "F": "Dolaşım",
    "G": "Sindirim",
    "H": "Karaciğer/Safra",
    "I": "Kas-İskelet",
    "J": "Deri",
    "K": "Endokrin",
    "L": "Böbrek/Üriner",
    "M": "Erkek Üreme",
    "N": "Kadın Üreme",
    "O": "Gebelik/Doğum",
    "P": "Yenidoğan",
    "Q": "Kan",
    "R": "Ruhsal Hast.",
    "S": "Madde Kullanımı",
    "T": "Enfeksiyon",
    "U": "Yanık",
    "V": "Sağlık Faktörleri",
    "W": "Yaralanma",
    "X": "Diğer",
    "Y": "HIV",
    "Z": "Gruplandırılamayan",
}

mdc_stats = (df.groupby("MDC")["total_charge_aud"]
               .agg(median="median", count="count", mean="mean")
               .reset_index()
               .query("count >= 50")   # en az 50 epizod → güvenilir medyan
               .sort_values("median", ascending=True))

mdc_stats["label"] = mdc_stats["MDC"].map(MDC_SHORT).fillna(mdc_stats["MDC"])

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(mdc_stats["label"], mdc_stats["median"],
               color=PALETTE_MAIN, edgecolor="white", linewidth=0.5)
# Değer etiketleri
for bar, val in zip(bars, mdc_stats["median"]):
    ax.text(val + 50, bar.get_y() + bar.get_height()/2,
            f"${val:,.0f}", va="center", ha="left", fontsize=9.5, color="#2c3e50")

ax.set_xlabel("Medyan Toplam Fatura ($AUD)", fontsize=12)
ax.set_title("MDC Kategorisine Göre Medyan Episode Charge\\n"
             "(en az 50 epizod olan kategoriler gösterildi)",
             fontweight="bold", fontsize=14)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
plt.tight_layout()
save("03_mdc_cost.png")
print(f"  En pahalı MDC: {mdc_stats.iloc[-1]['MDC']} = ${mdc_stats.iloc[-1]['median']:,.0f}")
print(f"  En ucuz MDC  : {mdc_stats.iloc[0]['MDC']} = ${mdc_stats.iloc[0]['median']:,.0f}")
"""
))


# ──────────────────────────────────────────────────────────
# 3.3 YAŞ GRUBU MALİYET
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 3 — Yaş Grubu vs Ortalama Charge

**Soru:** Yaş grupları arasında billed charge farkı var mı?

Bu grafik yalnızca gözlenen ilişkiyi gösterir. Yaş farkları; komorbidite,
prosedür yoğunluğu, LOS ve case-mix ile karışabilir.

Ama dikkat: Bu veri **Avustralya özel hastane** verisi.  
Özel sigortalı yaşlı hastalar seçici tedavi alıyor — bu bazı sürprizler yaratabilir.
"""
))

cells.append(code(
"""# Yaş grupları tanımla
bins   = [-1, 0, 17, 44, 64, 79, 120]
labels = ["0 (Yenidoğan)", "1–17", "18–44", "45–64", "65–79", "80+"]
df["age_group"] = pd.cut(df["Age"], bins=bins, labels=labels)

age_stats = (df.groupby("age_group", observed=True)["total_charge_aud"]
               .agg(mean="mean", median="median", count="count")
               .reset_index())

fig, ax = plt.subplots(figsize=(11, 5))
colors = [PALETTE_LIGHT if m < df["total_charge_aud"].mean() else PALETTE_MAIN
          for m in age_stats["mean"]]
bars = ax.bar(age_stats["age_group"].astype(str), age_stats["mean"],
              color=colors, edgecolor="white", linewidth=0.5)

# Sayı etiketi
for bar, row in zip(bars, age_stats.itertuples()):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 30,
            f"${row.mean:,.0f}\\n(n={row.count:,})",
            ha="center", va="bottom", fontsize=9)

# Genel ortalama çizgisi
overall_mean = df["total_charge_aud"].mean()
ax.axhline(overall_mean, color=PALETTE_ACC, linestyle="--", lw=2,
           label=f"Genel Ortalama: ${overall_mean:,.0f}")

ax.set_xlabel("Yaş Grubu", fontsize=12)
ax.set_ylabel("Ortalama Toplam Fatura ($AUD)", fontsize=12)
ax.set_title("Yaş Grubuna Göre Ortalama Episode Charge",
             fontweight="bold", fontsize=14)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend()
plt.tight_layout()
save("03_age_cost.png")
"""
))


# ──────────────────────────────────────────────────────────
# 3.4 LOS vs MALİYET
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 4 — Yatış Süresi (LOS) vs Charge

**Soru:** LOS arttıkça billed charge nasıl değişiyor?

Gözlenen ilişkide LOS yükseldikçe medyan charge da yükseliyor, ancak bu
nedensel ve doğrusal bir iddia değildir. LOS aynı zamanda case-mix ve episode
karmaşıklığını da yansıtır.

**Bu grafiğin sunumdaki önemi:**  
LOS epizod tamamlandıktan sonra bilindiği için bu modeli admission-time model
olarak konumlandırmıyoruz.
"""
))

cells.append(code(
"""# LOS > 0 ve 99. persantil altındaki veriyi göster
mask = (df["LOS"] >= 0) & (df["LOS"] <= df["LOS"].quantile(0.99))
sub  = df[mask].copy()

# LOS için kutu grupları
los_groups = sub.groupby("LOS")["total_charge_aud"].agg(
    median="median", mean="mean", count="count"
).reset_index().query("count >= 10")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(los_groups["LOS"], los_groups["median"],
        color=PALETTE_MAIN, linewidth=2.5, marker="o",
        markersize=5, label="Medyan Charge")
ax.fill_between(los_groups["LOS"],
                los_groups["median"] * 0.7,
                los_groups["median"] * 1.3,
                alpha=0.15, color=PALETTE_MAIN)

ax.set_xlabel("Yatış Süresi — LOS (Gün)", fontsize=12)
ax.set_ylabel("Medyan Toplam Fatura / Charge ($AUD)", fontsize=12)
ax.set_title("Yatış Süresine (LOS) Göre Medyan Charge\\n"
             "(LOS=0: günübirlik hastalar)",
             fontweight="bold", fontsize=14)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.xaxis.set_major_locator(mticker.MultipleLocator(2))

# LOS=0 etiket
los0 = los_groups.loc[los_groups["LOS"] == 0, "median"].values
if len(los0):
    ax.annotate(f"LOS=0\\n(Günübirlik)\\n${los0[0]:,.0f}",
                xy=(0, los0[0]), xytext=(3, los0[0] + 1500),
                arrowprops=dict(arrowstyle="->", color=PALETTE_ACC),
                fontsize=9, color=PALETTE_ACC)

ax.legend()
plt.tight_layout()
save("03_los_vs_cost.png")
"""
))


# ──────────────────────────────────────────────────────────
# 3.5 KOMORBİDİTE ETKİSİ
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 5 — Komorbidite Sayısı vs Medyan Charge

**Soru:** Kaydedilmiş ek tanı sayısı arttıkça medyan charge nasıl değişiyor?

Bu grafik, `comorbidity_count` özelliğinin tahmin sinyali taşıyıp taşımadığını gösterir.  
Higher recorded comorbidity counts were associated with progressively higher median charges.

Bu bir ilişki bulgusudur; coding practice ve case-mix etkileri nedeniyle nedensel yorum yapılmaz.
"""
))

cells.append(code(
"""# 7+ komorbiditeyi grupla (az veri var)
df["comorbidity_grp"] = df["comorbidity_count"].clip(upper=7)
df.loc[df["comorbidity_count"] >= 7, "comorbidity_grp"] = 7  # "7+" grubu

comorb_stats = (df.groupby("comorbidity_grp")["total_charge_aud"]
                  .agg(median="median", mean="mean", count="count",
                       q25=lambda x: x.quantile(0.25),
                       q75=lambda x: x.quantile(0.75))
                  .reset_index())

fig, ax = plt.subplots(figsize=(11, 5))

# Çubuk (medyan)
bars = ax.bar(comorb_stats["comorbidity_grp"], comorb_stats["median"],
              color=PALETTE_MAIN, alpha=0.8, edgecolor="white",
              label="Medyan Charge")
# IQR (q25–q75) error bars
ax.errorbar(comorb_stats["comorbidity_grp"], comorb_stats["median"],
            yerr=[comorb_stats["median"] - comorb_stats["q25"],
                  comorb_stats["q75"]   - comorb_stats["median"]],
            fmt="none", color="#2c3e50", capsize=5, linewidth=1.5)

# Sayılar
for bar, row in zip(bars, comorb_stats.itertuples()):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + 60,
            f"n={row.count:,}", ha="center", va="bottom", fontsize=8.5)

x_labels = [str(int(x)) if x < 7 else "7+" for x in comorb_stats["comorbidity_grp"]]
ax.set_xticks(comorb_stats["comorbidity_grp"])
ax.set_xticklabels(x_labels)
ax.set_xlabel("Ek Tanı (Komorbidite) Sayısı", fontsize=12)
ax.set_ylabel("Medyan Toplam Fatura / Charge ($AUD)", fontsize=12)
ax.set_title("Komorbidite Sayısına Göre Medyan Charge\\n"
             "(hata çubukları: çeyrekler arası aralık)",
             fontweight="bold", fontsize=14)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend()
plt.tight_layout()
save("03_comorbidity_cost.png")
"""
))


# ──────────────────────────────────────────────────────────
# 3.6 GÜNÜBİRLİK VS YATIŞLI
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 6 — Günübirlik vs Yatışlı Hasta: Charge Karşılaştırması

**Soru:** Günübirlik ve yatışlı epizodların charge profilleri ne kadar farklı?

**LOS=0 (günübirlik):** yüksek hacimli ayrı bir segment  
**LOS>0 (yatışlı):** farklı charge dağılımı ve case-mix profili

Same-day status produced one of the clearest univariate charge differences in EDA.
"""
))

cells.append(code(
"""df["stay_type"] = df["LOS"].apply(
    lambda x: "Günübirlik (LOS=0)" if x == 0 else "Yatışlı (LOS≥1)"
)

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Sol: Violin plot
parts = axes[0].violinplot(
    [df.loc[df["stay_type"]=="Günübirlik (LOS=0)","total_charge_aud"].clip(upper=15000),
     df.loc[df["stay_type"]=="Yatışlı (LOS≥1)","total_charge_aud"].clip(upper=30000)],
    positions=[0, 1], widths=0.6, showmedians=True, showextrema=False
)
for pc in parts["bodies"]:
    pc.set_facecolor(PALETTE_MAIN); pc.set_alpha(0.7)
parts["cmedians"].set_color(PALETTE_ACC); parts["cmedians"].set_linewidth(2.5)

axes[0].set_xticks([0, 1])
axes[0].set_xticklabels(["Günübirlik\\n(LOS=0)", "Yatışlı\\n(LOS≥1)"])
axes[0].set_ylabel("Toplam Fatura ($AUD)")
axes[0].set_title("Charge Dağılımı\\n(99. persantil kırpıldı)", fontweight="bold")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

# Sağ: Özet tablo
stats = df.groupby("stay_type")["total_charge_aud"].agg(
    ["count","median","mean"]).reset_index()
stats.columns = ["Tür","Sayı","Medyan","Ortalama"]
stats["Pay (%)"] = (stats["Sayı"] / stats["Sayı"].sum() * 100).round(1)

axes[1].axis("off")
tbl_data = [[row["Tür"], f"{row['Sayı']:,}", f"${row['Medyan']:,.0f}",
             f"${row['Ortalama']:,.0f}", f"{row['Pay (%)']:.1f}%"]
            for _, row in stats.iterrows()]
tbl = axes[1].table(
    cellText=tbl_data,
    colLabels=["Tür","Sayı","Medyan","Ortalama","Pay"],
    cellLoc="center", loc="center",
    bbox=[0.0, 0.3, 1.0, 0.45]
)
tbl.auto_set_font_size(False); tbl.set_fontsize(11)
for (r, c), cell in tbl.get_celld().items():
    if r == 0:
        cell.set_facecolor(PALETTE_MAIN); cell.set_text_props(color="white", fontweight="bold")
    else:
        cell.set_facecolor("#ecf0f1" if r % 2 else "white")
axes[1].set_title("Özet İstatistikler", fontweight="bold", fontsize=13)

fig.suptitle("Günübirlik vs Yatışlı Hasta Charge Karşılaştırması",
             fontsize=15, fontweight="bold", y=1.01)
plt.tight_layout()
save("03_sameday_vs_overnight.png")
"""
))


# ──────────────────────────────────────────────────────────
# 3.7 AYLIK TREND
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Grafik 7 — Aylık Hacim ve Charge Trendi

**Soru:** Gözlenen dönemde aylık hacim ve ortalama charge nasıl değişiyor?

Tek veri kesitinde "seasonality" iddiası kurmuyoruz. Doğru ifade:
**Monthly activity varied across the observed period.**

Bu grafik, gözlenen dönem içindeki aylık değişimi görselleştirir.
"""
))

cells.append(code(
"""df["adm_month"] = df["AdmissionDate_dt"].dt.to_period("M")
monthly = (df.groupby("adm_month")
             .agg(count=("total_charge_aud","count"),
                  mean_charge=("total_charge_aud","mean"))
             .reset_index())
monthly["adm_month_dt"] = monthly["adm_month"].dt.to_timestamp()

fig, ax1 = plt.subplots(figsize=(14, 5))

# Birincil eksen: hacim
color1 = PALETTE_MAIN
ax1.bar(range(len(monthly)), monthly["count"],
        color=color1, alpha=0.7, width=0.6, label="Epizod Sayısı")
ax1.set_xlabel("Ay", fontsize=12)
ax1.set_ylabel("Epizod Sayısı", color=color1, fontsize=12)
ax1.tick_params(axis="y", labelcolor=color1)
ax1.set_xticks(range(len(monthly)))
ax1.set_xticklabels(
    [m.strftime("%b %y") for m in monthly["adm_month_dt"]],
    rotation=45, ha="right", fontsize=9
)

# İkincil eksen: ortalama charge
ax2 = ax1.twinx()
ax2.plot(range(len(monthly)), monthly["mean_charge"],
         color=PALETTE_ACC, linewidth=2.5, marker="o",
         markersize=6, label="Ort. Charge ($AUD)")
ax2.set_ylabel("Ortalama Charge ($AUD)", color=PALETTE_ACC, fontsize=12)
ax2.tick_params(axis="y", labelcolor=PALETTE_ACC)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

# Efsane birleştir
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

ax1.set_title("Aylık Başvuru Hacmi ve Ortalama Charge Değişimi",
              fontweight="bold", fontsize=14)
plt.tight_layout()
save("03_monthly_trend.png")
"""
))


# ──────────────────────────────────────────────────────────
# ÖZET
# ──────────────────────────────────────────────────────────
cells.append(md(
"""---
## Özet: EDA'dan Çıkan 7 Ana Bulgu

Tüm grafikleri tamamladık. İşte sunumda kullanılacak kilit bulgular:
"""
))

cells.append(code(
"""figs = sorted(FIGS.glob("03_*.png"))
print(f"✓ Üretilen sunum grafikleri ({len(figs)} adet):")
for f in figs:
    size_kb = f.stat().st_size / 1024
    print(f"  {f.name:<40}  {size_kb:>6.1f} KB")

print("\\n" + "=" * 60)
print("EDA BULGULARI ÖZETİ — SUNUMDA KULLANILACAK")
print("=" * 60)

findings = [
    ("1. Charge çarpık",
     f"Medyan ${df['total_charge_aud'].median():,.0f} "
     f"ama Ort. ${df['total_charge_aud'].mean():,.0f} — "
     f"→ Model log(charge) tahmin edecek"),
    ("2. MDC etkisi",
     "Kategoriler arası 10+ kat fark — "
     "MDC modelimizin kritik özelliği"),
    ("3. Yaş etkisi",
     f"65+ yaş: ${df.loc[df['Age']>=65,'total_charge_aud'].mean():,.0f} ort. "
     f"vs 18-44: ${df.loc[(df['Age']>=18)&(df['Age']<=44),'total_charge_aud'].mean():,.0f}"),
    ("4. LOS etkisi",
     f"LOS=0 medyan ${df.loc[df['LOS']==0,'total_charge_aud'].median():,.0f} "
     f"vs LOS>0 medyan ${df.loc[df['LOS']>0,'total_charge_aud'].median():,.0f}"),
    ("5. Komorbidite",
     "Higher recorded comorbidity counts were associated with higher median charges"),
    ("6. Günübirlik ağırlık",
     f"%{(df['LOS']==0).mean()*100:.1f} günübirlik → "
     "yatışlı hasta segmenti ayrı modellenmeli"),
    ("7. Aylık değişim",
     "Monthly activity varied across the observed period"),
]
for title, desc in findings:
    print(f"  {title:<22}: {desc}")
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
