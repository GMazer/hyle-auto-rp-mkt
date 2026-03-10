# -*- coding: utf-8 -*-
"""
Hyle Auto Report MKT — Configuration
Load environment variables và define constants.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

ALLOWED_USERS: set[int] = set(
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USERS", "").split(",")
    if uid.strip()
)

# --- Google Sheets / OAuth 2.0 ---
GOOGLE_SHEETS_CREDENTIALS_FILE: str = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json"
)
GOOGLE_OAUTH_TOKEN_FILE: str = os.getenv(
    "GOOGLE_OAUTH_TOKEN_FILE", "token.json"
)
# ID của spreadsheet MKT template (sẽ được copy mỗi lần tạo báo cáo)
GOOGLE_SHEETS_TEMPLATE_ID: str = os.getenv("GOOGLE_SHEETS_TEMPLATE_ID", "")
# ID folder Google Drive để lưu các bản copy (optional)
GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(
    format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)

logger = logging.getLogger("hyle-mkt")

# --- Data Schema ---
# 16 cột chuẩn từ Facebook Ads export. Parser chỉ lấy các cột này.
REQUIRED_COLUMNS: list[str] = [
    "Tên chiến dịch",
    "Tên Trang",
    "Tần suất",
    "Cài đặt ghi nhận",
    "Loại kết quả",
    "Chi phí trên mỗi kết quả",
    "Bắt đầu",
    "Kết thúc",
    "Số tiền đã chi tiêu (VND)",
    "CPM (Chi phí trên mỗi 1.000 lượt hiển thị)",
    "Loại giá trị kết quả",
    "ROAS kết quả",
    "Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn",
    "CTR (Tất cả)",
    "Bắt đầu báo cáo",
    "Kết thúc báo cáo",
]

# Các cột số liệu chính mà sếp yêu cầu
KEY_METRICS: dict[str, str] = {
    "spend": "Số tiền đã chi tiêu (VND)",
    "cost_per_result": "Chi phí trên mỗi kết quả",
    "cost_per_message": "Chi phí trên mỗi lượt bắt đầu cuộc trò chuyện qua tin nhắn",
    "cpm": "CPM (Chi phí trên mỗi 1.000 lượt hiển thị)",
    "roas": "ROAS kết quả",
    "ctr": "CTR (Tất cả)",
    "frequency": "Tần suất",
}

# Mapping cột MKT output (TỔNG section, row 3)
MKT_TOTAL_HEADERS: list[str] = [
    "MÃ SP",           # A
    "Chi phí ads",     # B — tổng spend
    "GIÁ MESS",        # C — giá tin nhắn
    "CHI PHÍ/ KẾT QUẢ",  # D — cost per result
    "CPM",             # E — formula = B/D
    "DOANH SỐ",        # F — formula = B/C
]

# Mapping cột daily section (lặp mỗi 5 cột)
MKT_DAILY_HEADERS: list[str] = [
    "Chi phí ads",     # spend
    "Số đơn",          # (để trống — chưa có nguồn)
    "Doanh số",        # (để trống — chưa có nguồn)
    "%ads",            # formula = Chi phí ads / Doanh số
    "Chí phí / đơn",   # formula = Chi phí ads / Số đơn
]

MKT_DAILY_COLS_PER_DAY: int = len(MKT_DAILY_HEADERS)  # 5

# --- Product Code Mapping ---
# Quy tắc nhận diện mã sản phẩm từ tên chiến dịch Facebook Ads.
# A = Áo, V = Váy — nhưng bán set nên gộp chung (VD: A700 + V700 → "700").
# Thứ tự quan trọng: pattern đầu tiên match sẽ được chọn.
PRODUCT_CODE_PATTERNS: list[tuple[str, str]] = [
    # Combo (phải check TRƯỚC các mã số, vì tên chứa "320-730-150")
    (r"(?i)3\s*m[aã]\s*320", "3 MÃ COMBO"),
    # Mã số sản phẩm (A/V + số)
    (r"(?i)[AV]?360", "360"),
    (r"(?i)[AV]?520", "520"),
    (r"(?i)[AV]?690", "690"),
    (r"(?i)[AV]?700", "700"),
    (r"(?i)[AV]?730", "730"),
    # Sản phẩm gia dụng
    (r"(?i)c[aâ]y\s*ch[aà]\s*s[aà]n", "CÂY CHÀ SÀN"),
    (r"(?i)c[oọ]\s*(b[oồ]n\s*c[aầ]u|mess)", "CỌ BỒN CẦU"),
    (r"(?i)ch[oổ]i\s*499", "CHỔI 499K"),
    (r"(?i)[aấ]m\s*g[aấ]p\s*g[oọ]n", "ẤM GẤP GỌN"),
    (r"(?i)m[aá]y\s*(?:l[aà]m\s*)?s[uữ]a(?:\s*h[aạ]t)?", "MÁY SỮA HẠT"),
]
