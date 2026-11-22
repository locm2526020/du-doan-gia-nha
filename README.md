# AI + Python sinh báo cáo khoa học từ dữ liệu – Dự đoán giá nhà

Mini-project môn **Công nghệ số nâng cao** – Yêu cầu 6: *Tự động hóa sáng tạo và quản lý nội dung số*.

Dự án đọc dữ liệu giao dịch nhà ở thực tế, làm sạch, phân tích thống kê, huấn luyện mô hình hồi quy,
rồi **tự động sinh báo cáo khoa học PDF** và cung cấp **dashboard Streamlit** để người dùng chọn biến,
xem biểu đồ, ước tính giá và tải báo cáo.

## Nhóm thực hiện – Nhóm 11

| STT | MSSV | Họ và tên |
|---|---|---|
| 1 | M2526019 | Trương Thị Thanh Loan |
| 2 | M2526029 | Bùi Gia Bảo |
| 3 | M2526020 | Nguyễn Văn Tấn Lộc |

## Dữ liệu

- **Nguồn:** Kaggle – [House Price Prediction](https://www.kaggle.com/datasets/shree1992/housedata) (`data.csv`)
- **Quy mô:** 4.600 giao dịch × 18 cột, bang Washington (khu vực Seattle), 02/05–10/07/2014
- **Biến chính:** `price` (mục tiêu), `bedrooms`, `bathrooms`, `sqft_living`, `sqft_lot`, `floors`,
  `waterfront`, `view`, `condition`, `yr_built`, `yr_renovated`, `city`, …

## Kết quả chính

| Mô hình | R² (log giá, tập kiểm tra) | R² CV 5-fold | MAE (USD) | MAPE |
|---|---|---|---|---|
| Hồi quy tuyến tính | 0,695 | 0,712 | ~110.000 | 21,8% |
| Random Forest | **0,721** | **0,719** | **~103.000** | **20,9%** |

- Sau làm sạch còn **4.471** giao dịch (loại 49 dòng giá = 0, 2 dòng 0 phòng, 78 ngoại lai).
- **Diện tích ở** là yếu tố quan trọng nhất (r = 0,66 với log giá; 52% độ quan trọng RF), tiếp theo là **thành phố** (25%).
- Giá trung vị ở Bellevue (~712 nghìn USD) cao gấp khoảng 2,7 lần Federal Way (~265 nghìn USD).
- Mọi kiểm định (Pearson, Welch t-test, ANOVA) đều có ý nghĩa ở mức α = 0,05.

Báo cáo đầy đủ: [`reports/bao_cao_khoa_hoc.pdf`](reports/bao_cao_khoa_hoc.pdf)

## Cấu trúc thư mục

```
├── app.py                    # Dashboard Streamlit
├── data.csv                  # Dữ liệu mẫu (Kaggle)
├── src/
│   ├── phan_tich.py          # Làm sạch, thống kê, kiểm định, mô hình (dùng chung)
│   └── bao_cao.py            # Sinh báo cáo PDF (reportlab + matplotlib/seaborn)
├── reports/
│   ├── bao_cao_khoa_hoc.pdf  # Báo cáo đã sinh
│   └── figures/              # Biểu đồ PNG
├── requirements.txt
├── LICENSE                   # MIT
├── HUONG_DAN_GITHUB.md       # Hướng dẫn đưa dự án lên GitHub
└── README.md
```

## Cài đặt và chạy

```bash
pip install -r requirements.txt

# 1) Sinh báo cáo PDF -> reports/bao_cao_khoa_hoc.pdf
python src/bao_cao.py

# 2) Mở dashboard tại http://localhost:8501
streamlit run app.py
```

> Trên Windows có thể dùng `py` thay cho `python`, và `py -m streamlit run app.py`.
> Báo cáo dùng font Arial (Windows) hoặc DejaVu Sans (Linux) để hiển thị tiếng Việt.

## Dashboard

| Tab | Chức năng |
|---|---|
| Tổng quan | Chỉ số chính, phân phối giá, giá theo thành phố, bảng dữ liệu, tải CSV đã lọc |
| Khám phá biến | Chọn loại biểu đồ (phân tán, histogram, hộp, cột), biến X, Y và biến tô màu |
| Tương quan & kiểm định | Ma trận tương quan theo biến tự chọn, bảng kiểm định trên dữ liệu đang lọc |
| Mô hình dự đoán | So sánh mô hình, độ quan trọng đặc trưng, thực tế vs dự đoán, form ước tính giá |
| Báo cáo | Tải báo cáo PDF đầy đủ hoặc sinh báo cáo mới theo bộ lọc |

Thanh bên cho phép lọc theo thành phố, khoảng giá, năm xây dựng và số phòng ngủ.

## Phương pháp

1. **Làm sạch** (pandas, numpy): loại giá = 0, nhà 0 phòng ngủ/tắm, dòng trùng, ngoại lai theo 1,5×IQR trên log(giá);
   tạo đặc trưng tuổi nhà, cờ cải tạo, cờ tầng hầm, giá/sqft, log diện tích lô đất, nhóm thành phố.
2. **Trực quan hóa:** matplotlib, seaborn (báo cáo) và plotly (dashboard).
3. **Thống kê:** tương quan Pearson, Welch t-test, ANOVA một yếu tố (scipy).
4. **Mô hình:** Linear Regression và Random Forest (scikit-learn) dự đoán log(giá); chia 80/20 và CV 5-fold.
5. **Báo cáo tự động:** nội dung, số liệu và kết luận được tính từ dữ liệu rồi dựng PDF bằng reportlab.

## Giấy phép

- **Mã nguồn và báo cáo:** phát hành theo giấy phép [MIT](LICENSE). Bạn được tự do sử dụng, sửa đổi và phân phối, miễn giữ nguyên thông báo bản quyền.
- **Dữ liệu `data.csv`:** thuộc tác giả dataset trên Kaggle và tuân theo giấy phép ghi trên trang dataset; dự án chỉ dùng cho mục đích học tập.
