"""
Dashboard tương tác – Phân tích & dự đoán giá nhà
Chạy:  streamlit run app.py      (hoặc: py -m streamlit run app.py)
"""
import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit import runtime

# Chạy bằng "python app.py" (hoặc nút Run của VS Code) -> tự khởi động lại bằng "streamlit run"
if __name__ == "__main__" and not runtime.exists():
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__),
                              *sys.argv[1:]]))

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
import phan_tich as pt  # noqa: E402

st.set_page_config(page_title="Dashboard giá nhà", page_icon="🏠", layout="wide")
L = pt.VAR_LABELS


@st.cache_data
def load():
    raw = pt.load_raw()
    df, log = pt.clean(raw)
    return raw, df, log


@st.cache_resource
def models(df):
    return pt.train_models(df)


raw, df_all, clean_log = load()

# ---------- Bộ lọc ----------
st.sidebar.header("Bộ lọc dữ liệu")
cities = df_all["city"].value_counts().index.tolist()
sel_city = st.sidebar.multiselect("Thành phố", cities, placeholder="Tất cả thành phố")
pmin, pmax = int(df_all.price.min()), int(df_all.price.max())
price_rng = st.sidebar.slider("Khoảng giá (USD)", pmin, pmax, (pmin, pmax), step=10000, format="%d")
y0, y1 = int(df_all.yr_built.min()), int(df_all.yr_built.max())
yr_rng = st.sidebar.slider("Năm xây dựng", y0, y1, (y0, y1))
beds = st.sidebar.slider("Số phòng ngủ", int(df_all.bedrooms.min()), int(df_all.bedrooms.max()),
                         (int(df_all.bedrooms.min()), int(df_all.bedrooms.max())))

mask = (df_all.price.between(*price_rng) & df_all.yr_built.between(*yr_rng)
        & df_all.bedrooms.between(*beds))
if sel_city:
    mask &= df_all.city.isin(sel_city)
df = df_all[mask]
st.sidebar.caption(f"Đang hiển thị {len(df):,} / {len(df_all):,} căn nhà")

st.title("🏠 Phân tích & dự đoán giá nhà – bang Washington (2014)")
if df.empty:
    st.warning("Không có dữ liệu phù hợp bộ lọc. Hãy nới rộng điều kiện lọc.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Tổng quan", "🔎 Khám phá biến", "🧮 Tương quan & kiểm định", "🤖 Mô hình dự đoán", "📄 Báo cáo"])

# ---------- Tab 1: Tổng quan ----------
with tab1:
    c = st.columns(4)
    c[0].metric("Số căn nhà", f"{len(df):,}")
    c[1].metric("Giá trung vị", f"${df.price.median():,.0f}")
    c[2].metric("Diện tích TB", f"{df.sqft_living.mean():,.0f} sqft")
    c[3].metric("Giá / sqft (TV)", f"${df.price_per_sqft.median():,.0f}")

    a, b = st.columns(2)
    a.plotly_chart(px.histogram(df, x="price", nbins=60, labels=L, title="Phân phối giá bán",
                                color_discrete_sequence=["#2E5EAA"]), width="stretch")
    city_med = (df.groupby("city").agg(gia=("price", "median"), n=("price", "size"))
                .query("n >= 5").sort_values("gia").tail(15).reset_index())
    b.plotly_chart(px.bar(city_med, x="gia", y="city", orientation="h", text_auto=".3s",
                          labels={"gia": "Giá trung vị (USD)", "city": ""},
                          title="Giá trung vị theo thành phố (≥ 5 giao dịch)",
                          color_discrete_sequence=["#E07A1F"]), width="stretch")

    with st.expander("Quy trình làm sạch dữ liệu"):
        st.dataframe(clean_log, hide_index=True, width="stretch")
    st.subheader("Dữ liệu")
    show = ["date", "price", "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
            "waterfront", "view", "condition", "yr_built", "city", "street"]
    st.dataframe(df[show], width="stretch", height=300)
    st.download_button("⬇️ Tải dữ liệu đã lọc (CSV)", df[show].to_csv(index=False).encode("utf-8-sig"),
                       "du_lieu_loc.csv", "text/csv")

# ---------- Tab 2: Khám phá ----------
with tab2:
    opts = pt.NUMERIC_VARS
    c = st.columns(4)
    kind = c[0].selectbox("Loại biểu đồ", ["Phân tán", "Histogram", "Hộp (box)", "Cột (trung vị)"])
    x = c[1].selectbox("Biến X", opts + ["city"], index=opts.index("sqft_living"),
                       format_func=lambda v: L.get(v, v))
    y = c[2].selectbox("Biến Y", opts, index=0, format_func=lambda v: L.get(v, v))
    color = c[3].selectbox("Tô màu theo", [None, "condition", "view", "waterfront", "has_basement",
                                           "was_renovated", "floors"],
                           format_func=lambda v: "(không)" if v is None else L.get(v, v))
    d = df.copy()
    if color:
        d[color] = d[color].astype(str)
    if kind == "Phân tán":
        fig = px.scatter(d, x=x, y=y, color=color, opacity=0.6, labels=L,
                         hover_data=["city", "street"])
    elif kind == "Histogram":
        fig = px.histogram(d, x=x, color=color, nbins=50, labels=L, barmode="overlay")
    elif kind == "Hộp (box)":
        fig = px.box(d, x=x if x in ["city", "bedrooms", "floors", "view", "condition"] else color,
                     y=y, color=color, labels=L)
    else:
        g = d.groupby(x)[y].median().reset_index()
        fig = px.bar(g, x=x, y=y, labels=L)
    fig.update_layout(height=520, title=f"{L.get(y, y)} theo {L.get(x, x)}" if kind != "Histogram"
                      else f"Phân phối {L.get(x, x)}")
    st.plotly_chart(fig, width="stretch")
    st.caption("Gợi ý: biểu đồ hộp phù hợp khi X là biến rời rạc (thành phố, số phòng ngủ, tình trạng, view).")

# ---------- Tab 3: Tương quan & kiểm định ----------
with tab3:
    vars_ = st.multiselect("Chọn biến cho ma trận tương quan", pt.NUMERIC_VARS,
                           default=["price", "sqft_living", "bathrooms", "bedrooms", "view",
                                    "condition", "house_age"], format_func=lambda v: L.get(v, v))
    if len(vars_) >= 2:
        corr = df[vars_].corr().round(2)
        corr.index = corr.columns = [L.get(v, v) for v in vars_]
        st.plotly_chart(px.imshow(corr, text_auto=True, color_continuous_scale="RdBu_r",
                                  zmin=-1, zmax=1, aspect="auto", title="Ma trận tương quan Pearson"),
                        width="stretch")
    if len(df) >= 30:
        t = pt.stat_tests(df)
        t["Kết luận (α=0,05)"] = np.where(t["p-value"] < 0.05, "Có ý nghĩa", "Không có ý nghĩa")
        t["p-value"] = t["p-value"].map(lambda p: "< 0,001" if p < 0.001 else f"{p:.4f}")
        st.subheader("Kiểm định thống kê trên dữ liệu đang lọc")
        st.dataframe(t, hide_index=True, width="stretch")
    else:
        st.info("Cần ít nhất 30 căn nhà để chạy kiểm định thống kê.")

# ---------- Tab 4: Mô hình ----------
with tab4:
    res = models(df_all)
    st.subheader("Hiệu năng mô hình (huấn luyện trên toàn bộ dữ liệu sạch)")
    m = res["metrics"].copy()
    st.dataframe(m.style.format({"R² (log giá)": "{:.3f}", "R² CV 5-fold": "{:.3f}",
                                 "MAE (USD)": "{:,.0f}", "RMSE (USD)": "{:,.0f}", "MAPE (%)": "{:.1f}"}),
                 width="stretch")
    a, b = st.columns(2)
    imp = res["importance"].sort_values().reset_index()
    imp.columns = ["Đặc trưng", "Độ quan trọng"]
    a.plotly_chart(px.bar(imp, x="Độ quan trọng", y="Đặc trưng", orientation="h",
                          title="Độ quan trọng đặc trưng (Random Forest)", text_auto=".1%"),
                   width="stretch")
    name = b.radio("Mô hình", list(res["preds"]), horizontal=True)
    pr = res["preds"][name]
    fig = px.scatter(pr, x="Thực tế", y="Dự đoán", opacity=0.5, title="Thực tế vs dự đoán (tập kiểm tra)")
    mx = pr.max().max()
    fig.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx, line=dict(color="red", dash="dash"))
    b.plotly_chart(fig, width="stretch")

    st.subheader("🔮 Ước tính giá một căn nhà")
    c = st.columns(4)
    inp = dict(
        sqft_living=c[0].number_input("Diện tích ở (sqft)", 300, 10000, 2000, 50),
        sqft_lot=c[1].number_input("Diện tích lô đất (sqft)", 500, 500000, 7500, 100),
        bedrooms=c[2].number_input("Số phòng ngủ", 1, 9, 3),
        bathrooms=c[3].number_input("Số phòng tắm", 0.5, 8.0, 2.0, 0.25),
    )
    c = st.columns(4)
    inp.update(
        floors=c[0].selectbox("Số tầng", [1.0, 1.5, 2.0, 2.5, 3.0, 3.5], index=0),
        condition=c[1].slider("Tình trạng (1–5)", 1, 5, 3),
        view=c[2].slider("Điểm view (0–4)", 0, 4, 0),
        house_age=2014 - c[3].number_input("Năm xây dựng", 1900, 2014, 1980),
    )
    c = st.columns(4)
    inp.update(
        waterfront=int(c[0].checkbox("Giáp mặt nước")),
        has_basement=int(c[1].checkbox("Có tầng hầm")),
        was_renovated=int(c[2].checkbox("Đã cải tạo")),
        city_grp=c[3].selectbox("Thành phố", (cg := sorted(df_all.city_grp.unique())),
                                index=cg.index("Seattle") if "Seattle" in cg else 0),
    )
    out = {n: pt.predict_price(mdl, **inp) for n, mdl in res["models"].items()}
    c = st.columns(len(out))
    for col, (n, v) in zip(c, out.items()):
        col.metric(f"Giá dự đoán – {n}", f"${v:,.0f}")
    st.caption(f"Sai số trung bình tham khảo (MAPE) ~{m['MAPE (%)'].min():.0f}%. "
               "Kết quả chỉ mang tính tham khảo.")

# ---------- Tab 5: Báo cáo ----------
with tab5:
    st.subheader("Tải báo cáo khoa học PDF")
    pdf_path = os.path.join(pt.ROOT, "reports", "bao_cao_khoa_hoc.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Báo cáo đầy đủ (toàn bộ dữ liệu)", f.read(),
                               "bao_cao_khoa_hoc.pdf", "application/pdf")
    else:
        st.info("Chưa có báo cáo sẵn. Chạy `py src/bao_cao.py` hoặc tạo báo cáo bên dưới.")

    st.markdown("**Tạo báo cáo cho dữ liệu đang lọc** – phân tích, mô hình và biểu đồ được tính lại "
                "theo bộ lọc ở thanh bên.")
    if st.button("⚙️ Sinh báo cáo PDF theo bộ lọc"):
        import bao_cao
        note = ", ".join(sel_city) if sel_city else "tất cả thành phố"
        note += f"; giá {price_rng[0]:,}–{price_rng[1]:,} USD; năm xây {yr_rng[0]}–{yr_rng[1]}"
        raw_f = raw[raw.price.between(*price_rng) & raw.yr_built.between(*yr_rng)
                    & raw.bedrooms.between(*beds)]
        if sel_city:
            raw_f = raw_f[raw_f.city.isin(sel_city)]
        try:
            with st.spinner("Đang phân tích và dựng PDF..."):
                st.session_state["pdf_filtered"] = bao_cao.report_bytes(raw_f, filter_note=note)
        except ValueError as e:
            st.error(str(e))
    if "pdf_filtered" in st.session_state:
        st.download_button("⬇️ Tải báo cáo theo bộ lọc", st.session_state["pdf_filtered"],
                           "bao_cao_theo_bo_loc.pdf", "application/pdf")
