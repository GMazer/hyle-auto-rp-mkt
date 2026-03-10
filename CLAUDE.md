# Hyle Auto Report MKT — Project Constitution

> **Hyle Auto Report MKT** là Telegram Bot tự động tổng hợp báo cáo chi phí quảng cáo Facebook Ads.
> User gửi file Excel → Bot xử lý → Điền Google Sheets → Trả kết quả tóm tắt + link.
> Đọc file này đầu tiên trước khi làm bất kỳ task nào.

## Companion Documents

| File | Nội dung |
|------|----------|
| [AGENTS.md](AGENTS.md) | Agent personas, guardrails, interaction rules |
| [Project Structure.md](Project%20Structure.md) | Cấu trúc thư mục và giải thích modules |
| [AGENT_PROMPT.md](AGENT_PROMPT.md) | Startup prompt cho AI agent |

---

## Project Identity

| Field | Value |
|-------|-------|
| **Name** | Hyle Auto Report MKT |
| **Type** | Telegram Bot — Marketing Report Automation |
| **Language** | Python 3.11+ |
| **Bot Framework** | `python-telegram-bot` v21+ (async) |
| **Excel Parser** | `openpyxl` |
| **Google Sheets** | `gspread` + `google-auth` (Service Account) |
| **Config** | `python-dotenv` (`.env` file) |

---

## System Architecture

```
User (Telegram) → Bot nhận file .xlsx
                → Excel Parser (normalize schema)
                → Data Processor (aggregate metrics)
                → Google Sheets Writer (điền data)
                → Bot reply: summary + nút link Sheets
```

---

## Data Schema

### Input: File báo cáo Facebook Ads (xuất từ Ads Manager)

Các cột **bắt buộc** (tìm theo tên header, không theo index):

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| Tên chiến dịch | string | Tên campaign quảng cáo |
| Tên Trang | string | Fanpage chạy ads (VD: "Mavo Sportwear") |
| Số tiền đã chi tiêu (VND) | number | Tổng spend |
| CPM (Chi phí trên mỗi 1.000 lượt hiển thị) | number | Cost per mille |
| Chi phí trên mỗi kết quả | number | Cost per result |
| Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn | number | Giá mỗi message |
| ROAS kết quả | number | Return on ad spend |
| Bắt đầu báo cáo | date | Ngày bắt đầu report |
| Kết thúc báo cáo | date | Ngày kết thúc report |

> **Lưu ý:** File có thể có 16 hoặc 20 cột tùy cách export. File 20 cột có thêm 5 cột (Trạng thái phân phối, Cấp độ phân phối, Người tiếp cận, Lượt hiển thị, Kết quả) — **tự động bỏ qua** các cột này, chỉ xử lý 16 cột chuẩn ở trên. Parser phải tìm cột theo tên, không theo index.

### Output: Google Sheets (theo layout MKT.xlsx)

| Khu vực | Cột | Metrics |
|---------|-----|---------|
| **TỔNG** | B–F | Chi phí ads, GIÁ MESS, CHI PHÍ/KẾT QUẢ, CPM, DOANH SỐ |
| **Theo ngày** | G–K | Chi phí ads, Số đơn, Doanh số, %ads, Chi phí/đơn |
| **Index** | A | MÃ SP (mã sản phẩm) |

---

## Non-Negotiable Rules

1. **File gốc là Read-Only.** Không bao giờ ghi đè file Excel user gửi. Download → đọc → xóa file tạm.

2. **Tìm cột bằng tên Header.** Tuyệt đối không dùng `df.iloc[:, 3]` hay hardcode column index. File export từ Facebook Ads Manager có thể thay đổi số lượng/vị trí cột.

3. **Không hardcode credentials.** Token Telegram, Google credentials → `.env` file. File `credentials.json` (Google Service Account) phải nằm trong `.gitignore`.

4. **Whitelist User IDs.** Bot chỉ xử lý file từ Telegram user IDs có trong `ALLOWED_USERS`. Từ chối tất cả user không nằm trong danh sách.

5. **Xử lý gửi nhiều lần.** User có thể gửi file nhiều lần trong ngày. Bot phải merge/cập nhật data trên Google Sheets thay vì duplicate.

6. **Log rõ ràng.** Mọi file nhận được phải log: user ID, filename, số rows, số rows lỗi (nếu có). Không silent fail.

7. **Error reporting có context.** Khi parse lỗi, thông báo cho user: file nào, dòng nào, cột nào bị thiếu/sai type. Không chỉ nói "Lỗi xử lý file".

---

## Build & Run

```powershell
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env: thêm TELEGRAM_BOT_TOKEN, GOOGLE_SHEETS_SPREADSHEET_ID

# Run
python -m src.bot
```

---

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| Module | `snake_case.py` | `parser.py`, `sheets.py` |
| Function | `snake_case` | `parse_excel_file()` |
| Class | `PascalCase` | `ReportProcessor` |
| Constant | `UPPER_SNAKE_CASE` | `REQUIRED_COLUMNS` |
| Env var | `UPPER_SNAKE_CASE` | `TELEGRAM_BOT_TOKEN` |

---

## Skills System

| Nếu task liên quan đến... | Đọc skill |
|---------------------------|-----------|
| Telegram Bot, handlers, whitelist | `skills/telegram-bot/SKILL.md` |
| Đọc file Excel, normalize schema | `skills/excel-parser/SKILL.md` |
| Google Sheets API, ghi data | `skills/google-sheets/SKILL.md` |
