"""
Sinh báo cáo khoa học PDF tự động từ dữ liệu giá nhà.
Chạy:  py src/bao_cao.py           -> reports/bao_cao_khoa_hoc.pdf (+ reports/figures/*.png)
Trong code: build_report(df_raw, out)  với out là đường dẫn hoặc io.BytesIO (dùng cho dashboard)
"""
import io
import os
import sys
import tempfile
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phan_tich as pt  # noqa: E402

# ---------- Thông tin đề tài (sửa theo nhóm) ----------
TEN_DE_TAI = "PHÂN TÍCH CÁC YẾU TỐ ẢNH HƯỞNG VÀ DỰ ĐOÁN GIÁ NHÀ Ở BANG WASHINGTON (HOA KỲ)"
TEN_NHOM = "Nhóm 11"
NHOM = [("M2526019", "Trương Thị Thanh Loan"),
        ("M2526029", "Bùi Gia Bảo"),
        ("M2526020", "Nguyễn Văn Tấn Lộc")]
LOP = "Công nghệ số nâng cao"
NGUON = "Kaggle – House Price Prediction (shree1992/housedata), giao dịch 02/05–10/07/2014"

REPORT_DIR = os.path.join(pt.ROOT, "reports")
FIG_DIR = os.path.join(REPORT_DIR, "figures")

# ---------- Font ----------
_FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/msttcorefonts",
              "/usr/share/fonts/truetype/dejavu"]


def _register_fonts():
    for d in _FONT_DIRS:
        for reg, bold, ital in [("arial.ttf", "arialbd.ttf", "ariali.ttf"),
                                ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf")]:
            if os.path.exists(os.path.join(d, reg)):
                pdfmetrics.registerFont(TTFont("VN", os.path.join(d, reg)))
                pdfmetrics.registerFont(TTFont("VN-B", os.path.join(d, bold)))
                pdfmetrics.registerFont(TTFont("VN-I", os.path.join(d, ital)))
                pdfmetrics.registerFontFamily("VN", normal="VN", bold="VN-B", italic="VN-I")
                return "Arial" if reg == "arial.ttf" else "DejaVu Sans"
    raise RuntimeError("Không tìm thấy font Unicode (Arial/DejaVu) để hiển thị tiếng Việt")


MPL_FONT = _register_fonts()
sns.set_theme(style="whitegrid", font=MPL_FONT)
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
BLUE, ORANGE = "#2E5EAA", "#E07A1F"


# ---------- Biểu đồ ----------
def _save(fig, folder, name):
    p = os.path.join(folder, name)
    fig.tight_layout()
    fig.savefig(p, dpi=180)
    plt.close(fig)
    return p


def make_figures(df, res, folder):
    os.makedirs(folder, exist_ok=True)
    f = {}

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    sns.histplot(df["price"] / 1000, bins=50, color=BLUE, ax=ax[0])
    ax[0].set(xlabel="Giá bán (nghìn USD)", ylabel="Số nhà", title="Phân phối giá bán")
    sns.histplot(df["log_price"], bins=50, color=ORANGE, kde=True, ax=ax[1])
    ax[1].set(xlabel="log(Giá bán)", ylabel="Số nhà", title="Phân phối log(giá) – gần chuẩn")
    f["hist"] = _save(fig, folder, "01_phan_phoi_gia.png")

    cols = ["price", "sqft_living", "bathrooms", "bedrooms", "view", "floors", "sqft_basement",
            "condition", "house_age", "sqft_lot"]
    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(8, 6.4))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1,
                xticklabels=[pt.VAR_LABELS[c] for c in cols],
                yticklabels=[pt.VAR_LABELS[c] for c in cols], annot_kws={"size": 8}, ax=ax)
    ax.set_title("Ma trận tương quan Pearson")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right", fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)
    f["corr"] = _save(fig, folder, "02_tuong_quan.png")

    fig, ax = plt.subplots(figsize=(9, 4.4))
    sns.scatterplot(data=df, x="sqft_living", y=df["price"] / 1000, hue="condition",
                    palette="viridis", s=12, alpha=0.6, ax=ax, edgecolor=None)
    sns.regplot(data=df, x="sqft_living", y=df["price"] / 1000, scatter=False, color="red",
                ax=ax, line_kws={"lw": 1.5})
    ax.set(xlabel="Diện tích ở (sqft)", ylabel="Giá bán (nghìn USD)",
           title="Giá bán theo diện tích ở (màu: tình trạng nhà)")
    ax.legend(title="Tình trạng", fontsize=8)
    f["scatter"] = _save(fig, folder, "03_gia_theo_dien_tich.png")

    top = df["city"].value_counts().head(10).index
    sub = df[df.city.isin(top)]
    order = sub.groupby("city")["price"].median().sort_values(ascending=False).index
    fig, ax = plt.subplots(figsize=(9, 4.4))
    sns.boxplot(data=sub, x="city", y=sub["price"] / 1000, order=order, color="#9DB7E0",
                fliersize=2, ax=ax)
    ax.set(xlabel="", ylabel="Giá bán (nghìn USD)", title="Giá bán theo 10 thành phố nhiều giao dịch nhất")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    f["city"] = _save(fig, folder, "04_gia_theo_thanh_pho.png")

    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    sns.barplot(data=df, x="condition", y=df["price"] / 1000, estimator=np.median, color=BLUE,
                errorbar=None, ax=ax[0])
    ax[0].set(xlabel="Tình trạng nhà (1–5)", ylabel="Giá trung vị (nghìn USD)", title="Theo tình trạng")
    sns.barplot(data=df, x="view", y=df["price"] / 1000, estimator=np.median, color=ORANGE,
                errorbar=None, ax=ax[1])
    ax[1].set(xlabel="Điểm view (0–4)", ylabel="Giá trung vị (nghìn USD)", title="Theo điểm view")
    f["cat"] = _save(fig, folder, "05_gia_theo_tinh_trang_view.png")

    imp = res["importance"].sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(imp.index, imp.values, color=BLUE)
    for i, v in enumerate(imp.values):
        ax.text(v + 0.004, i, f"{v:.1%}", va="center", fontsize=8)
    ax.set(xlabel="Mức độ quan trọng", title="Độ quan trọng đặc trưng (Random Forest)")
    f["imp"] = _save(fig, folder, "06_do_quan_trong.png")

    best = res["metrics"]["R² (log giá)"].idxmax()
    pr = res["preds"][best] / 1000
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(pr["Thực tế"], pr["Dự đoán"], s=10, alpha=0.5, color=BLUE)
    m = max(pr.max())
    ax.plot([0, m], [0, m], "r--", lw=1)
    ax.set(xlabel="Giá thực tế (nghìn USD)", ylabel="Giá dự đoán (nghìn USD)",
           title=f"Thực tế vs dự đoán – {best} (tập kiểm tra)")
    f["pred"] = _save(fig, folder, "07_thuc_te_vs_du_doan.png")
    return f


# ---------- PDF helpers ----------
P = ParagraphStyle("p", fontName="VN", fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=6)
H1 = ParagraphStyle("h1", fontName="VN-B", fontSize=14, leading=18, spaceBefore=10, spaceAfter=6,
                    textColor=colors.HexColor("#1F3F75"))
H2 = ParagraphStyle("h2", fontName="VN-B", fontSize=11.5, leading=15, spaceBefore=6, spaceAfter=4,
                    textColor=colors.HexColor("#2E5EAA"))
CAP = ParagraphStyle("cap", fontName="VN-I", fontSize=9, alignment=TA_CENTER,
                     textColor=colors.HexColor("#555555"), spaceAfter=10)
BUL = ParagraphStyle("b", parent=P, leftIndent=14, bulletIndent=4)
W = A4[0] - 4 * cm


def table(frame, widths=None, fmt="{:,.2f}", index=True, size=8.5):
    head = ([frame.index.name or ""] if index else []) + [str(c) for c in frame.columns]
    rows = [head]
    for idx, r in frame.iterrows():
        cells = [str(idx)] if index else []
        for v in r.values:
            if isinstance(v, (float, np.floating)):
                cells.append(fmt.format(v))
            elif isinstance(v, (int, np.integer)):
                cells.append(f"{v:,}")
            else:
                cells.append(str(v))
        rows.append(cells)
    cs = ParagraphStyle("c", fontName="VN", fontSize=size, leading=size + 2)
    hs = ParagraphStyle("h", parent=cs, fontName="VN-B", textColor=colors.white)
    data = [[Paragraph(c, hs if i == 0 else cs) for c in row] for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5EAA")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3FA")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C4D6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("VN", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, "Báo cáo khoa học – Phân tích & dự đoán giá nhà")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Trang {doc.page}")
    canvas.restoreState()


def _usd(x):
    return f"{x:,.0f} USD"


# ---------- Dựng báo cáo ----------
def build_report(raw, out, filter_note=None, fig_dir=None):
    """raw: DataFrame gốc (có thể đã lọc). out: đường dẫn file hoặc BytesIO."""
    df, clean_log = pt.clean(raw)
    if len(df) < 50:
        raise ValueError("Cần ít nhất 50 dòng dữ liệu sạch để phân tích và huấn luyện mô hình")
    res = pt.train_models(df)
    tests = pt.stat_tests(df)
    tmp = None
    if fig_dir is None:
        tmp = tempfile.TemporaryDirectory()
        fig_dir = tmp.name
    figs = make_figures(df, res, fig_dir)

    story, fig_no = [], [0]

    def figure(key, caption, width=W * 0.9):
        fig_no[0] += 1
        iw, ih = ImageReader(figs[key]).getSize()
        story.append(KeepTogether([Image(figs[key], width=width, height=width * ih / iw),
                                   Paragraph(f"Hình {fig_no[0]}. {caption}", CAP)]))

    # Trang bìa ngắn
    story += [
        Spacer(1, 30),
        Paragraph("BÁO CÁO KHOA HỌC", ParagraphStyle("k", fontName="VN-B", fontSize=13,
                  alignment=TA_CENTER, textColor=colors.HexColor("#E07A1F"))),
        Spacer(1, 8),
        Paragraph(TEN_DE_TAI, ParagraphStyle("t", fontName="VN-B", fontSize=18, leading=24,
                  alignment=TA_CENTER, textColor=colors.HexColor("#1F3F75"))),
        Spacer(1, 14),
    ]
    info = ParagraphStyle("i", fontName="VN", fontSize=11, leading=16, alignment=TA_CENTER)
    story.append(Paragraph(f"<b>Nhóm thực hiện: {TEN_NHOM}</b> – Lớp: {LOP}", info))
    story.append(Spacer(1, 4))
    mem = pd.DataFrame(NHOM, columns=["MSSV", "Họ và tên"])
    mem.insert(0, "STT", [str(i) for i in range(1, len(mem) + 1)])
    mt_ = table(mem, index=False, size=10, widths=[1.4 * cm, 3.2 * cm, 6.4 * cm])
    mt_.hAlign = "CENTER"
    story.append(mt_)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Ngày lập: {date.today():%d/%m/%Y}", info))
    if filter_note:
        story.append(Paragraph(f"<i>Phạm vi dữ liệu: {filter_note}</i>", info))
    story.append(Spacer(1, 16))

    # Tóm tắt
    m = res["metrics"]
    best = m["R² (log giá)"].idxmax()
    imp = res["importance"]
    story.append(Paragraph("Tóm tắt", H2))
    story.append(Paragraph(
        f"Nghiên cứu phân tích {len(df):,} giao dịch nhà ở sau làm sạch nhằm xác định các yếu tố ảnh hưởng "
        f"đến giá bán và xây dựng mô hình dự đoán. Giá trung vị là {_usd(df.price.median())}. Diện tích ở có "
        f"tương quan mạnh nhất với log(giá) (r = {np.corrcoef(df.sqft_living, df.log_price)[0, 1]:.2f}); "
        f"vị trí (thành phố) là yếu tố quan trọng thứ hai. Mô hình tốt nhất ({best}) đạt R² = "
        f"{m.loc[best, 'R² (log giá)']:.3f} trên tập kiểm tra, sai số tuyệt đối trung bình "
        f"{_usd(m.loc[best, 'MAE (USD)'])} (MAPE {m.loc[best, 'MAPE (%)']:.1f}%).", P))

    # 1. Giới thiệu
    story.append(Paragraph("1. Giới thiệu đề tài", H1))
    story.append(Paragraph(
        "Giá nhà là chỉ báo quan trọng của thị trường bất động sản, ảnh hưởng trực tiếp đến quyết định "
        "của người mua, người bán, ngân hàng và cơ quan quản lý. Việc định giá thủ công thường dựa vào "
        "kinh nghiệm và khó nhất quán. Đề tài ứng dụng Python và học máy để phân tích dữ liệu giao dịch "
        "thực tế, tự động sinh báo cáo và dashboard tương tác phục vụ việc khám phá dữ liệu.", P))
    story.append(Paragraph("Mục tiêu và câu hỏi nghiên cứu:", P))
    for q in ["Giá nhà phân phối như thế nào và khác nhau ra sao giữa các thành phố?",
              "Những đặc điểm nào của căn nhà (diện tích, số phòng, tình trạng, view, tuổi nhà…) "
              "có liên hệ có ý nghĩa thống kê với giá bán?",
              "Mô hình hồi quy đơn giản có thể dự đoán giá nhà với độ chính xác bao nhiêu?"]:
        story.append(Paragraph(q, BUL, bulletText="•"))

    # 2. Mô tả dữ liệu
    story.append(Paragraph("2. Mô tả dữ liệu", H1))
    story.append(Paragraph(
        f"Nguồn: {NGUON}. Tệp data.csv gồm {len(raw):,} dòng × {raw.shape[1]} cột, mỗi dòng là một "
        f"giao dịch bán nhà tại {raw.city.nunique()} thành phố thuộc bang Washington (khu vực Seattle).", P))
    var_desc = pd.DataFrame([
        ("date", "Ngày giao dịch"), ("price", "Giá bán (USD) – biến mục tiêu"),
        ("bedrooms, bathrooms", "Số phòng ngủ, phòng tắm"),
        ("sqft_living, sqft_lot", "Diện tích ở, diện tích lô đất (feet vuông)"),
        ("sqft_above, sqft_basement", "Diện tích trên mặt đất, tầng hầm"),
        ("floors", "Số tầng"), ("waterfront", "Giáp mặt nước (0/1)"),
        ("view", "Điểm tầm nhìn (0–4)"), ("condition", "Tình trạng nhà (1–5)"),
        ("yr_built, yr_renovated", "Năm xây, năm cải tạo (0 = chưa cải tạo)"),
        ("street, city, statezip, country", "Địa chỉ, thành phố, mã bang + ZIP, quốc gia"),
    ], columns=["Biến", "Ý nghĩa"]).set_index("Biến")
    story.append(table(var_desc, widths=[5.5 * cm, W - 5.5 * cm], size=9))

    # 3. Phương pháp
    story.append(Paragraph("3. Phương pháp", H1))
    story.append(Paragraph("3.1. Làm sạch dữ liệu", H2))
    story.append(Paragraph(
        "Dữ liệu không có giá trị rỗng nhưng có giá trị bất hợp lý. Quy trình làm sạch (pandas, numpy) "
        "và số dòng bị loại ở mỗi bước:", P))
    cl = clean_log.set_index("Bước")
    story.append(table(cl, widths=[W - 6 * cm, 3 * cm, 3 * cm], size=9))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Các đặc trưng được tạo thêm: log(giá), giá/sqft, tuổi nhà = năm giao dịch − năm xây, cờ đã cải tạo, "
        "cờ có tầng hầm, log(diện tích lô đất); các thành phố có dưới 30 giao dịch được gộp thành nhóm "
        "“Khác”. Cột country bị loại vì chỉ có một giá trị.", P))
    story.append(Paragraph("3.2. Phân tích thống kê và mô hình", H2))
    for s in ["Thống kê mô tả, trực quan hóa bằng matplotlib/seaborn.",
              "Tương quan Pearson, kiểm định Welch t-test và ANOVA một yếu tố với mức ý nghĩa α = 0,05; "
              "dùng log(giá) vì phân phối giá lệch phải.",
              "Hai mô hình hồi quy (scikit-learn) dự đoán log(giá): Hồi quy tuyến tính (biến chuẩn hóa) và "
              "Random Forest (300 cây). Chia 80% huấn luyện / 20% kiểm tra, thêm kiểm định chéo 5-fold. "
              "Chỉ số: R², MAE, RMSE, MAPE (sai số tính trên giá USD sau khi đổi ngược từ log)."]:
        story.append(Paragraph(s, BUL, bulletText="•"))

    # 4. Kết quả
    story.append(PageBreak())
    story.append(Paragraph("4. Kết quả phân tích", H1))
    story.append(Paragraph("4.1. Thống kê mô tả", H2))
    desc = pt.descriptive(df).map(lambda v: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:,.1f}")
    story.append(table(desc, size=8,
                       widths=[4.2 * cm] + [(W - 4.2 * cm) / 7] * 7))
    story.append(Spacer(1, 6))
    figure("hist", "Phân phối giá bán và log(giá bán)")
    story.append(Paragraph(
        f"Giá bán lệch phải mạnh (TB {_usd(df.price.mean())} > trung vị {_usd(df.price.median())}); "
        "sau khi lấy log, phân phối gần chuẩn nên log(giá) được dùng làm biến mục tiêu.", P))

    story.append(Paragraph("4.2. Tương quan giữa các biến", H2))
    figure("corr", "Ma trận tương quan Pearson giữa các biến số", W * 0.8)
    figure("scatter", "Giá bán theo diện tích ở")

    story.append(Paragraph("4.3. Giá theo vị trí và đặc điểm nhà", H2))
    ct = pt.city_table(df)
    ct.index.name = "Thành phố"
    story.append(table(ct, fmt="{:,.0f}", size=8.5, widths=[3.6 * cm] + [(W - 3.6 * cm) / 4] * 4))
    story.append(Spacer(1, 6))
    figure("city", "Phân bố giá theo thành phố")
    figure("cat", "Giá trung vị theo tình trạng nhà và điểm view")

    story.append(Paragraph("4.4. Kiểm định thống kê", H2))
    t = tests.copy()
    t["p-value"] = t["p-value"].map(lambda p: "< 0,001" if p < 0.001 else f"{p:.4f}")
    t["Kết luận (α = 0,05)"] = np.where(tests["p-value"] < 0.05, "Có ý nghĩa", "Không có ý nghĩa")
    story.append(table(t, index=False, size=8, widths=[W - 8.4 * cm, 2.4 * cm, 2.4 * cm, 3.6 * cm]))

    story.append(Paragraph("4.5. Mô hình dự đoán giá", H2))
    mt = m.copy()
    mt.index.name = "Mô hình"
    for c in ["MAE (USD)", "RMSE (USD)"]:
        mt[c] = mt[c].map("{:,.0f}".format)
    story.append(table(mt, fmt="{:.3f}", size=8.5, widths=[3.6 * cm] + [(W - 3.6 * cm) / 5] * 5))
    story.append(Spacer(1, 6))
    figure("imp", "Độ quan trọng của các đặc trưng trong mô hình Random Forest")
    figure("pred", "Giá thực tế so với giá dự đoán trên tập kiểm tra", W * 0.65)
    eff = res["lr_effect_pct"]
    story.append(Paragraph(
        "Theo hồi quy tuyến tính (giữ các biến khác không đổi), khi diện tích ở tăng thêm một độ lệch chuẩn "
        f"(~{df.sqft_living.std():,.0f} sqft) giá tăng khoảng {eff['Diện tích ở (sqft)']:.1f}%; "
        f"số phòng tắm +{eff['Số phòng tắm']:.1f}%, điểm view +{eff['Điểm view (0–4)']:.1f}%, "
        f"tình trạng +{eff['Tình trạng (1–5)']:.1f}%. Số phòng ngủ có hệ số âm "
        f"({eff['Số phòng ngủ']:.1f}%): với cùng diện tích, nhiều phòng ngủ hơn nghĩa là phòng nhỏ hơn.", P))

    # 5. Kết luận
    story.append(Paragraph("5. Kết luận và đề xuất", H1))
    ct_full = df.groupby("city")["price"].median()
    big = df["city"].value_counts()
    big = big[big >= 30].index
    hi, lo = ct_full[big].idxmax(), ct_full[big].idxmin()
    wf = df.groupby("waterfront")["price"].median()
    conclusions = [
        f"Diện tích ở là yếu tố quyết định giá mạnh nhất (r = {np.corrcoef(df.sqft_living, df.log_price)[0, 1]:.2f}, "
        f"chiếm {imp.iloc[0]:.0%} độ quan trọng trong Random Forest).",
        f"Vị trí tạo chênh lệch lớn: giá trung vị ở {hi} ({_usd(ct_full[hi])}) cao gấp "
        f"{ct_full[hi] / ct_full[lo]:.1f} lần {lo} ({_usd(ct_full[lo])}); ANOVA theo thành phố có ý nghĩa (p < 0,001).",
        (f"Nhà giáp mặt nước có giá trung vị {_usd(wf.get(1, np.nan))} so với {_usd(wf.get(0, np.nan))}; "
         "view, tình trạng nhà và số phòng tắm cũng liên hệ có ý nghĩa thống kê với giá.")
        if 1 in wf.index else "View, tình trạng nhà và số phòng tắm liên hệ có ý nghĩa thống kê với giá.",
        f"Mô hình {best} giải thích khoảng {m.loc[best, 'R² (log giá)']:.0%} biến thiên của log(giá), sai số "
        f"trung bình ~{m.loc[best, 'MAPE (%)']:.0f}% – đủ dùng để ước lượng sơ bộ, chưa thay thế thẩm định chuyên nghiệp.",
    ]
    for c in conclusions:
        story.append(Paragraph(c, BUL, bulletText="•"))
    story.append(Paragraph("<b>Đề xuất:</b>", P))
    for s in ["Người mua/bán: dùng mô hình và dashboard để tham khảo khoảng giá hợp lý theo diện tích và vị trí "
              "trước khi đàm phán.",
              "Bổ sung đặc trưng vị trí chi tiết hơn (mã ZIP, tọa độ, khoảng cách trung tâm, trường học) và dữ liệu "
              "nhiều năm để nắm xu hướng theo thời gian.",
              "Thử các mô hình mạnh hơn (Gradient Boosting, XGBoost) và tinh chỉnh siêu tham số; theo dõi sai số "
              "theo từng phân khúc giá.",
              "Hạn chế: dữ liệu chỉ trong ~2 tháng năm 2014 tại một khu vực, nên kết quả không khái quát cho "
              "thị trường khác hay thời điểm hiện tại."]:
        story.append(Paragraph(s, BUL, bulletText="•"))

    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm,
                            title="Báo cáo khoa học – Dự đoán giá nhà",
                            author=f"{TEN_NHOM}: " + ", ".join(n for _, n in NHOM))
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    if tmp:
        tmp.cleanup()
    return res


def report_bytes(raw, filter_note=None):
    buf = io.BytesIO()
    build_report(raw, buf, filter_note=filter_note)
    return buf.getvalue()


if __name__ == "__main__":
    os.makedirs(REPORT_DIR, exist_ok=True)
    out = os.path.join(REPORT_DIR, "bao_cao_khoa_hoc.pdf")
    r = build_report(pt.load_raw(), out, fig_dir=FIG_DIR)
    print(r["metrics"].round(3).to_string())
    print("Đã tạo:", out)
