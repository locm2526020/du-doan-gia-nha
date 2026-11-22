"""
Module phân tích dữ liệu giá nhà (dùng chung cho báo cáo PDF và dashboard).
  - load_raw()      : đọc CSV gốc
  - clean()         : làm sạch + tạo đặc trưng, trả về (df_sạch, nhật_ký_làm_sạch)
  - descriptive()   : thống kê mô tả
  - stat_tests()    : tương quan Pearson, kiểm định t, ANOVA
  - train_models()  : hồi quy tuyến tính & Random Forest dự đoán log(giá)
"""
import os

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data.csv")
SEED = 42

VAR_LABELS = {
    "price": "Giá bán (USD)",
    "log_price": "log(Giá bán)",
    "price_per_sqft": "Giá / sqft (USD)",
    "bedrooms": "Số phòng ngủ",
    "bathrooms": "Số phòng tắm",
    "sqft_living": "Diện tích ở (sqft)",
    "sqft_lot": "Diện tích lô đất (sqft)",
    "sqft_above": "Diện tích trên mặt đất (sqft)",
    "sqft_basement": "Diện tích tầng hầm (sqft)",
    "floors": "Số tầng",
    "waterfront": "Giáp mặt nước (0/1)",
    "view": "Điểm view (0–4)",
    "condition": "Tình trạng (1–5)",
    "yr_built": "Năm xây dựng",
    "house_age": "Tuổi nhà (năm)",
    "was_renovated": "Đã cải tạo (0/1)",
    "has_basement": "Có tầng hầm (0/1)",
    "city": "Thành phố",
}
NUMERIC_VARS = ["price", "price_per_sqft", "bedrooms", "bathrooms", "sqft_living", "sqft_lot",
                "sqft_above", "sqft_basement", "floors", "view", "condition", "yr_built",
                "house_age"]
MODEL_NUM = ["sqft_living", "log_sqft_lot", "bedrooms", "bathrooms", "floors", "waterfront",
             "view", "condition", "house_age", "was_renovated", "has_basement"]
MODEL_CAT = ["city_grp"]


def load_raw(path=DATA_PATH):
    return pd.read_csv(path)


def clean(raw):
    """Làm sạch theo từng bước, ghi lại số dòng bị loại."""
    log = []
    df = raw.copy()
    n0 = len(df)
    log.append(("Dữ liệu gốc", n0, 0))

    def step(name, mask_keep):
        nonlocal df
        before = len(df)
        df = df[mask_keep].copy()
        log.append((name, len(df), before - len(df)))

    step("Loại giá bán = 0 (thiếu giá)", df["price"] > 0)
    step("Loại nhà 0 phòng ngủ hoặc 0 phòng tắm", (df["bedrooms"] > 0) & (df["bathrooms"] > 0))
    step("Loại dòng trùng lặp", ~df.duplicated())
    lp = np.log(df["price"])
    q1, q3 = lp.quantile([0.25, 0.75])
    iqr = q3 - q1
    step("Loại ngoại lai giá (quy tắc 1,5×IQR trên log giá)",
         lp.between(q1 - 1.5 * iqr, q3 + 1.5 * iqr))

    # Chuẩn hóa kiểu & tạo đặc trưng
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop(columns=["country"])                     # chỉ có 1 giá trị "USA"
    df["bedrooms"] = df["bedrooms"].astype(int)
    df["zipcode"] = df["statezip"].str.extract(r"(\d{5})")[0]
    df["log_price"] = np.log(df["price"])
    df["price_per_sqft"] = df["price"] / df["sqft_living"]
    df["house_age"] = df["date"].dt.year - df["yr_built"]
    df["was_renovated"] = (df["yr_renovated"] > df["yr_built"]).astype(int)
    df["has_basement"] = (df["sqft_basement"] > 0).astype(int)
    df["log_sqft_lot"] = np.log(df["sqft_lot"])
    top_cities = df["city"].value_counts()
    keep = top_cities[top_cities >= 30].index
    df["city_grp"] = np.where(df["city"].isin(keep), df["city"], "Khác")
    df = df.reset_index(drop=True)
    log.append(("Dữ liệu sau làm sạch", len(df), n0 - len(df)))
    return df, pd.DataFrame(log, columns=["Bước", "Số dòng còn lại", "Số dòng loại"])


def descriptive(df, cols=None):
    cols = cols or ["price", "sqft_living", "sqft_lot", "bedrooms", "bathrooms", "floors",
                    "condition", "house_age", "price_per_sqft"]
    d = df[cols].describe().T[["mean", "std", "min", "25%", "50%", "75%", "max"]]
    d.columns = ["TB", "Độ lệch chuẩn", "Min", "Q1", "Trung vị", "Q3", "Max"]
    d.index = [VAR_LABELS.get(c, c) for c in d.index]
    return d


def city_table(df, top=10):
    g = df.groupby("city").agg(so_nha=("price", "size"), gia_tb=("price", "mean"),
                               gia_tv=("price", "median"), gia_sqft=("price_per_sqft", "median"))
    g = g.sort_values("so_nha", ascending=False).head(top).sort_values("gia_tv", ascending=False)
    g.columns = ["Số nhà", "Giá TB", "Giá trung vị", "Giá/sqft (TV)"]
    return g


def stat_tests(df):
    res = []
    for v in ["sqft_living", "bathrooms", "bedrooms", "view", "house_age", "sqft_lot"]:
        r, p = stats.pearsonr(df[v], df["log_price"])
        res.append({"Kiểm định": f"Tương quan Pearson: log(giá) ~ {VAR_LABELS[v]}",
                    "Thống kê": f"r = {r:.3f}", "p-value": p})
    a = df.loc[df.waterfront == 1, "log_price"]
    b = df.loc[df.waterfront == 0, "log_price"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    res.append({"Kiểm định": "Welch t-test: log(giá) nhà giáp mặt nước vs không",
                "Thống kê": f"t = {t:.2f}", "p-value": p})
    a = df.loc[df.has_basement == 1, "log_price"]
    b = df.loc[df.has_basement == 0, "log_price"]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    res.append({"Kiểm định": "Welch t-test: log(giá) có tầng hầm vs không",
                "Thống kê": f"t = {t:.2f}", "p-value": p})
    groups = [g["log_price"].values for _, g in df.groupby("condition") if len(g) > 5]
    f, p = stats.f_oneway(*groups)
    res.append({"Kiểm định": "ANOVA một yếu tố: log(giá) theo tình trạng nhà",
                "Thống kê": f"F = {f:.2f}", "p-value": p})
    top = df["city"].value_counts().head(10).index
    groups = [df.loc[df.city == c, "log_price"].values for c in top]
    f, p = stats.f_oneway(*groups)
    res.append({"Kiểm định": "ANOVA một yếu tố: log(giá) theo 10 thành phố lớn nhất",
                "Thống kê": f"F = {f:.2f}", "p-value": p})
    return pd.DataFrame(res)


def _pipeline(model, scale):
    num = StandardScaler() if scale else "passthrough"
    pre = ColumnTransformer([("num", num, MODEL_NUM),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), MODEL_CAT)])
    return Pipeline([("pre", pre), ("model", model)])


def train_models(df):
    """Huấn luyện 2 mô hình dự đoán log(giá); đánh giá trên tập kiểm tra 20% + CV 5-fold."""
    X, y = df[MODEL_NUM + MODEL_CAT], df["log_price"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=SEED)
    models = {
        "Hồi quy tuyến tính": _pipeline(LinearRegression(), scale=True),
        "Random Forest": _pipeline(RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                                                         random_state=SEED, n_jobs=-1),
                                   scale=False),
    }
    kf = KFold(5, shuffle=True, random_state=SEED)
    rows, preds = [], {}
    for name, pipe in models.items():
        cv = cross_val_score(pipe, X, y, cv=kf, scoring="r2")
        pipe.fit(X_tr, y_tr)
        p_log = pipe.predict(X_te)
        p, a = np.exp(p_log), np.exp(y_te)
        preds[name] = pd.DataFrame({"Thực tế": a.values, "Dự đoán": p})
        rows.append({"Mô hình": name,
                     "R² (log giá)": r2_score(y_te, p_log),
                     "R² CV 5-fold": cv.mean(),
                     "MAE (USD)": mean_absolute_error(a, p),
                     "RMSE (USD)": np.sqrt(mean_squared_error(a, p)),
                     "MAPE (%)": np.mean(np.abs(p - a) / a) * 100})
    metrics = pd.DataFrame(rows).set_index("Mô hình")

    # Độ quan trọng đặc trưng (Random Forest), gộp các cột one-hot của thành phố
    rf = models["Random Forest"]
    names = rf.named_steps["pre"].get_feature_names_out()
    imp = pd.Series(rf.named_steps["model"].feature_importances_, index=names)
    grouped = imp.groupby(lambda n: "city" if n.startswith("cat__") else n.split("__", 1)[1]).sum()
    label = {**VAR_LABELS, "log_sqft_lot": "log(Diện tích lô đất)", "city": "Thành phố"}
    grouped.index = [label.get(i, i) for i in grouped.index]

    # Hệ số hồi quy tuyến tính (biến số đã chuẩn hóa) -> % thay đổi giá khi tăng 1 độ lệch chuẩn
    lr = models["Hồi quy tuyến tính"]
    coef = pd.Series(lr.named_steps["model"].coef_[:len(MODEL_NUM)], index=MODEL_NUM)
    coef_pct = (np.exp(coef) - 1) * 100
    coef_pct.index = [label.get(i, i) for i in coef_pct.index]

    return {"metrics": metrics, "preds": preds, "models": models,
            "importance": grouped.sort_values(ascending=False),
            "lr_effect_pct": coef_pct.sort_values()}


def predict_price(model, **features):
    """Dự đoán giá cho 1 căn nhà từ các đặc trưng đầu vào (dùng trong dashboard)."""
    row = pd.DataFrame([features])
    row["log_sqft_lot"] = np.log(row.pop("sqft_lot"))
    return float(np.exp(model.predict(row[MODEL_NUM + MODEL_CAT])[0]))
