---
description: Hướng dẫn copy MKT template spreadsheet + ghi data với gspread + Service Account
---

# Google Sheets — Template Copy & Report Writer

## Khi nào dùng skill này
- Copy MKT template spreadsheet (giữ nguyên formatting)
- Ghi data vào bản copy mà không phá formula
- Quản lý Google Drive folder

## Setup Google Service Account

### Bước 1: Tạo Service Account
1. Vào [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Sheets API** + **Google Drive API**
3. Tạo Service Account → Download `credentials.json`
4. Copy email service account (VD: `bot@project.iam.gserviceaccount.com`)

### Bước 2: Share Google Sheet
- Mở Google Sheet target
- Share với email service account (Editor permission)

### Bước 3: Config
```env
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=1ABC_spreadsheet_id_here
```

## Layout MKT.xlsx (output template)

```
     A          B             C              D                E         F
  ┌──────────┬────────────────────────────────────────────────────────────────┐
1 │          │                                                              │
2 │  NGÀY    │  ◄──── TỔNG (merged B2:F2) ────►                            │
3 │  MÃ SP   │  Chi phí ads │ GIÁ MESS │ CHI PHÍ/KẾT QUẢ │ CPM │ DOANH SỐ │
4 │  SP001   │  500000      │ 25000    │ 50000            │ 150 │ 2000000  │
  └──────────┴────────────────────────────────────────────────────────────────┘
     G              H          I         J          K
  ┌────────────────────────────────────────────────────────┐
  │  ◄──── Theo ngày (merged G2:K2) ────►                  │
  │  Chi phí ads │ Số đơn │ Doanh số │ %ads │ Chi phí/đơn  │
  │  200000      │ 5      │ 1000000  │ 20%  │ 40000        │
  └────────────────────────────────────────────────────────┘
```

## Patterns

### 1. Connect & Auth
```python
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_sheets_client():
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_FILE,
        scopes=SCOPES
    )
    return gspread.authorize(creds)
```

### 2. Open Spreadsheet
```python
def get_spreadsheet():
    client = get_sheets_client()
    return client.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)
```

### 3. Tìm hoặc tạo worksheet theo ngày
```python
def get_or_create_worksheet(spreadsheet, date_str: str):
    """date_str format: '07-03' (ngày-tháng)"""
    try:
        return spreadsheet.worksheet(date_str)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=date_str, rows=50, cols=11)
        # Setup header giống MKT template
        ws.update('A2', 'NGÀY')
        ws.update('A3', 'MÃ SP')
        ws.merge_cells('B2:F2')
        ws.update('B2', 'TỔNG')
        ws.merge_cells('G2:K2')
        ws.update('G2', date_str)
        # Header row 3
        headers = ['', 'Chi phí ads', 'GIÁ MESS', 'CHI PHÍ/ KẾT QUẢ', 
                   'CPM', 'DOANH SỐ', 'Chi phí ads', 'Số đơn', 
                   'Doanh số', '%ads', 'Chí phí / đơn']
        ws.update('A3:K3', [headers])
        return ws
```

### 4. Batch Update (tránh rate limit)
```python
def write_report_data(ws, data: list[dict], start_row: int = 4):
    """Ghi toàn bộ data 1 lần bằng batch update"""
    rows = []
    for item in data:
        rows.append([
            item.get('ma_sp', ''),
            item.get('chi_phi_ads', 0),
            item.get('gia_mess', 0),
            item.get('chi_phi_ket_qua', 0),
            item.get('cpm', 0),
            item.get('doanh_so', 0),
            # Các cột theo ngày sẽ bổ sung sau
            item.get('chi_phi_ads_ngay', 0),
            item.get('so_don', 0),
            item.get('doanh_so_ngay', 0),
            item.get('phan_tram_ads', ''),
            item.get('chi_phi_don', ''),
        ])
    
    end_row = start_row + len(rows) - 1
    ws.update(f'A{start_row}:K{end_row}', rows)
```

## Best Practices

1. **Batch update** thay vì ghi từng cell — tránh rate limit (100 requests/100s)
2. **Cache auth** — không tạo credentials mới mỗi lần gọi
3. **Handle gửi nhiều lần** — kiểm tra xem sheet ngày đã có data chưa, cập nhật thay vì duplicate
4. **Format số** — Google Sheets tự nhận kiểu nếu gửi number, nên cast trước khi ghi
5. **Error handling** — catch `gspread.exceptions.APIError` cho rate limit hoặc permission issues

## Lỗi thường gặp
- `SpreadsheetNotFound` → Chưa share sheet với service account email
- `APIError 429` → Rate limit, cần dùng batch update hoặc delay
- Merged cells bị lỗi khi cập nhật → Phải unmerge trước khi ghi lại
- Credentials file thiếu scope → Cần cả Sheets API + Drive API
