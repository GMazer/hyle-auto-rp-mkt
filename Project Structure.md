# Hyle Auto Report MKT — Project Structure

```
hyle-auto-rp-mkt/
├── src/                        ← Source code chính
│   ├── __init__.py
│   ├── bot.py                  ← Entry point: Telegram bot, handlers
│   ├── config.py               ← Load .env, constants, whitelist
│   ├── parser.py               ← Excel Parser: đọc file, normalize schema
│   ├── processor.py            ← Data Processor: aggregate metrics
│   ├── sheets.py               ← Google Sheets: gspread read/write
│   └── formatter.py            ← Format summary text cho Telegram reply
├── skills/                     ← AI agent skills (custom cho dự án)
│   ├── telegram-bot/SKILL.md   ← Bot patterns, file handling, whitelist
│   ├── excel-parser/SKILL.md   ← 16-col schema, column-by-name parsing
│   └── google-sheets/SKILL.md  ← Service Account, MKT layout, batch update
├── Raw Data/                   ← Dữ liệu mẫu (gitignored, chỉ tham khảo)
├── .env.example                ← Template environment variables
├── .gitignore
├── requirements.txt            ← Python dependencies
├── README.md                   ← Hướng dẫn setup & sử dụng
├── CLAUDE.md                   ← Project Constitution (đọc đầu tiên)
├── AGENTS.md                   ← Agent Configuration
├── AGENT_PROMPT.md             ← Agent Startup Prompt
└── Project Structure.md        ← File này
```

## Module Responsibilities

| Module | Vai trò |
|--------|---------|
| `bot.py` | Khởi tạo Telegram bot, register handlers (document, /start, /help), orchestrate flow |
| `config.py` | Load `TELEGRAM_BOT_TOKEN`, `GOOGLE_SHEETS_*`, `ALLOWED_USERS` từ `.env` |
| `parser.py` | Đọc file `.xlsx`, tìm cột theo tên header, trả về list[dict] chuẩn hóa |
| `processor.py` | Group by chiến dịch, tính tổng spend, CPM, giá mess, cost/result |
| `sheets.py` | Auth Google Service Account, tìm/tạo sheet ngày, điền data theo layout MKT |
| `formatter.py` | Tạo bảng tóm tắt Markdown cho Telegram + InlineKeyboard link |
