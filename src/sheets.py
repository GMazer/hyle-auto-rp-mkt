# -*- coding: utf-8 -*-
"""
Hyle Auto Report MKT — Google Sheets Writer
Mỗi lần tạo báo cáo → copy template MKT → điền data → trả URL.
Template giữ nguyên: font, màu sắc, cỡ chữ, công thức, merge cells.
"""

import os
from typing import Any

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from src.config import (
    GOOGLE_SHEETS_CREDENTIALS_FILE,
    GOOGLE_OAUTH_TOKEN_FILE,
    GOOGLE_SHEETS_TEMPLATE_ID,
    GOOGLE_DRIVE_FOLDER_ID,
    logger,
)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Cache client
_client: gspread.Client | None = None


def _get_oauth_credentials() -> Credentials:
    """
    Lấy OAuth 2.0 credentials từ token hoặc chạy login flow.

    - Lần đầu: mở browser để user đăng nhập Google → lưu token.json
    - Lần sau: load token từ file, refresh nếu expired.
    """
    creds = None

    # Load cached token
    if os.path.exists(GOOGLE_OAUTH_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            GOOGLE_OAUTH_TOKEN_FILE, SCOPES,
        )
        logger.debug("Loaded cached token từ %s", GOOGLE_OAUTH_TOKEN_FILE)

    # Refresh hoặc chạy login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, đang refresh...")
            creds.refresh(Request())
        else:
            logger.info(
                "Chưa có token — mở browser để đăng nhập Google..."
            )
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_SHEETS_CREDENTIALS_FILE, SCOPES,
            )
            creds = flow.run_local_server(port=0)
            logger.info("Đăng nhập thành công!")

        # Lưu token cho lần sau
        with open(GOOGLE_OAUTH_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        logger.info("Đã lưu token → %s", GOOGLE_OAUTH_TOKEN_FILE)

    return creds


def get_client() -> gspread.Client:
    """Khởi tạo hoặc trả về cached gspread client."""
    global _client
    if _client is None:
        creds = _get_oauth_credentials()
        _client = gspread.authorize(creds)
        logger.info("Google Sheets client đã kết nối (OAuth 2.0).")
    return _client


def copy_template(report_title: str) -> gspread.Spreadsheet:
    """
    Copy spreadsheet MKT template, giữ nguyên toàn bộ formatting.

    Args:
        report_title: Tên cho bản copy (VD: "MKT Report 07-03-2026")

    Returns:
        gspread.Spreadsheet — bản copy đã tạo.
    """
    client = get_client()

    if not GOOGLE_SHEETS_TEMPLATE_ID:
        raise ValueError(
            "GOOGLE_SHEETS_TEMPLATE_ID chưa được cấu hình! "
            "Hãy set trong file .env"
        )

    # Copy spreadsheet trực tiếp vào folder đích (giữ nguyên format, màu, font, formulas)
    copy_kwargs = {
        "file_id": GOOGLE_SHEETS_TEMPLATE_ID,
        "title": report_title,
        "copy_permissions": False,
    }
    if GOOGLE_DRIVE_FOLDER_ID:
        copy_kwargs["folder_id"] = GOOGLE_DRIVE_FOLDER_ID

    copied = client.copy(**copy_kwargs)

    logger.info(
        "Đã copy template → '%s' (ID: %s, folder: %s)",
        report_title, copied.id,
        GOOGLE_DRIVE_FOLDER_ID or "My Drive",
    )

    return copied


def write_daily_report(
    campaigns: list[dict[str, Any]],
    date_str: str,
    file_count: int = 1,
) -> str:
    """
    Tạo bản copy từ MKT template và điền dữ liệu báo cáo.

    Args:
        campaigns: list[dict] từ processor.aggregate_by_product_code()
        date_str: ngày báo cáo (VD: "2026-03-07")
        file_count: số file đã gửi

    Returns:
        URL của spreadsheet mới.
    """
    # Tạo tiêu đề: "MKT Report [số file] [ngày hiện tại]"
    from datetime import datetime
    today = datetime.now().strftime("%d-%m-%Y")
    report_title = f"MKT Report {file_count} {today}"

    # Copy template
    spreadsheet = copy_template(report_title)

    # Mở sheet đầu tiên (sheet gốc trong template)
    ws = spreadsheet.sheet1

    # Cập nhật ngày trong header (cell G2 theo MKT layout)
    try:
        ws.update_acell("G2", sheet_date)
    except Exception as e:
        logger.warning("Không thể cập nhật header ngày: %s", e)

    # Chuẩn bị data rows (bắt đầu từ row 4 theo layout MKT)
    if campaigns:
        rows: list[list[Any]] = []

        for camp in campaigns:
            spend = camp.get("spend") or ""
            cost_msg = camp.get("cost_per_message") or ""
            cost_result = camp.get("cost_per_result") or ""
            cpm = camp.get("cpm") or ""

            row_data = [
                camp.get("campaign", ""),   # A: MÃ SP / Tên chiến dịch
                "",                          # B: Chi phí ads TỔNG (formula trong template)
                cost_msg,                    # C: GIÁ MESS (chi phí/tin nhắn)
                cost_result,                 # D: CHI PHÍ/KẾT QUẢ
                cpm,                         # E: CPM (đ)
                "",                          # F: DOANH SỐ (formula)
                spend,                       # G: Chi phí ads (ngày)
                "",                          # H: Số đơn (để trống)
                "",                          # I: Doanh số (để trống)
                "",                          # J: %ads (formula trong template)
                "",                          # K: Chi phí/đơn (formula trong template)
            ]
            rows.append(row_data)

        start_row = 4
        end_row = start_row + len(rows) - 1

        # Batch update — ghi data vào các cột có giá trị thực
        # Cột A (tên), C (giá mess), D (chi phí/KQ), E (CPM), G (spend ngày)
        # Các cột B, F, J, K giữ formula từ template
        _write_data_preserving_formulas(ws, rows, start_row)

        logger.info(
            "Đã ghi %d rows vào '%s' (rows %d-%d)",
            len(rows), report_title, start_row, end_row,
        )

    return spreadsheet.url


def _write_data_preserving_formulas(
    ws: gspread.Worksheet,
    rows: list[list[Any]],
    start_row: int,
) -> None:
    """
    Ghi data vào sheet, chỉ cập nhật các cell có giá trị thực.
    Giữ nguyên formulas có sẵn trong template.
    """
    batch_updates: list[dict] = []

    for i, row in enumerate(rows):
        r = start_row + i

        # A: Tên chiến dịch
        if row[0]:
            batch_updates.append({
                "range": f"A{r}",
                "values": [[row[0]]],
            })

        # C: GIÁ MESS (chi phí trên mỗi lượt bắt đầu cuộc trò chuyện)
        if row[2] != "":
            batch_updates.append({
                "range": f"C{r}",
                "values": [[row[2]]],
            })

        # D: CHI PHÍ/KẾT QUẢ (chi phí trên mỗi kết quả)
        if row[3] != "":
            batch_updates.append({
                "range": f"D{r}",
                "values": [[row[3]]],
            })

        # E: CPM (đ — chi phí trên mỗi 1.000 lượt hiển thị)
        if row[4] != "":
            batch_updates.append({
                "range": f"E{r}",
                "values": [[row[4]]],
            })

        # G: Chi phí ads (spend ngày)
        if row[6] != "":
            batch_updates.append({
                "range": f"G{r}",
                "values": [[row[6]]],
            })

    if batch_updates:
        ws.batch_update(batch_updates, value_input_option="USER_ENTERED")

    # Fix cell format — template có thể dùng format % hoặc khác
    # Force các cột tiền tệ sang format số thường (đ)
    end_row = start_row + len(rows) - 1
    number_format = {"numberFormat": {"type": "NUMBER", "pattern": '#,##0"đ"'}}
    ws.format(f"C{start_row}:E{end_row}", number_format)
    ws.format(f"G{start_row}:G{end_row}", number_format)


def _format_display_date(date_str: str) -> str:
    """
    Format date cho tiêu đề.
    Input: '2026-03-07' → Output: '07-03-2026'
    Input: '07-03' → Output: '07-03'
    """
    if not date_str:
        return "unknown"

    # Format YYYY-MM-DD
    if len(date_str) == 10 and date_str[4] == "-":
        parts = date_str.split("-")
        return f"{parts[2]}-{parts[1]}-{parts[0]}"

    return date_str
