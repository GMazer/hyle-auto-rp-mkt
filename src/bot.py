# -*- coding: utf-8 -*-
"""
Hyle Auto Report MKT — Telegram Bot Entry Point
Nhận nhiều file Excel từ user → buffer → bấm nút tạo báo cáo → ghi Google Sheets.

Flow:
    1. User gửi file .xlsx → bot parse & buffer (debounce 3s)
    2. Khi hết file (3s không nhận thêm) → gửi summary + nút 📊 Tạo báo cáo
    3. User bấm nút → aggregate tất cả records → ghi Sheets → trả kết quả
    4. /clear để xóa buffer, bắt đầu lại

Usage:
    python -m src.bot
"""

import os
import tempfile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import ALLOWED_USERS, TELEGRAM_BOT_TOKEN, logger
from src.formatter import (
    format_error,
    format_no_data,
    format_summary,
)
from src.parser import get_report_date, parse_excel_file
from src.processor import aggregate_by_product_code, compute_totals
from src.sheets import write_daily_report


# --- User Data Keys ---
KEY_RECORDS = "buffered_records"
KEY_FILES = "buffered_files"
KEY_STATUS_MSG = "status_message"

# Thời gian chờ sau file cuối cùng trước khi gửi summary (giây)
BATCH_DEBOUNCE_SECONDS = 3.0

# Callback data cho nút tạo báo cáo
REPORT_CALLBACK = "create_report"


# --- Handlers ---


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler cho /start command."""
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng bot này.")
        return

    await update.message.reply_text(
        f"👋 Chào *{user.first_name}*!\n\n"
        "Gửi file `.xlsx` báo cáo Facebook Ads để tôi tổng hợp lên Google Sheets.\n\n"
        "📌 *Lệnh:*\n"
        "  /start — Hiện thông tin này\n"
        "  /help — Hướng dẫn sử dụng\n"
        "  /clear — Xóa buffer, bắt đầu lại\n"
        "  /status — Xem số file đã gửi\n\n"
        "📊 Sau khi gửi file, bấm nút *Tạo báo cáo* để tổng hợp.",
        parse_mode="Markdown",
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler cho /help command."""
    if not _is_allowed(update.effective_user.id):
        return

    await update.message.reply_text(
        "📖 *HƯỚNG DẪN SỬ DỤNG*\n\n"
        "1️⃣ Gửi các file `.xlsx` (báo cáo từ Facebook Ads Manager)\n"
        "   ↳ Có thể gửi nhiều file cùng lúc — bot tự gộp\n"
        "2️⃣ Bấm nút *📊 Tạo báo cáo* khi đã gửi đủ file\n"
        "3️⃣ Bot sẽ tự động:\n"
        "   • Gộp dữ liệu theo mã sản phẩm\n"
        "   • Điền vào Google Sheets theo format MKT\n"
        "   • Trả về bảng tóm tắt + link Sheets\n\n"
        "📎 Gửi bao nhiêu file cũng được, bấm nút khi sẵn sàng.\n"
        "🗑 Dùng /clear để xóa và bắt đầu lại.\n"
        "⚠️ Chỉ hỗ trợ file `.xlsx` (không hỗ trợ `.xls`).",
        parse_mode="Markdown",
    )


async def document_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler cho file Excel — parse & buffer, debounce summary."""
    user = update.effective_user
    if not _is_allowed(user.id):
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng bot này.")
        return

    doc = update.message.document
    filename = doc.file_name or "unknown.xlsx"

    # Validate file extension
    if not filename.lower().endswith(".xlsx"):
        await update.message.reply_text(
            f"❌ File `{filename}` không phải định dạng `.xlsx`.\n"
            "Chỉ hỗ trợ file Excel (.xlsx) từ Facebook Ads Manager.",
            parse_mode="Markdown",
        )
        return

    # Check file size (Telegram limit: 20MB)
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await update.message.reply_text("❌ File quá lớn (tối đa 20MB).")
        return

    logger.info(
        "Nhận file từ user %s (%d): %s (%d bytes)",
        user.first_name, user.id, filename, doc.file_size or 0,
    )

    # Init buffer nếu chưa có
    if KEY_RECORDS not in context.user_data:
        context.user_data[KEY_RECORDS] = []
        context.user_data[KEY_FILES] = []

    # Gửi/cập nhật status message "đang nhận file..."
    file_count = len(context.user_data[KEY_FILES]) + 1
    status_text = f"⏳ Đang nhận file... ({file_count} file)"

    status_msg = context.user_data.get(KEY_STATUS_MSG)
    if status_msg:
        try:
            await status_msg.edit_text(status_text)
        except Exception:
            # Message quá cũ hoặc đã bị xóa → gửi mới
            status_msg = await update.message.reply_text(status_text)
            context.user_data[KEY_STATUS_MSG] = status_msg
    else:
        status_msg = await update.message.reply_text(status_text)
        context.user_data[KEY_STATUS_MSG] = status_msg

    # Download file tạm
    temp_path = os.path.join(tempfile.gettempdir(), f"mkt_{user.id}_{filename}")

    try:
        # Download
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(temp_path)
        logger.info("Downloaded: %s → %s", filename, temp_path)

        # Parse Excel
        records = parse_excel_file(temp_path)

        if not records:
            logger.warning("File %s không có dữ liệu", filename)
            # Vẫn tiếp tục — không fail cả batch vì 1 file rỗng
        else:
            context.user_data[KEY_RECORDS].extend(records)

        context.user_data[KEY_FILES].append(filename)

        logger.info(
            "Buffered: %s (%d records) — tổng %d files",
            filename, len(records) if records else 0,
            len(context.user_data[KEY_FILES]),
        )

    except Exception as e:
        logger.exception("Lỗi đọc file %s: %s", filename, e)
        await update.message.reply_text(
            format_error(filename, str(e)),
            parse_mode="Markdown",
        )
        return

    finally:
        # Cleanup file tạm
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # --- Debounce: hủy task cũ, tạo task mới sau 3s ---
    import asyncio

    # Hủy task debounce cũ nếu có
    old_task = context.user_data.get("_debounce_task")
    if old_task and not old_task.done():
        old_task.cancel()

    # Tạo task mới — sau 3s không nhận thêm file → gửi summary
    chat_id = update.effective_chat.id
    user_data_ref = context.user_data

    async def _send_batch_summary():
        await asyncio.sleep(BATCH_DEBOUNCE_SECONDS)
        await _batch_summary(context.bot, chat_id, user_data_ref)

    context.user_data["_debounce_task"] = asyncio.create_task(
        _send_batch_summary()
    )


async def _batch_summary(bot, chat_id: int, user_data: dict) -> None:
    """Gửi summary sau khi nhận xong tất cả file (debounce callback)."""
    files = user_data.get(KEY_FILES, [])
    record_count = len(user_data.get(KEY_RECORDS, []))
    status_msg = user_data.get(KEY_STATUS_MSG)

    if not files:
        return

    file_list = "\n".join(
        f"  {i+1}. `{f}`" for i, f in enumerate(files)
    )

    summary_text = (
        f"✅ *Đã nhận {len(files)} file* ({record_count} dòng dữ liệu)\n\n"
        f"{file_list}\n\n"
        "↳ Gửi thêm file hoặc bấm nút bên dưới để tạo báo cáo"
    )

    report_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📊 Tạo báo cáo", callback_data=REPORT_CALLBACK)]]
    )

    if status_msg:
        try:
            await status_msg.edit_text(
                summary_text, parse_mode="Markdown",
                reply_markup=report_keyboard,
            )
        except Exception:
            await bot.send_message(
                chat_id=chat_id, text=summary_text,
                parse_mode="Markdown", reply_markup=report_keyboard,
            )
    else:
        await bot.send_message(
            chat_id=chat_id, text=summary_text,
            parse_mode="Markdown", reply_markup=report_keyboard,
        )

    # Reset status message reference
    user_data[KEY_STATUS_MSG] = None

    logger.info(
        "Batch summary: %d files, %d records",
        len(files), record_count,
    )


async def report_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler cho nút 📊 Tạo báo cáo — tạo báo cáo từ tất cả file đã buffer."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not _is_allowed(user.id):
        return

    records = context.user_data.get(KEY_RECORDS, [])
    files = context.user_data.get(KEY_FILES, [])

    if not records:
        await query.edit_message_text(
            "📭 Chưa có file nào! Gửi file `.xlsx` trước.",
            parse_mode="Markdown",
        )
        return

    await query.edit_message_text(
        f"⏳ Đang xử lý {len(files)} file ({len(records)} dòng)..."
    )
    status_msg = query.message

    try:
        # Process data — gộp theo mã sản phẩm
        campaigns = aggregate_by_product_code(records)
        totals = compute_totals(campaigns)
        report_date = get_report_date(records)

        # Ghi Google Sheets
        sheet_url = write_daily_report(
            campaigns, report_date or "unknown", file_count=len(files),
        )

        # Tạo summary message
        summary = format_summary(campaigns, totals, report_date)

        # Reply với InlineKeyboard (nút mở Sheets)
        keyboard = [
            [InlineKeyboardButton("📊 Mở Google Sheets", url=sheet_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_msg.edit_text(
            summary,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        logger.info(
            "✅ Hoàn tất: %d files → %d mã SP → sheet '%s'",
            len(files), len(campaigns), report_date,
        )

        # Clear buffer sau khi tạo report thành công
        context.user_data[KEY_RECORDS] = []
        context.user_data[KEY_FILES] = []
        context.user_data[KEY_STATUS_MSG] = None

    except Exception as e:
        logger.exception("Lỗi tạo report: %s", e)
        await status_msg.edit_text(
            format_error("report", str(e)),
            parse_mode="Markdown",
        )


async def clear_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler cho /clear — xóa buffer, bắt đầu lại."""
    if not _is_allowed(update.effective_user.id):
        return

    file_count = len(context.user_data.get(KEY_FILES, []))
    context.user_data[KEY_RECORDS] = []
    context.user_data[KEY_FILES] = []
    context.user_data[KEY_STATUS_MSG] = None

    if file_count > 0:
        await update.message.reply_text(
            f"🗑 Đã xóa {file_count} file. Buffer trống, sẵn sàng nhận file mới."
        )
    else:
        await update.message.reply_text("📭 Buffer đã trống sẵn rồi.")

    logger.info("Cleared buffer (%d files)", file_count)


async def status_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler cho /status — xem trạng thái buffer."""
    if not _is_allowed(update.effective_user.id):
        return

    files = context.user_data.get(KEY_FILES, [])
    record_count = len(context.user_data.get(KEY_RECORDS, []))

    if not files:
        await update.message.reply_text(
            "📭 Chưa có file nào. Gửi file `.xlsx` để bắt đầu.",
            parse_mode="Markdown",
        )
        return

    file_list = "\n".join(
        f"  {i+1}. `{f}`" for i, f in enumerate(files)
    )

    report_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("📊 Tạo báo cáo", callback_data=REPORT_CALLBACK)]]
    )
    await update.message.reply_text(
        f"📁 *Buffer hiện tại: {len(files)} file, {record_count} dòng*\n"
        f"{file_list}\n\n"
        "↳ Bấm nút bên dưới để tạo báo cáo | /clear để xóa",
        parse_mode="Markdown",
        reply_markup=report_keyboard,
    )


# --- Helpers ---


def _is_allowed(user_id: int) -> bool:
    """Kiểm tra user có trong whitelist không."""
    if not ALLOWED_USERS:
        logger.warning("ALLOWED_USERS rỗng — cho phép tất cả.")
        return True
    return user_id in ALLOWED_USERS


# --- Main ---


def main() -> None:
    """Khởi chạy Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN chưa được cấu hình!")
        logger.error("   Copy .env.example → .env và điền token.")
        return

    logger.info("🤖 Khởi động Hyle Auto Report MKT Bot...")
    logger.info("   Allowed users: %s", ALLOWED_USERS or "(tất cả)")

    # Hugging Face Spaces: cần HTTP server cho health check
    if os.environ.get("SPACE_ID"):
        from src.health import start_health_server
        start_health_server(port=7860)
        logger.info("   Health check server on :7860 (HF Spaces)")


    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CallbackQueryHandler(report_callback_handler, pattern=f"^{REPORT_CALLBACK}$"))
    app.add_handler(CommandHandler("clear", clear_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(
        MessageHandler(filters.Document.ALL, document_handler)
    )

    # Start polling (bootstrap_retries cho phép retry khi network chưa sẵn sàng)
    logger.info("🟢 Bot đang chạy... (Ctrl+C để dừng)")
    app.run_polling(
        drop_pending_updates=True,
        bootstrap_retries=5,
        connect_timeout=30,
        read_timeout=30,
    )


if __name__ == "__main__":
    main()
