# -*- coding: utf-8 -*-
"""
Hyle Auto Report MKT — Telegram Message Formatter
Tạo bảng tóm tắt Markdown và InlineKeyboard cho Telegram reply.
"""

from typing import Any


def format_summary(
    campaigns: list[dict[str, Any]],
    totals: dict[str, Any],
    report_date: str | None = None,
) -> str:
    """
    Tạo message tóm tắt cho Telegram bot.

    Args:
        campaigns: list campaigns đã sorted
        totals: dict từ processor.compute_totals()
        report_date: ngày báo cáo

    Returns:
        str — message Markdown
    """
    date_display = report_date or "N/A"
    count = totals.get("campaign_count", 0)
    total_spend = totals.get("total_spend", 0)

    lines: list[str] = []
    lines.append(f"📊 *BÁO CÁO NGÀY {date_display}*")
    lines.append("")

    # Tổng quan
    lines.append(f"▫️ Số chiến dịch: *{count}*")
    lines.append(f"▫️ Tổng chi phí ads: *{_fmt_money(total_spend)}*")

    avg_msg = totals.get("avg_cost_per_message")
    if avg_msg is not None:
        lines.append(f"▫️ Giá MESS TB: *{_fmt_money(avg_msg)}*")

    avg_result = totals.get("avg_cost_per_result")
    if avg_result is not None:
        lines.append(f"▫️ Chi phí/kết quả TB: *{_fmt_money(avg_result)}*")

    avg_cpm = totals.get("avg_cpm")
    if avg_cpm is not None:
        lines.append(f"▫️ CPM TB: *{_fmt_money(avg_cpm)}*")

    # Top 5 campaigns by spend
    if campaigns:
        lines.append("")
        lines.append("📌 *TOP CHIẾN DỊCH (theo chi phí):*")
        for i, camp in enumerate(campaigns[:5], 1):
            name = _truncate(camp.get("campaign", ""), 30)
            spend = _fmt_money(camp.get("spend"))
            msg_cost = camp.get("cost_per_message")
            msg_str = f" | Mess: {_fmt_money(msg_cost)}" if msg_cost else ""
            lines.append(f"  {i}. {name}")
            lines.append(f"     💰 {spend}{msg_str}")

    return "\n".join(lines)


def format_error(filename: str, error: str) -> str:
    """Format error message cho Telegram."""
    return (
        f"❌ *Lỗi xử lý file:* `{filename}`\n\n"
        f"```\n{error}\n```\n\n"
        f"Vui lòng kiểm tra lại file và thử gửi lại."
    )


def format_processing() -> str:
    """Message trạng thái đang xử lý."""
    return "⏳ Đang xử lý file báo cáo..."


def format_no_data(filename: str) -> str:
    """Message khi file không có dữ liệu."""
    return (
        f"⚠️ File `{filename}` không chứa dữ liệu chiến dịch nào.\n"
        f"Kiểm tra lại file có đúng format Facebook Ads export không."
    )


def _fmt_money(value: float | None) -> str:
    """Format số tiền VND với dấu phẩy ngăn cách."""
    if value is None:
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"{value:,.0f}đ"
    return f"{value:,.2f}đ"


def _truncate(text: str, max_len: int) -> str:
    """Cắt text nếu quá dài."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
