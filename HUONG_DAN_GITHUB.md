# Hướng dẫn đưa dự án lên GitHub

Thư mục dự án **đã là một git repo** (nhánh `main`, đã có commit). Chỉ cần tạo repo trên GitHub và đẩy code lên.

---

## Bước 1. Tạo repo trống trên GitHub

1. Đăng nhập <https://github.com> (chưa có tài khoản thì bấm **Sign up**).
2. Bấm dấu **+** góc trên phải → **New repository**.
3. Điền:
   - **Repository name:** ví dụ `du-doan-gia-nha-nhom11` (không dấu, không khoảng trắng).
   - **Description:** `Mini-project: phân tích & dự đoán giá nhà, báo cáo PDF tự động, dashboard Streamlit`.
   - Chọn **Public** (giảng viên xem được) hoặc **Private** (nhớ mời giảng viên vào xem).
   - **KHÔNG** tích *Add a README file*, **KHÔNG** chọn *.gitignore* hay *license*
     (dự án đã có sẵn, tích vào sẽ gây xung đột khi đẩy lên).
4. Bấm **Create repository** rồi sao chép đường link dạng
   `https://github.com/<ten-tai-khoan>/du-doan-gia-nha-nhom11.git`.

---

## Bước 2. Kiểm tra tên tác giả commit (làm 1 lần)

Mở PowerShell tại thư mục dự án (`Bài 6`), kiểm tra:

```powershell
git config user.name
git config user.email
```

Nếu muốn đổi cho trùng tài khoản GitHub:

```powershell
git config --global user.name "Nguyen Van Tan Loc"
git config --global user.email "email-dang-ky-github@example.com"
```

---

## Bước 3. Kết nối và đẩy code lên

> ⚠️ **Thay `<ten-tai-khoan>` bằng tên tài khoản GitHub thật** (và tên repo nếu bạn đặt khác),
> tốt nhất là dán nguyên link đã sao chép ở Bước 1. Giữ nguyên `<ten-tai-khoan>` sẽ báo lỗi
> `The requested URL returned error: 400`. Nếu lỡ thêm sai, sửa bằng
> `git remote set-url origin <link-dung>`.

```powershell
cd "D:\CÁ NHÂN\A_THACSI\công nghệ số nâng cao\Bài 4\Bài 6"
git remote add origin https://github.com/<ten-tai-khoan>/du-doan-gia-nha-nhom11.git
git push -u origin main
```

Lần đầu đẩy lên, Windows sẽ mở cửa sổ **Git Credential Manager** → chọn **Sign in with your browser**
→ đăng nhập GitHub → bấm **Authorize**. Những lần sau không cần đăng nhập lại.

> Nếu không hiện cửa sổ đăng nhập mà hỏi *Password*: GitHub không nhận mật khẩu tài khoản.
> Vào **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) →
> Generate new token**, tích quyền **repo**, rồi dán token đó vào ô Password.

Tải lại trang repo trên GitHub: phải thấy `README.md` hiển thị cùng các thư mục `src/`, `reports/`,
file `app.py`, `data.csv`, `LICENSE`, `requirements.txt`.

---

## Bước 4. Thêm thành viên nhóm

Trên trang repo: **Settings → Collaborators → Add people** → nhập username GitHub của từng thành viên:

| MSSV | Họ và tên |
|---|---|
| M2526019 | Trương Thị Thanh Loan |
| M2526029 | Bùi Gia Bảo |
| M2526020 | Nguyễn Văn Tấn Lộc |

Thành viên nhận email mời → **Accept invitation**. Sau đó mỗi người tải dự án về máy:

```powershell
git clone https://github.com/<ten-tai-khoan>/du-doan-gia-nha-nhom11.git
cd du-doan-gia-nha-nhom11
pip install -r requirements.txt
```

---

## Bước 5. Cập nhật code về sau

Mỗi lần sửa xong:

```powershell
git pull                      # lấy thay đổi mới nhất của các bạn trong nhóm
git add -A
git commit -m "Mô tả ngắn thay đổi"
git push
```

Nếu sửa phân tích, nhớ sinh lại báo cáo trước khi commit:

```powershell
py src/bao_cao.py
```

---

## Bước 6 (tuỳ chọn). Mô tả repo cho đẹp

Trên trang repo, bấm biểu tượng ⚙️ cạnh **About**:
- **Topics:** `python`, `data-analysis`, `machine-learning`, `streamlit`, `reportlab`, `house-price`.
- Tích **Releases**: có thể tạo bản phát hành `v1.0` đính kèm `reports/bao_cao_khoa_hoc.pdf` để nộp bài.

**Đưa dashboard lên mạng (miễn phí):** vào <https://share.streamlit.io> → đăng nhập bằng GitHub →
**Create app** → chọn repo, nhánh `main`, file `app.py` → **Deploy**. Bạn sẽ có link dạng
`https://<ten-app>.streamlit.app` để gửi giảng viên.

---

## Lỗi thường gặp

| Thông báo lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `remote origin already exists` | Đã thêm remote trước đó | `git remote set-url origin <link-moi>` |
| `The requested URL returned error: 400` | Link remote còn chữ mẫu `<ten-tai-khoan>` | `git remote set-url origin https://github.com/<user-that>/<ten-repo>.git` |
| `fatal: not in a git directory` khi `git config user.email` | Chạy ngoài thư mục dự án mà thiếu `--global` | Thêm `--global` hoặc `cd` vào thư mục dự án trước |
| `Repository not found` | Sai tên tài khoản/tên repo, hoặc chưa tạo repo trên GitHub | Kiểm tra lại link trên trang repo (nút **Code**) |
| `! [rejected] main -> main (fetch first)` | Repo GitHub đã có README/LICENSE tạo sẵn | `git pull origin main --allow-unrelated-histories`, giữ bản của mình khi xung đột, rồi `git push -u origin main` |
| `Authentication failed` / `Support for password authentication was removed` | Dùng mật khẩu thay vì đăng nhập trình duyệt/token | Dùng Git Credential Manager hoặc Personal access token (Bước 3) |
| `error: src refspec main does not match any` | Chưa có commit hoặc nhánh tên khác | `git branch` để xem tên nhánh; `git add -A` rồi `git commit -m "..."` |
| `Permission denied (403)` | Đẩy vào repo của người khác khi chưa được mời | Chủ repo thêm bạn vào **Collaborators** (Bước 4) |
| Không thấy file `.claude/`, `__pycache__/` trên GitHub | Bị loại trong `.gitignore` (đúng ý) | Không cần xử lý |

---

## Cách khác: GitHub Desktop (không cần gõ lệnh)

1. Cài <https://desktop.github.com> và đăng nhập GitHub.
2. **File → Add local repository** → chọn thư mục `Bài 6`.
3. Bấm **Publish repository** → đặt tên, bỏ tích *Keep this code private* nếu muốn công khai → **Publish**.
4. Về sau: sửa code → ghi mô tả ở ô **Summary** → **Commit to main** → **Push origin**.
