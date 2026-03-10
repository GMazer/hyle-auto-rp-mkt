---
description: Hướng dẫn đọc và parse file Excel Facebook Ads report với openpyxl — normalize schema 16/20 cột
---

# Excel Parser — Facebook Ads Report

## Khi nào dùng skill này
- Đọc file .xlsx từ Facebook Ads Manager export
- Normalize schema (16 cột vs 20 cột)
- Clean data (xử lý None, chuẩn hóa kiểu dữ liệu)

## Nguyên tắc cốt lõi

> **KHÔNG BAO GIỜ** tìm cột bằng index. LUÔN tìm bằng tên header.

## 16 cột chuẩn (chỉ xử lý các cột này)

| # | Tên cột | Kiểu | Ghi chú |
|---|---------|------|---------|
| 1 | Tên chiến dịch | str | Campaign name |
| 2 | Tên Trang | str | Fanpage |
| 3 | Tần suất | float | Frequency |
| 4 | Cài đặt ghi nhận | str | Attribution setting |
| 5 | Loại kết quả | str | Result type (có thể rỗng) |
| 6 | Chi phí trên mỗi kết quả | float | Cost per result (có thể rỗng) |
| 7 | Bắt đầu | str | Campaign start date |
| 8 | Kết thúc | str | Campaign end date |
| 9 | Số tiền đã chi tiêu (VND) | float | **Total spend** |
| 10 | CPM (Chi phí trên mỗi 1.000 lượt hiển thị) | float | Cost per mille |
| 11 | Loại giá trị kết quả | str | Result value type |
| 12 | ROAS kết quả | float | Return on ad spend |
| 13 | Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn | float | **Giá mess** |
| 14 | CTR (Tất cả) | float | Click-through rate |
| 15 | Bắt đầu báo cáo | str/date | Report start date |
| 16 | Kết thúc báo cáo | str/date | Report end date |

### 5 cột PHẢI BỎ QUA (chỉ có ở file 20-cột)
- Trạng thái phân phối
- Cấp độ phân phối
- Người tiếp cận
- Lượt hiển thị
- Kết quả

### Cột đặc biệt ở MAVO-6
- "Chi phí trên mỗi tin nhắn đã đến" — có tên khác nhưng thường rỗng, bỏ qua

## Pattern: Parse file

```python
import openpyxl

# Các cột cần lấy (tìm bằng tên)
REQUIRED_COLUMNS = {
    'Tên chiến dịch',
    'Tên Trang',
    'Tần suất',
    'Số tiền đã chi tiêu (VND)',
    'CPM (Chi phí trên mỗi 1.000 lượt hiển thị)',
    'Chi phí trên mỗi kết quả',
    'Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn',
    'ROAS kết quả',
    'Bắt đầu báo cáo',
    'Kết thúc báo cáo',
}

def parse_excel_file(filepath: str) -> list[dict]:
    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active
    
    # Bước 1: Tìm header row, map tên → index
    headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
    col_map = {}
    for col_name in REQUIRED_COLUMNS:
        if col_name in headers:
            col_map[col_name] = headers.index(col_name)
    
    # Bước 2: Kiểm tra cột thiếu
    missing = REQUIRED_COLUMNS - set(col_map.keys())
    if missing:
        logger.warning(f"Thiếu cột: {missing}")
    
    # Bước 3: Đọc data rows
    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[col_map.get('Tên chiến dịch', 0)] is None:
            continue  # Skip empty rows
        record = {}
        for col_name, idx in col_map.items():
            record[col_name] = row[idx]
        records.append(record)
    
    wb.close()
    return records
```

## Data Cleaning Rules

1. **Empty rows**: Skip nếu `Tên chiến dịch` là None
2. **Số tiền**: Luôn cast sang `float`, xử lý string có dấu phẩy
3. **Date**: Có thể là string `"2026-03-07"` hoặc `datetime` object → chuẩn hóa thành string
4. **Rỗng vs 0**: Phân biệt giữa cột rỗng (không có data) và giá trị 0 thực sự

## Lỗi thường gặp
- File không có default style → openpyxl warning (vô hại, bỏ qua)
- Cột "Chi phí trên mỗi tin nhắn đã đến" ≠ "Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn" → tên khác nhau, phải tìm chính xác
- File 20 cột: header index bị lệch so với file 16 cột → lý do phải tìm bằng tên
