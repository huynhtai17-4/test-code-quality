# SKILLS.md — Thiết kế UX/UI Desktop (PyQt6)

_Bản 2: đã tinh chỉnh sau khi chạy thử giao diện thật (căn lề, tỷ lệ cột, khoảng cách, trạng thái rỗng, thứ bậc nút)._

Đề tài: **Hệ thống phân tích và đánh giá chất lượng mã nguồn mở**
Phạm vi: chỉ phần `frontend/` (GUI PyQt6 + matplotlib). Backend không liên quan file này.

> Dành cho AI (Gemini) khi viết code giao diện: đọc hết file này trước khi viết bất kỳ view, stylesheet hay biểu đồ nào. Khi có xung đột giữa file này và thói quen mặc định của bạn, **file này thắng**.

---

## 1. Mục tiêu giao diện

Người dùng là **sinh viên và lập trình viên** đang kiểm tra chất lượng một dự án. Họ cần:

1. Biết ngay dự án này **tốt hay tệ** (điểm + xếp loại).
2. Biết **tệ ở đâu** (file nào, dòng nào, tiêu chí nào).
3. Xử lý từng lỗi nhanh bằng bàn phím và chuột, không phải đi tìm.

Giao diện phải giống **một công cụ làm việc nghiêm túc** (như trình soạn code, công cụ review), không giống trang web giới thiệu sản phẩm hay một app "đẹp cho có".

Một câu chốt hướng: **"Đọc như một báo cáo kiểm định, thao tác như một công cụ lập trình."**

---

## 2. Thế nào là "nhựa" và "AI" (cấm)

Đây là các dấu hiệu khiến giao diện trông như sinh tự động. **Không được dùng**, trừ khi tài liệu này cho phép rõ:

| Cấm | Vì sao |
|---|---|
| Mọi thứ đều nằm trong thẻ (card) bo góc to, đổ bóng xám giống hệt nhau | Dấu hiệu rõ nhất của giao diện mẫu. Dữ liệu dạng bảng thì dùng bảng. |
| Một mức bo góc duy nhất cho tất cả (nút, ô nhập, thẻ, hộp thoại đều 12px) | Không có thứ bậc. Xem mục 4.3. |
| Nền gradient, màu tím–xanh, hiệu ứng kính mờ (glassmorphism), glow | Trang trí không mang thông tin. |
| Nền kem + chữ serif + màu đất nung | Công thức "AI editorial" đã quá phổ biến. |
| Nền đen gần như tuyệt đối + một màu neon (xanh acid, cam đỏ) | Công thức "AI dark mode". |
| Emoji làm icon (🚀 ✅ ⚠️ 📊) | Rất rẻ tiền. Dùng bộ icon SVG đồng nhất. |
| Nhãn IN HOA giãn chữ phía trên mỗi tiêu đề (`TỔNG QUAN`, `CHI TIẾT`) | Trang trí, không thêm thông tin. |
| Đánh số `01 / 02 / 03` khi nội dung không phải một chuỗi bước | Chỉ đánh số khi thật sự là quy trình. |
| Làm nổi đúng một từ trong tiêu đề bằng màu hoặc in nghiêng | Dấu hiệu sinh tự động. |
| Thêm `→` vào cuối mọi nút hoặc liên kết | Thừa. |
| Chuỗi meta nối bằng dấu chấm giữa `A · B · C` ở mọi nơi | Dùng cột hoặc nhãn riêng nếu cần. |
| Hiệu ứng hover phóng to, nảy, trượt cho mọi thẻ | Công cụ làm việc không cần. |
| Animation tự chạy lúc vào mỗi màn hình | Xem mục 9. |
| Câu chữ kiểu quảng cáo: "Khám phá sức mạnh…", "Trải nghiệm liền mạch…" | Giao diện nói việc người dùng cần làm. |
| Màn hình chào mừng to đùng với ảnh minh họa vector người cầm laptop | Không cần. |

**Các lỗi khiến giao diện trông "thô" (đã gặp khi chạy thử, cũng cấm):**

| Cấm | Làm đúng |
|---|---|
| Tiêu đề cột căn giữa, có vạch dọc ngăn từng cột | Căn **trái**, không vạch dọc, chỉ đường kẻ ngang mảnh |
| Một cột đường dẫn chiếm gần hết chiều ngang, các cột số bị chèn nhỏ | Chỉ **một** cột co giãn, các cột còn lại vừa nội dung (xem mục 6.0) |
| Mũi tên sắp xếp nằm lơ lửng phía trên chữ tiêu đề | Ẩn chỉ báo sắp xếp mặc định; nếu cần thì đặt cạnh phải chữ |
| Màn hình này có tiêu đề và lề lớn, màn kia dán sát mép | **Mọi màn** dùng chung `PageHeader` và lề trang cố định |
| Hai nút chính trên cùng một màn hình | Một nút chính. Các nút còn lại là nút phụ |
| Nút xóa tô đỏ đặc khi chưa chọn gì, trong khi các nút khác bị mờ | Nút xóa dạng **viền đỏ**, mờ cùng nhóm khi chưa chọn. Đỏ đặc chỉ ở hộp thoại xác nhận |
| Cùng một thông tin hiện hai lần (địa chỉ máy chủ ở sidebar và ở thanh dưới) | Mỗi thông tin chỉ hiện **một** nơi |
| Cột viết tắt khó hiểu: `C / H`, `M / L` | Tách thành cột riêng, tên đầy đủ, số căn phải |
| Bảng trống để trắng hoàn toàn | Dòng chữ trạng thái rỗng ngay trong bảng, kèm gợi ý hành động |
| Dải cảnh báo lặp lại đúng ý của trạng thái rỗng | Chỉ giữ một trong hai |
| Chữ thanh trạng thái dính sát mép cửa sổ | Lề trái phải 12px |

---

## 3. Hướng thẩm mỹ: "Phòng kiểm định mã nguồn"

Lấy cảm hứng từ chính thế giới của đề tài: **diff, trình soạn code, báo cáo lint, bảng điểm kiểm định**.

- **Nền sáng, trung tính, hơi lạnh**, mật độ thông tin vừa phải (không thưa như web landing page).
- **Cột điều hướng bên trái tối màu**, vùng làm việc bên phải sáng. Tương phản này giúp mắt biết đâu là "khung công cụ", đâu là "nội dung".
- **Phông đơn cách (monospace) chỉ dùng cho thứ thật sự là code**: đường dẫn file, số dòng, đoạn mã, mã lỗi. Không dùng cho nhãn thường.
- **Màu có nghĩa**: màu chỉ xuất hiện để nói về **mức nghiêm trọng** và **xếp loại**. Phần còn lại gần như xám xanh.
- **Một điểm nhấn duy nhất**: xếp loại (chữ cái A–F) ở màn hình phân tích. Mọi thứ xung quanh yên lặng.

---

## 4. Token thiết kế

### 4.1 Bảng màu

Dùng đúng các giá trị này, đặt thành hằng số trong `frontend/views/theme.py`. Không tự nghĩ thêm màu.

**Nền và chữ**

| Tên | Hex | Dùng cho |
|---|---|---|
| `window_bg` | `#F3F5F8` | Nền cửa sổ, khoảng giữa các vùng |
| `surface` | `#FFFFFF` | Vùng nội dung, bảng, ô nhập |
| `surface_alt` | `#F5F6F8` | Vùng phụ, nền nút bị vô hiệu |
| `header_bg` | `#FAFBFC` | Nền hàng tiêu đề của bảng |
| `row_hover` | `#F6F8FB` | Hàng bảng khi rê chuột |
| `border` | `#D3D8DF` | Viền ô nhập, nút |
| `border_panel` | `#DDE2E9` | Viền khung chứa bảng, đường kẻ dưới tiêu đề cột |
| `border_soft` | `#EEF0F4` | Đường kẻ ngang giữa các hàng bảng |
| `text` | `#1D232B` | Chữ chính |
| `text_muted` | `#5B6573` | Chữ phụ, chú thích (phải đạt tương phản ≥ 4.5:1 trên nền trắng) |
| `sidebar_bg` | `#222B36` | Cột điều hướng trái |
| `sidebar_text` | `#B9C2CE` | Chữ mục điều hướng thường |
| `sidebar_active_bg` | `#2F3A48` | Mục đang chọn |
| `sidebar_active_text` | `#FFFFFF` | Chữ mục đang chọn |

**Điểm nhấn thao tác (chỉ một màu)**

| Tên | Hex | Dùng cho |
|---|---|---|
| `accent` | `#1F5FA8` | Nút chính, liên kết, viền focus, mục đang chọn |
| `accent_hover` | `#194F8C` | Hover nút chính |
| `accent_soft` | `#E8F0FA` | Nền dòng đang chọn trong bảng |

**Mức nghiêm trọng (dùng nhất quán ở bảng, biểu đồ, huy hiệu)**

| Mức | Hex | Ghi chú |
|---|---|---|
| Critical | `#B42318` | Đỏ sẫm |
| High | `#D9622B` | Cam |
| Medium | `#C79A0A` | Vàng đậm (không dùng vàng chói) |
| Low | `#5E7A94` | Xám xanh, cố ý **không** gây chú ý |

**Xếp loại (dùng cho chữ cái điểm)**

| Loại | Hex |
|---|---|
| A | `#1E7A4C` |
| B | `#4C8A2E` |
| C | `#B38A00` |
| D | `#D9622B` |
| F | `#B42318` |

**Trạng thái lỗi (status)**: dùng **chấm tròn nhỏ + chữ**, không tô cả nền ô.

| Trạng thái | Chấm |
|---|---|
| Chưa sửa | `#B42318` |
| Đang sửa | `#C79A0A` |
| Đã sửa | `#1E7A4C` |
| Báo sai | `#8A94A1` |

**Quy tắc màu**
- Không bao giờ truyền đạt thông tin chỉ bằng màu. Mức nghiêm trọng luôn kèm **chữ** ("Cao", "Trung bình"), trạng thái luôn kèm chữ.
- Không dùng thuần `#000000` cho chữ, dùng `text`.
- Không gradient. Không bóng đổ cho thành phần nằm trong trang. Chỉ hộp thoại nổi mới có bóng nhẹ.

### 4.2 Phông chữ

| Vai trò | Phông | Dự phòng |
|---|---|---|
| Giao diện (chữ, nút, bảng) | **Segoe UI** (Windows) / **SF Pro** (macOS) / **Noto Sans** (Linux), dùng phông hệ thống để giao diện giống ứng dụng thật | `QFont()` mặc định |
| Code, đường dẫn, số dòng | **JetBrains Mono** (đóng gói kèm app) | `Cascadia Mono`, `Consolas`, `monospace` |

- Đóng gói file `.ttf` của JetBrains Mono vào `frontend/assets/fonts/` và nạp bằng `QFontDatabase.addApplicationFont()`. Phải hiển thị tốt tiếng Việt có dấu.
- **Không được crash khi thiếu file `.ttf`.** Nếu file chưa có hoặc nạp lỗi (`addApplicationFont` trả về `-1`), tự động dùng phông đơn cách có sẵn trên máy theo thứ tự: `Cascadia Mono` → `Consolas` → `Courier New` → phông monospace của hệ thống. Ví dụ:

```python
from pathlib import Path
from PyQt6.QtGui import QFont, QFontDatabase

def lay_font_code(co: int = 12) -> QFont:
    """Nạp JetBrains Mono nếu có, không có thì dùng phông đơn cách của máy."""
    ttf = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"
    if ttf.exists() and QFontDatabase.addApplicationFont(str(ttf)) != -1:
        ten = "JetBrains Mono"
    else:
        co_san = set(QFontDatabase.families())
        ten = next((f for f in ("Cascadia Mono", "Consolas", "Courier New") if f in co_san), "")
    f = QFont(ten) if ten else QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    f.setPointSize(co)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f
```
- Chỉ **hai** họ phông. Không thêm phông trang trí.

**Thang cỡ chữ** (px)

| Dùng cho | Cỡ | Đậm |
|---|---|---|
| Chú thích, tiêu đề cột bảng, đường dẫn trong bảng | 12 | thường (tiêu đề cột: 600) |
| Nội dung, bảng, nút, ô nhập | 14 | thường |
| Tiêu đề vùng | 16 | semibold (600) |
| Tiêu đề màn hình | 22 | semibold |
| Số điểm tổng | 40 | semibold |
| Chữ cái xếp loại | 72 | bold |

- Nhãn dùng **chữ thường kiểu câu** ("Độ phức tạp"), không in hoa toàn bộ, không giãn chữ. Áp dụng cả cho logo trên sidebar ("Code Quality") và nhãn "Máy chủ".
- Số trong bảng **căn phải** và dùng chữ số đều chiều rộng (tabular) nếu phông hỗ trợ.

### 4.3 Hình khối: bo góc và khoảng cách có thứ bậc

| Thành phần | Bo góc |
|---|---|
| Khung chứa bảng / vùng nội dung (`Panel`) | 8px |
| Nút, ô nhập, combobox | 6px |
| Huy hiệu mức nghiêm trọng (badge), nhãn nguồn | 4px |
| Hộp thoại, menu nổi | 12px |
| Chấm trạng thái | tròn |

Bảng nằm **bên trong** một `Panel` (nền trắng, viền 1px `border_panel`, bo 8px), không để bảng trần trên nền xám.

**Khoảng cách**: bội số của 4 (4, 8, 12, 16, 24, 32).

| Vị trí | Giá trị |
|---|---|
| Lề trang (trái, trên, phải, dưới) | 32, 28, 32, 24 |
| Khoảng giữa các khối trong trang | 16 |
| Chiều cao hàng bảng | 40 |
| Chiều cao hàng tiêu đề cột | 38 |
| Đệm ngang trong ô bảng | 12 |
| Chiều cao nút và ô nhập | 34 |
| Đệm ngang nút | 16 |

**Viền thay cho bóng**: ngăn cách vùng bằng đường kẻ 1px, không dùng bóng.

---

## 5. Bố cục khung chính

Cửa sổ tối thiểu **1100×680**, cho phép phóng to. Lưu kích thước và vị trí cửa sổ lần trước (`QSettings`).

```
┌──────────┬───────────────────────────────────────────────────────┐
│          │  Tiêu đề màn hình                    [Hành động chính]│
│ Dự án    ├───────────────────────────────────────────────────────┤
│ Phân tích│                                                       │
│ Lỗi      │               Vùng làm việc                           │
│ Lịch sử  │                                                       │
│          │                                                       │
│ ──────── │                                                       │
│ Cài đặt  │                                                       │
├──────────┴───────────────────────────────────────────────────────┤
│ ● Đã kết nối 127.0.0.1:8000                 Dự án: Flask         │
└──────────────────────────────────────────────────────────────────┘
```

- **Cột trái** rộng cố định 188px: icon + chữ, mục "Cài đặt" tách xuống đáy bằng một đường kẻ. Không thu gọn thành chỉ icon. Tên các mục: **Dự án, Phân tích, Lỗi phát hiện, Lịch sử quét, Cài đặt**.
- **Đầu cột trái**: logo là một ô vuông 24px màu `accent` (bo 6px) kèm chữ "Code Quality" kiểu câu, cỡ 15 đậm. **Không** dùng chữ in hoa.
- **Thẻ "Máy chủ" ở đáy cột trái** (phía trên mục Cài đặt) là nơi **duy nhất** hiển thị tình trạng kết nối: chấm xanh/đỏ + chữ "Đã kết nối" / "Mất kết nối" + `127.0.0.1:8000`. Nhãn "Máy chủ" viết kiểu câu, cỡ 12.
- **Thanh trạng thái dưới cùng** (cao 28px, lề trái phải 12px) **không lặp lại địa chỉ máy chủ**. Bên trái: thông báo tạm thời ("Đã lưu ghi chú", tự mất sau 3 giây). Bên phải: "Dự án: tên" đang chọn.
- Tiêu đề màn hình căn **trái**. Nút hành động chính của màn hình nằm **góc phải trên**, chỉ có **một** nút chính (màu `accent`) trên mỗi màn hình.
- Không có thanh tiêu đề tự vẽ. Dùng khung cửa sổ gốc của hệ điều hành.

---

## 6. Thiết kế từng màn hình

### 6.0 Quy tắc chung cho mọi màn hình và mọi bảng

**Khung trang (widget `PageHeader` + `Panel`)**

```
 (lề 32 trái/phải, 28 trên)
 Tiêu đề màn hình (22, semibold)                   [Nút phụ] [Nút chính]
 Dòng phụ đề (12, text_muted), có thể bỏ
                                   (khoảng cách 16)
 Bộ lọc / tìm kiếm (một hàng, cao 34)
                                   (khoảng cách 16)
 ┌─ Panel (nền trắng, viền border_panel, bo 8) ───────────────────────┐
 │ Tên cột (12, 600)  │ ...                          │ Số (căn phải)  │
 │────────────────────────────────────────────────────────────────────│
 │ Hàng 40px                                                          │
 └────────────────────────────────────────────────────────────────────┘
                                   (khoảng cách 16)
 Hàng nút thao tác theo dòng đang chọn (bên trái)      Tổng số: N (bên phải, 12)
```

- **Mọi màn đều có `PageHeader`**: Dự án, Phân tích, Lỗi phát hiện, Lịch sử quét, Cài đặt. Không có màn nào dán nội dung sát mép.
- Bộ lọc nằm **dưới** tiêu đề, không nằm chung hàng với tiêu đề.

**Quy tắc bảng (áp dụng cho mọi `QTableView`)**

- Dùng hàm `chuan_hoa_bang()` ở mục 11 cho **mọi** bảng, không tự cấu hình lẻ từng bảng.
- Tiêu đề cột và nội dung chữ **căn trái**; **cột số căn phải** (cả tiêu đề cột đó).
- **Chỉ một cột co giãn** (cột nội dung dài nhất: đường dẫn, mô tả, thời gian...). Các cột còn lại **vừa nội dung** với độ rộng tối thiểu 80px.
- Không vạch dọc giữa các cột, không xen kẽ màu hàng, không viền ô. Chỉ đường kẻ ngang `border_soft` giữa các hàng.
- Chữ dài (đường dẫn, tên file) **cắt ở giữa** bằng "…", tên đầy đủ hiện trong tooltip.
- Không hiện mũi tên sắp xếp lơ lửng. Cho phép bấm tiêu đề cột để sắp xếp, hiển thị chỉ báo bằng chữ nhỏ cạnh phải tên cột chỉ khi cột đó đang được sắp xếp.
- Bảng trống: hiện câu trạng thái rỗng **ngay giữa vùng bảng** (mục 8), không để trắng.

**Quy tắc nút**

| Vai trò | Kiểu | Ví dụ |
|---|---|---|
| Chính (tối đa một mỗi màn) | Nền `accent`, chữ trắng | Thêm dự án, Phân tích lại |
| Phụ | Nền trắng, viền `border` | Làm mới, Sửa, Hủy |
| Nguy hiểm | **Viền đỏ nhạt, chữ đỏ, nền trong suốt**; đỏ đặc **chỉ** trong hộp thoại xác nhận | Xóa dự án, Xóa phiên quét |
| Vô hiệu | Chữ và viền xám nhạt, nền `surface_alt` (kể cả nút nguy hiểm) | Khi chưa chọn dòng |

- Nút thao tác theo dòng (Phân tích, Sửa, Xóa) nằm dưới bảng, **cùng vô hiệu khi chưa chọn dòng**, cùng bật khi đã chọn. Khi đã chọn dòng, nút hành động hợp lý nhất chuyển thành nút chính.

### 6.1 Dự án (CRUD)

```
Dự án                                             [Làm mới] [Thêm dự án]
Tìm theo tên hoặc đường dẫn…                         Nguồn [Tất cả ▾]
┌────────────────────────────────────────────────────────────────────┐
│ Tên dự án     Nguồn    Đường dẫn / liên kết    Lần phân tích cuối  Điểm│
├────────────────────────────────────────────────────────────────────┤
│ flask         GitHub   github.com/pallets/…    09/11/2026         82 B │
│ bad_project   Thư mục  D:\Python\…\bad_project  Chưa phân tích     — │
└────────────────────────────────────────────────────────────────────┘
[Phân tích] [Sửa] [Xóa dự án]                              Tổng số: 2 dự án
```

- Cột co giãn là **Đường dẫn / liên kết** (chữ mono 12px, `text_muted`, cắt giữa). Tên dự án rộng khoảng 220px. Các cột còn lại vừa nội dung.
- Cột **Nguồn** hiện nhãn nhỏ (bo 4px, nền `surface_alt`): "Thư mục", "GitHub".
- Cột **Điểm** căn phải: số kèm chữ xếp loại **có màu theo bảng xếp loại**; chưa phân tích thì hiện "—" màu xám nhạt. Cột "Lần phân tích cuối" chưa có thì hiện "Chưa phân tích" màu `text_muted`.
- Thêm/Sửa mở **hộp thoại** với các trường: Tên, Mô tả, Loại nguồn (GitHub / Thư mục), Đường dẫn hoặc liên kết. Nút: **Lưu** (chính), **Hủy**.
- Xóa phải hỏi xác nhận, nêu rõ **hậu quả**: "Xóa dự án flask và 12 lần phân tích của nó? Không hoàn tác được." Nút: **Xóa dự án** (đỏ đặc, chỉ ở hộp thoại này), **Giữ lại**.
- Nhấp đúp một dòng để mở màn hình Phân tích của dự án đó.
- Bảng trống: "Chưa có dự án nào. Thêm dự án đầu tiên để bắt đầu phân tích." + nút **Thêm dự án**.

### 6.2 Phân tích (màn hình quan trọng nhất)

Đây là nơi duy nhất được phép "nổi bật".

```
flask                                              [Phân tích lại]
Phân tích lúc 09/11/2026 14:32 · 214 file · 18.420 dòng
┌───────────────────┬──────────────────────────────────────────┐
│                   │  Độ phức tạp & bảo trì ████████░░  72    │
│        B          │  An toàn bảo mật       █████████░  88    │
│      82 / 100     │  Quy chuẩn mã nguồn    ██████░░░░  61    │
│                   │  Sức khỏe & Git        ███████░░░  70    │
│                   │  Thư viện & CVE        ████████░░  79    │
├───────────────────┴──────────────────────────────────────────┤
│ [Tổng quan] [Theo file] [Biểu đồ]                            │
│ ...                                                          │
└──────────────────────────────────────────────────────────────┘
```

**Năm tiêu chí chấm điểm (phải khớp đúng backend, không tự đổi tên):**

| Khóa (`key` trong JSON) | Tên hiển thị | Nguồn | Trọng số mặc định |
|---|---|---|---|
| `complexity` | Độ phức tạp & bảo trì | Radon (CC và MI) | 0,25 |
| `security` | An toàn bảo mật | Bandit | 0,25 |
| `pylint` | Quy chuẩn mã nguồn | Pylint score | 0,20 |
| `health` | Sức khỏe & Git | README, LICENSE, tests, git log | 0,15 |
| `dependency` | Thư viện & CVE | pip-audit | 0,15 |

Tên hiển thị lấy từ một bảng ánh xạ duy nhất trong `theme.py` (`TEN_TIEU_CHI = {"complexity": "Độ phức tạp & bảo trì", ...}`). Trọng số và điểm luôn lấy từ dữ liệu server trả về, không viết cứng trong view.

- **Chữ cái xếp loại cỡ 72, màu theo bảng xếp loại**, là yếu tố đáng nhớ duy nhất. Số điểm cỡ 40 ngay dưới.
- Điểm từng tiêu chí là **thanh ngang mảnh (6px)** kèm số, **không** dùng vòng tròn tiến độ, không dùng đồng hồ đo. Mỗi thanh hiện **trọng số** khi di chuột ("Chiếm 25% điểm tổng").
- Tab bên dưới: **Tổng quan** (các con số chính), **Theo file** (bảng `pandas` hiển thị lên `QTableView`, sắp xếp được, mặc định file xấu nhất lên đầu), **Biểu đồ**.
- Khi đang phân tích: thay vùng điểm bằng thanh tiến độ **có tên bước** ("Đang chạy bandit…", "Đang tính độ phức tạp…"), có nút **Hủy**. Không dùng vòng xoay vô định không nói gì.

**Khi chưa chọn dự án hoặc dự án chưa được phân tích** (trạng thái hay gặp nhất, phải đẹp):

- Tiêu đề màn hình là "Phân tích" (không phải "Chưa chọn dự án"), phụ đề nêu tên dự án nếu có.
- **Không có nút chính ở góc phải trên** và **không có dải cảnh báo**. Chỉ còn trạng thái rỗng ở giữa vùng làm việc, nằm trong một `Panel`:
  - Chưa chọn dự án: icon (đủ đậm để thấy rõ, `text_muted`), tiêu đề "Chưa chọn dự án", mô tả một dòng "Chọn một dự án ở màn hình Dự án để xem kết quả phân tích.", nút chính **Chọn dự án** (chuyển sang màn Dự án).
  - Đã chọn nhưng chưa phân tích: tiêu đề "Dự án này chưa được phân tích", mô tả "Phân tích sẽ đo độ phức tạp, quy chuẩn mã nguồn, bảo mật, thư viện và sức khỏe dự án.", nút chính **Bắt đầu phân tích** (nút duy nhất kích hoạt phân tích trong trạng thái này).

### 6.3 Lỗi phát hiện (issues)

```
Lỗi phát hiện                                              [Thêm lỗi]
Phiên [09/11/2026 14:32 ▾]  Mức [Tất cả ▾]  Trạng thái [Tất cả ▾]  Công cụ [Tất cả ▾]
Tìm theo tệp, mã kiểm thử hoặc mô tả…  (Ctrl+F)
┌─────────────────────────────────────────────────────────────────────┐
│ Tệp : dòng            Mức độ     Trạng thái    Công cụ   Mô tả tóm tắt│
│ app/db.py:42          Cao        ● Chưa sửa    bandit    Nguy cơ SQL…  │
│ app/utils.py:118      Trung bình ● Đang sửa    pylint    Hàm quá dài…  │
├══════════════ thanh kéo QSplitter ═════════════════════════════════┤
│ Chi tiết                                                            │
│ app/db.py:42                                                        │
│ B608: Có nguy cơ SQL injection do nối chuỗi vào câu truy vấn.       │
│  41 │ cur = conn.cursor()                                           │
│  42 │ cur.execute("SELECT * FROM u WHERE id=" + uid)                │
│ Trạng thái [Chưa sửa ▾]  Ghi chú [..........]   [Lưu ghi chú]       │
└─────────────────────────────────────────────────────────────────────┘
```

- Có `PageHeader` như mọi màn. Bộ lọc nằm **dưới tiêu đề**, tìm kiếm là một hàng riêng hoặc gộp cuối hàng bộ lọc, không dồn sát mép.
- Bố cục **bảng trên, chi tiết dưới** (`QSplitter`, tay nắm 8px trong suốt, nhớ vị trí chia). Cả hai nửa nằm trong `Panel`.
- Cột co giãn là **Mô tả tóm tắt**. Cột **Tệp : dòng** và đoạn code dùng phông mono.
- Mức nghiêm trọng hiển thị bằng **huy hiệu chữ** nhỏ (nền nhạt, chữ đậm màu tương ứng, bo 4px), không tô cả hàng. Trạng thái là **chấm màu + chữ**.
- Đổi trạng thái ngay trong khung chi tiết hoặc chuột phải. Hỗ trợ chọn nhiều dòng để đổi hàng loạt và xóa.
- Phím tắt: `Delete` xóa (có xác nhận), `Ctrl+F` tìm, `Enter` mở chi tiết.
- Bảng trống: "Chưa có lỗi nào. Chạy phân tích để thấy kết quả." (hoặc "Không có lỗi khớp bộ lọc." khi đang lọc). Khung chi tiết khi chưa chọn dòng: "Chọn một dòng lỗi để xem chi tiết và khuyến nghị sửa chữa." căn giữa, `text_muted`.

### 6.4 Lịch sử quét

```
Lịch sử quét                         [So sánh 2 phiên] [Xem chi tiết lỗi] [Xóa phiên quét]
┌─────────────────────────────────────────────────────────────────────┐
│ Mã   Thời gian              Điểm  Xếp loại  Tổng lỗi  ●Nghiêm trọng ●Cao ●Trung bình ●Thấp│
│ #12  09/11/2026 14:32        82      B          31         0       3      14       14 │
└─────────────────────────────────────────────────────────────────────┘
Tổng số phiên: 12
```

- **Bỏ các cột gộp** "Nghiêm trọng (C / H)" và "Khác (M / L)". Thay bằng **bốn cột số căn phải, hẹp**: **Nghiêm trọng, Cao, Trung bình, Thấp**, mỗi tiêu đề có chấm màu nhỏ đúng màu mức đó. Số 0 hiển thị màu `text_muted` để số khác 0 nổi lên.
- Cột co giãn là **Thời gian**. Các cột còn lại vừa nội dung. Điểm và Tổng lỗi căn phải, Xếp loại là chữ cái có màu.
- Ba nút trên cùng: "So sánh 2 phiên" và "Xem chi tiết lỗi" là nút phụ, **vô hiệu cho đến khi chọn đủ dòng** (2 dòng cho so sánh, 1 dòng cho xem chi tiết); "Xóa phiên quét" là nút nguy hiểm dạng viền đỏ. **Không có nút chính** trên màn này.
- Chọn 2 dòng → **So sánh** mở hộp thoại hiển thị điểm từng tiêu chí hai lần cạnh nhau, kèm **mũi tên tăng/giảm có số** ("+6", "−3"), màu xanh/đỏ nhạt kèm dấu +/−.
- Biểu đồ đường điểm theo thời gian đặt phía trên bảng khi có từ 2 phiên trở lên.
- Bảng trống: "Chưa có phiên quét nào. Phân tích một dự án để lưu lịch sử." Xóa lịch sử: xác nhận nêu số phiên sẽ bị xóa.

### 6.5 Cài đặt

- Một cột form đơn, căn trái, nhóm theo tiêu đề vùng (Kết nối server, Trọng số chấm điểm).
- Trọng số dùng các ô số (`QDoubleSpinBox`) hoặc thanh trượt kèm ô số. **Tổng phải bằng 1**: hiển thị tổng hiện tại bên cạnh, nút **Lưu** bị vô hiệu cho đến khi tổng đúng, kèm dòng giải thích lý do ("Tổng trọng số đang là 1,10. Cần bằng 1,00.").
- Nút **Khôi phục mặc định** (phụ) và **Lưu** (chính).

---

## 7. Biểu đồ matplotlib

Biểu đồ phải trông **thuộc về ứng dụng**, không phải ảnh dán vào. Đặt cấu hình chung trong `frontend/charts/style.py` và gọi một lần khi khởi động:

```python
import matplotlib as mpl

def ap_dung_style() -> None:
    mpl.rcParams.update({
        "figure.facecolor": "#FFFFFF",
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#D3D8DF",
        "axes.labelcolor": "#5B6573",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": "#E4E7EC",
        "grid.linewidth": 0.8,
        "xtick.color": "#5B6573",
        "ytick.color": "#5B6573",
        "font.family": "sans-serif",
        "font.sans-serif": ["Segoe UI", "SF Pro Text", "Noto Sans", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "legend.frameon": False,
    })
```

Quy tắc:

- **Màu theo ý nghĩa**: biểu đồ tròn/cột theo mức nghiêm trọng dùng đúng 4 màu ở mục 4.1, thứ tự Critical → Low. Biểu đồ không nói về mức nghiêm trọng thì dùng **một màu** (`accent`) hoặc xám xanh, không dùng cầu vồng mặc định của matplotlib.
- Tiêu đề biểu đồ **căn trái** và là câu nói điều biểu đồ cho thấy: "5 file phức tạp nhất", "Số lỗi theo mức nghiêm trọng".
- **Gắn nhãn số trực tiếp** lên cột và lát cắt thay vì bắt người xem dò theo trục. Bỏ chú giải nếu đã có nhãn trực tiếp.
- Cột ngang cho tên file dài (tên file mới đọc được), cắt giữa bằng "…" nếu quá dài, tên đầy đủ hiện khi di chuột.
- Biểu đồ tròn: **tối đa 4 lát** (đúng 4 mức nghiêm trọng), bắt đầu từ 12 giờ, kèm số lượng và %. Có thể thay bằng cột ngang xếp chồng nếu rõ hơn.
- **Radar** (điểm tiêu chí): đa giác một màu `accent` tô nhạt (alpha 0.15), nhãn trục ghi rõ điểm. Trục cố định 0–100.
- Đường điểm theo thời gian: một đường `accent`, chấm tròn nhỏ ở mỗi lần quét, nhãn điểm ở điểm đầu và cuối.
- Tỷ lệ khung hình ổn định, dùng `constrained_layout=True` để không bị cắt nhãn. Thay đổi kích thước cửa sổ phải vẽ lại đúng.
- Khi không có dữ liệu, hiển thị chữ thông báo ở giữa vùng biểu đồ, không vẽ trục trống.
- Có nút **Lưu ảnh** (PNG) cho mỗi biểu đồ.

---

## 8. Chữ trong giao diện (tiếng Việt)

Chữ là một phần của thiết kế. Quy tắc:

- **Câu thường, động từ rõ ràng, ngắn gọn.** Không viết hoa từng chữ cái đầu.
- **Nút nói đúng việc sẽ xảy ra**: "Lưu thay đổi", "Thêm dự án", "Phân tích lại", "Xóa dự án". Không dùng "Submit", "OK" trần, "Xác nhận" chung chung.
- **Một hành động giữ một tên xuyên suốt**: nút "Xóa dự án" thì thông báo sau đó là "Đã xóa dự án flask", không đổi thành "Gỡ bỏ".
- Thuật ngữ nhất quán:

| Dùng | Không dùng lẫn |
|---|---|
| Phân tích | Quét / Scan / Kiểm tra |
| Lỗi (cho mọi phát hiện) | Vấn đề / Cảnh báo / Issue |
| Mức nghiêm trọng: Nghiêm trọng, Cao, Trung bình, Thấp | Critical/High… (chỉ dùng tiếng Anh trong dữ liệu gốc của công cụ) |
| Trạng thái: Chưa sửa, Đang sửa, Đã sửa, Báo sai | |
| Điểm, Xếp loại | Score, Grade |

- **Thông báo lỗi nói rõ chuyện gì xảy ra và cách xử lý**, không xin lỗi, không mơ hồ:
  - Tốt: "Không kết nối được tới máy chủ 127.0.0.1:8000. Kiểm tra máy chủ đã chạy chưa, rồi bấm Thử lại."
  - Xấu: "Rất tiếc, đã có lỗi xảy ra! Vui lòng thử lại sau."
- **Trạng thái rỗng là lời mời hành động**:
  - Danh sách dự án rỗng: "Chưa có dự án nào. Thêm dự án đầu tiên để bắt đầu phân tích." + nút **Thêm dự án**.
  - Không có lỗi nào: "Không phát hiện lỗi nào ở lần phân tích này."
- Khi thiếu mạng cho `pip-audit`: "Không kiểm tra được thư viện có CVE vì không có Internet. Điểm tiêu chí này được tính không có phần thư viện." (không giấu, không làm điểm sai lặng lẽ).
- Tên trạng thái rỗng gồm **tiêu đề ngắn + một dòng mô tả + (nếu có hành động) một nút**. Không viết hai đoạn.
- Không dùng dấu chấm than. Không dùng biểu tượng cảm xúc.

---

## 9. Chuyển động

- **Không có animation tự chạy** khi mở màn hình hay khi tải bảng.
- Chỉ dùng chuyển động **đáp lại hành động người dùng** và cho thấy cái gì thay đổi:
  - Thanh tiến độ phân tích chạy theo bước thật.
  - Thanh điểm tiêu chí chạy từ 0 đến giá trị **một lần** sau khi có kết quả (≤ 400ms), đây là khoảnh khắc chuyển động duy nhất được phép nhấn.
  - Hộp thoại hiện ra/đóng đi (≤ 120ms, mờ dần).
- Không hover phóng to, không hiệu ứng nảy.

---

## 10. Trải nghiệm làm việc (UX)

**Không bao giờ để GUI đơ**
- Mọi gọi mạng chạy trong `QThread` (thư mục `workers/`). Tín hiệu `progress`, `finished`, `failed` cập nhật giao diện.
- Trong lúc chờ, vô hiệu đúng các nút liên quan, **không khóa cả cửa sổ**.

**Mọi trạng thái đều được thiết kế**

| Trạng thái | Cách hiển thị |
|---|---|
| Đang tải danh sách | Dòng chữ "Đang tải…" trong vùng bảng, không nhấp nháy |
| Rỗng | Câu mời hành động + nút (mục 8) |
| Lỗi mạng | Dải thông báo trên vùng làm việc, có nút **Thử lại** |
| Mất kết nối giữa chừng | Chấm đỏ ở thanh trạng thái + dải thông báo, các nút gọi server bị vô hiệu |
| Đang phân tích | Mục 6.2 |

**Bàn phím**
- Thứ tự `Tab` hợp lý trong mọi form, ô đầu tiên được focus khi mở hộp thoại.
- `Enter` = hành động chính của hộp thoại, `Esc` = hủy.
- `Ctrl+N` thêm dự án, `F5` làm mới, `Ctrl+1…5` chuyển màn hình.
- Viền **focus nhìn thấy rõ** (2px `accent`), không tắt outline.

**Tránh mất dữ liệu**
- Hành động xóa luôn hỏi xác nhận có nêu hậu quả.
- Không dùng hộp thoại thông báo cho thao tác thành công thông thường; dùng dòng thông báo nhỏ ở thanh trạng thái ("Đã lưu ghi chú") tự mất sau 3 giây.

**Hiệu năng cảm nhận**
- Bảng lớn (hàng nghìn lỗi) dùng `QAbstractTableModel` + `QSortFilterProxyModel`, không tạo `QTableWidgetItem` hàng loạt.

---

## 11. Gợi ý triển khai PyQt6

**Cấu trúc file liên quan (nằm trong `frontend/`)**

```
frontend/
├── assets/
│   ├── fonts/            JetBrains Mono (.ttf)
│   └── icons/            SVG cùng một bộ (nét 1.5px, vuông đầu), đổi màu bằng code
├── views/
│   ├── theme.py          hằng số màu, cỡ chữ, khoảng cách
│   ├── style.qss         stylesheet dùng token ở trên
│   └── widgets/          nút, badge, thanh điểm, bảng dùng lại
└── charts/
    └── style.py          cấu hình matplotlib (mục 7)
```

- **Icon**: dùng một bộ SVG nét đơn giản (ví dụ Lucide hoặc Phosphor, tải về lưu cục bộ, **không** gọi mạng lúc chạy). Cỡ 16px trong bảng và nút, 18px ở cột trái. Một độ dày nét duy nhất.
  - Hiển thị SVG trong PyQt6 cần gói phụ trợ **`PyQt6-Svg`** (thêm vào `frontend/requirements.txt`, cài bằng `pip install PyQt6-Svg`).
  - **Phải có phương án dự phòng, không được crash**: bọc việc nạp icon trong `try/except ImportError`. Nếu thiếu `PyQt6-Svg` hoặc thiếu file icon, dùng icon PNG cùng tên trong `assets/icons/`, hoặc vẽ hình khối đơn giản bằng `QPainter` (dấu cộng, thùng rác, mũi tên...), hoặc hiển thị nút chỉ có chữ. Giao diện luôn dùng được khi không có icon.
- Tạo sẵn widget dùng lại: `SeverityBadge`, `StatusDot`, `ScoreBar`, `GradeLabel`, `EmptyState`, `InlineNotice`. Không lặp lại code giao diện ở nhiều view.

**Khung `style.qss` tham khảo** (thay biến bằng giá trị thật khi nạp)

```css
* { font-family: "Segoe UI", "Noto Sans"; font-size: 14px; color: #1D232B; }

QMainWindow, QDialog { background: #F3F5F8; }

/* Khung chứa bảng / vùng nội dung */
#Panel { background: #FFFFFF; border: 1px solid #DDE2E9; border-radius: 8px; }

/* Tiêu đề màn hình */
#PageTitle { font-size: 22px; font-weight: 600; }
#PageSubtitle { font-size: 12px; color: #5B6573; }

/* Cột điều hướng */
#Sidebar { background: #222B36; }
#Sidebar QPushButton {
    background: transparent; color: #B9C2CE; border: none;
    text-align: left; padding: 0 16px; min-height: 38px; border-radius: 0;
}
#Sidebar QPushButton:hover { background: #2A3441; }
#Sidebar QPushButton:checked { background: #2F3A48; color: #FFFFFF; border-left: 3px solid #1F5FA8; }
#ServerCard { background: #1B232D; border-radius: 6px; }
#ServerCard QLabel { font-size: 12px; color: #B9C2CE; }

/* Nút */
QPushButton {
    background: #FFFFFF; border: 1px solid #D3D8DF; border-radius: 6px;
    min-height: 34px; padding: 0 16px;
}
QPushButton:hover { background: #F5F6F8; }
QPushButton:disabled { color: #A3ACB8; background: #F5F6F8; border-color: #E4E7EC; }
QPushButton:focus { border: 2px solid #1F5FA8; }
QPushButton[role="primary"] { background: #1F5FA8; border-color: #1F5FA8; color: #FFFFFF; }
QPushButton[role="primary"]:hover { background: #194F8C; }
QPushButton[role="primary"]:disabled { background: #A9C0DD; border-color: #A9C0DD; color: #FFFFFF; }
QPushButton[role="danger"] { background: transparent; color: #B42318; border: 1px solid #E7B4AF; }
QPushButton[role="danger"]:hover { background: #FDF1F0; }
QPushButton[role="danger"]:disabled { color: #C9CED6; border-color: #E4E7EC; background: transparent; }
QPushButton[role="danger-solid"] { background: #B42318; border-color: #B42318; color: #FFFFFF; } /* chỉ trong hộp thoại xác nhận */

/* Ô nhập */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #FFFFFF; border: 1px solid #D3D8DF; border-radius: 6px;
    min-height: 34px; padding: 0 10px;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 2px solid #1F5FA8; }

/* Bảng: không vạch dọc, đường kẻ ngang mảnh, nền trong suốt trong Panel */
QTableView { background: transparent; border: none; outline: none; }
QTableView::item { padding: 0 12px; border-bottom: 1px solid #EEF0F4; }
QTableView::item:hover { background: #F6F8FB; }
QTableView::item:selected { background: #E8F0FA; color: #1D232B; }
QHeaderView { background: transparent; }
QHeaderView::section {
    background: #FAFBFC; color: #5B6573; font-size: 12px; font-weight: 600;
    border: none; border-bottom: 1px solid #DDE2E9; padding: 0 12px; min-height: 38px;
}
QHeaderView::section:first { border-top-left-radius: 8px; }
QHeaderView::section:last  { border-top-right-radius: 8px; }

/* Tab */
QTabBar::tab { padding: 8px 14px; color: #5B6573; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #1D232B; border-bottom: 2px solid #1F5FA8; }

/* Thanh kéo chia vùng */
QSplitter::handle:vertical { height: 8px; background: transparent; }

/* Thanh trạng thái */
QStatusBar { background: #FFFFFF; border-top: 1px solid #DDE2E9; color: #5B6573; font-size: 12px; min-height: 28px; }
QStatusBar::item { border: none; }
```

**Hàm chuẩn hóa bảng** (đặt trong `frontend/views/widgets/table_utils.py`, gọi cho **mọi** `QTableView`; `cot_gian` là chỉ số cột duy nhất co giãn, `cot_so` là danh sách cột số căn phải):

```python
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

def chuan_hoa_bang(bang: QTableView, cot_gian: int, cot_so: tuple[int, ...] = ()) -> None:
    """Một cột co giãn, các cột còn lại vừa nội dung; căn trái; hàng cao 40px."""
    h = bang.horizontalHeader()
    h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    h.setHighlightSections(False)
    h.setSortIndicatorShown(False)          # không hiện mũi tên lơ lửng
    h.setMinimumSectionSize(80)
    h.setStretchLastSection(False)
    h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    h.setSectionResizeMode(cot_gian, QHeaderView.ResizeMode.Stretch)
    v = bang.verticalHeader()
    v.setVisible(False)
    v.setDefaultSectionSize(40)
    bang.setShowGrid(False)
    bang.setAlternatingRowColors(False)
    bang.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    bang.setTextElideMode(Qt.TextElideMode.ElideMiddle)
    bang.setWordWrap(False)
    bang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    bang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    bang.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    # Cột số: căn phải phải thực hiện ở model (TextAlignmentRole) và ở tiêu đề:
    #   headerData(..., Qt.ItemDataRole.TextAlignmentRole) trả về AlignRight | AlignVCenter cho các cột trong cot_so.
```

**Widget dùng lại** (trong `frontend/views/widgets/`), mỗi cái một file, không lặp code ở view:

| Widget | Việc |
|---|---|
| `PageHeader(tieu_de, phu_de="")` | Tiêu đề màn hình + phụ đề + vùng chứa nút bên phải (`them_nut_phai()`) |
| `Panel` | `QFrame` có `objectName("Panel")`, lề trong 0, dùng bọc bảng |
| `EmptyState(icon, tieu_de, mo_ta, ten_nut=None)` | Trạng thái rỗng, phát tín hiệu `nut_clicked` |
| `SeverityBadge`, `StatusDot`, `ScoreBar`, `GradeLabel`, `InlineNotice` | Như mô tả ở các mục trên |

- Dùng thuộc tính động `role="primary"` / `"danger"` thay vì tạo nhiều lớp nút. Mỗi màn hình chỉ **một** nút `primary`.
- Cần có `QSplitter` giữa bảng và chi tiết, kéo được, nhớ vị trí chia.

---

## 12. Chế độ tối

**Không bắt buộc cho phiên bản đầu.** Nếu làm, đặt toàn bộ màu trong `theme.py` thành hai bộ token (sáng/tối), không viết cứng hex trong từng view. Chế độ tối không được là "nền đen + màu neon": dùng nền xám xanh đậm (khoảng `#1B222B`), giữ nguyên màu mức nghiêm trọng đã làm dịu độ bão hòa.

---

## 13. Danh sách tự kiểm tra trước khi nộp một view

Đánh dấu từng mục. Còn mục chưa đạt thì sửa trước.

- [ ] Màn hình có **đúng một** nút chính và một điểm nhấn thị giác.
- [ ] Không có thẻ bo góc xếp thành lưới. Dữ liệu dạng bảng đang dùng bảng.
- [ ] Bo góc có thứ bậc (bảng 0, nút/ô nhập 4, hộp thoại 8), không phải một giá trị cho tất cả.
- [ ] Không gradient, không bóng đổ trong trang, không emoji, không icon lạ phong cách.
- [ ] Màu chỉ dùng cho mức nghiêm trọng, xếp loại, trạng thái và điểm nhấn thao tác. Mọi thông tin màu đều có kèm chữ.
- [ ] Chỉ monospace cho code, đường dẫn, số dòng.
- [ ] Không có nhãn in hoa giãn chữ, không đánh số vô cớ, không dấu `→` thừa.
- [ ] Đã thiết kế các trạng thái: đang tải, rỗng, lỗi, mất kết nối.
- [ ] Mọi gọi mạng chạy trong `QThread`, cửa sổ không đơ.
- [ ] Xóa có xác nhận nêu hậu quả. Thông báo lỗi nói rõ cách xử lý.
- [ ] Dùng được bằng bàn phím, viền focus nhìn thấy.
- [ ] Biểu đồ dùng chung `style.py`, tiêu đề căn trái, nhãn số trực tiếp, màu đúng bảng.
- [ ] Thuật ngữ nhất quán với bảng ở mục 8.
- [ ] Chữ rõ khi phóng lên 125% và cửa sổ ở kích thước tối thiểu 1100×680 không bị cắt.
- [ ] Mọi màn có `PageHeader`, lề trang 32/28/32/24, khối cách nhau 16.
- [ ] Mọi bảng đi qua `chuan_hoa_bang()`: tiêu đề căn trái, không vạch dọc, đúng **một** cột co giãn, cột số căn phải.
- [ ] Bảng nằm trong `Panel` bo 8px; hàng cao 40, tiêu đề cột cao 38.
- [ ] Nút xóa là viền đỏ, mờ cùng nhóm khi chưa chọn dòng; đỏ đặc chỉ ở hộp thoại xác nhận.
- [ ] Không có thông tin hiện hai lần (địa chỉ máy chủ chỉ ở thẻ Máy chủ trên sidebar).
- [ ] Không còn chữ in hoa ở logo hoặc nhãn; không còn cột viết tắt kiểu `C / H`.
- [ ] Bảng trống và vùng chi tiết chưa chọn đều có câu trạng thái rỗng.
- [ ] Hỏi bản thân: *"Nếu bỏ một thứ trang trí đi thì giao diện có tệ hơn không?"* Nếu không, bỏ nó.

---

## 14. Cách yêu cầu AI viết giao diện theo file này

Khi dán file này cho AI, luôn gửi kèm **ảnh chụp màn hình giao diện hiện tại** (AI không tự nhìn thấy app), và dặn nó:

> Đọc SKILLS.md. Bố cục và chức năng giữ nguyên. Chỉ sửa giao diện theo file. Mỗi lượt xong một nhóm file, cuối lượt liệt kê file đã sửa và tự kiểm tra theo mục 13, nói rõ mục nào chưa đạt.

**Thứ tự giao việc cho đợt "chỉnh giao diện" (mỗi lượt chạy thử xong mới sang lượt sau):**

1. **Nền tảng:** `theme.py`, `style.qss`, `charts/style.py` theo token và QSS ở mục 4 và 11.
2. **Widget dùng chung:** `table_utils.py` (`chuan_hoa_bang`), `PageHeader`, `Panel`, `EmptyState`, `SeverityBadge`, `StatusDot`, `ScoreBar`, `GradeLabel`, `InlineNotice`.
3. **Sidebar và thanh trạng thái:** theo mục 5 (logo, thẻ Máy chủ, thanh dưới không lặp địa chỉ).
4. **Từng màn hình**, theo thứ tự: `project_view.py` → `analysis_view.py` → `issues_view.py` → `history_view.py` → `settings_view.py`.
5. **Rà soát cuối:** chạy app, kiểm tra từng màn theo mục 13, chụp lại và so sánh.

**Thông số kết nối thống nhất với backend:** `SERVER_HOST=127.0.0.1`, `SERVER_PORT=8000`, đặt trong `frontend/config.py`. Mọi chỗ hiển thị địa chỉ server trên giao diện phải đọc từ file này.
