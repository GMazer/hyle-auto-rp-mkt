---
description: Hướng dẫn xây dựng Telegram Bot nhận file Excel và xử lý document với python-telegram-bot v21+
---

# Telegram Bot — File Processing

## Khi nào dùng skill này
- Xây dựng hoặc sửa Telegram Bot handlers
- Xử lý file document (nhận file từ user, download, validate)
- Tạo reply với InlineKeyboard buttons
- Quản lý whitelist user IDs

## Tech Stack
- `python-telegram-bot` v21+ (async)
- Python 3.11+

## Patterns

### 1. Bot Setup (Application)
```python
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler("help", help_handler))
app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
app.run_polling()
```

### 2. Document Handler (nhận + download file)
```python
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Whitelist check
    if user_id not in config.ALLOWED_USERS:
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng bot này.")
        return
    
    doc = update.message.document
    
    # Validate file type
    if not doc.file_name.endswith('.xlsx'):
        await update.message.reply_text("❌ Chỉ hỗ trợ file .xlsx")
        return
    
    # Download to temp
    file = await context.bot.get_file(doc.file_id)
    temp_path = os.path.join(tempfile.gettempdir(), doc.file_name)
    await file.download_to_drive(temp_path)
    
    try:
        # Process file...
        pass
    finally:
        # Always cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

### 3. Reply với InlineKeyboard
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = [[
    InlineKeyboardButton("📊 Mở Google Sheets", url=sheet_url)
]]
reply_markup = InlineKeyboardMarkup(keyboard)

await update.message.reply_text(
    summary_text,
    reply_markup=reply_markup,
    parse_mode="Markdown"
)
```

### 4. Whitelist Pattern
```python
# config.py
ALLOWED_USERS = set(
    int(uid.strip()) 
    for uid in os.getenv("ALLOWED_USERS", "").split(",") 
    if uid.strip()
)
```

## Best Practices

1. **Luôn cleanup file tạm** sau khi xử lý (dùng `try/finally`)
2. **Validate file type** trước khi download (kiểm tra extension)
3. **Reply trạng thái** cho user (VD: "⏳ Đang xử lý...") trước khi bắt đầu xử lý nặng
4. **Async handlers** — python-telegram-bot v21+ là async, dùng `async def` + `await`
5. **Error handling** — catch exception, reply lỗi cụ thể cho user thay vì để bot crash

## Lỗi thường gặp
- Quên `await` trước `file.download_to_drive()` → file rỗng
- Không cleanup file tạm → memory leak khi chạy lâu
- Không check whitelist → bất kỳ ai cũng dùng được bot
- File quá lớn (>20MB) → Telegram API giới hạn, cần thông báo user
