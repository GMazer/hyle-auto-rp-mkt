# -*- coding: utf-8 -*-
"""
Hyle Auto Report MKT — Data Processor
Aggregate dữ liệu từ parser theo mã sản phẩm, tính metrics cho MKT report.
"""

import re
from typing import Any

from src.config import KEY_METRICS, PRODUCT_CODE_PATTERNS, logger


def extract_product_code(campaign_name: str) -> str:
    """
    Trích xuất mã sản phẩm từ tên chiến dịch Facebook Ads.

    Dùng regex patterns từ PRODUCT_CODE_PATTERNS (config.py).
    First match wins.

    Args:
        campaign_name: tên chiến dịch gốc từ Facebook Ads

    Returns:
        Mã sản phẩm chuẩn hóa (VD: "700", "CÂY CHÀ SÀN"),
        hoặc tên gốc nếu không match pattern nào.
    """
    for pattern, code in PRODUCT_CODE_PATTERNS:
        if re.search(pattern, campaign_name):
            return code

    # Không match → giữ nguyên tên gốc
    logger.warning("Không nhận diện được mã SP: '%s'", campaign_name)
    return campaign_name


def aggregate_by_campaign(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize mỗi record thành dict chuẩn với metrics.

    Returns:
        list[dict] — mỗi dict chứa metrics cho 1 record.
    """
    if not records:
        return []

    results: list[dict[str, Any]] = []

    for record in records:
        campaign = record.get("Tên chiến dịch", "")
        results.append({
            "campaign": campaign,
            "product_code": extract_product_code(campaign),
            "page": record.get("Tên Trang", ""),
            "spend": _safe_float(record.get(KEY_METRICS["spend"])),
            "cost_per_result": _safe_float(record.get(KEY_METRICS["cost_per_result"])),
            "cost_per_message": _safe_float(record.get(KEY_METRICS["cost_per_message"])),
            "cpm": _safe_float(record.get(KEY_METRICS["cpm"])),
            "roas": _safe_float(record.get(KEY_METRICS["roas"])),
            "ctr": _safe_float(record.get(KEY_METRICS["ctr"])),
            "frequency": _safe_float(record.get(KEY_METRICS["frequency"])),
            "report_date": record.get("Bắt đầu báo cáo"),
        })

    results.sort(key=lambda x: x.get("spend") or 0, reverse=True)
    return results


def aggregate_by_product_code(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Aggregate dữ liệu theo mã sản phẩm.
    Gộp tất cả campaigns cùng mã SP → 1 row trong MKT output.

    - spend: tổng cộng
    - cost_per_result: weighted average theo spend
    - cost_per_message: weighted average theo spend

    Returns:
        list[dict] — mỗi dict = 1 mã SP, sắp xếp theo spend giảm dần.
    """
    if not records:
        return []

    # Normalize records
    campaigns = aggregate_by_campaign(records)

    # Group by product code
    groups: dict[str, list[dict[str, Any]]] = {}
    for camp in campaigns:
        code = camp["product_code"]
        if code not in groups:
            groups[code] = []
        groups[code].append(camp)

    # Aggregate each group
    results: list[dict[str, Any]] = []
    for code, items in groups.items():
        total_spend = sum(c["spend"] or 0 for c in items)

        result = {
            "product_code": code,
            "campaign": code,  # Dùng mã SP làm tên hiển thị
            "campaigns_count": len(items),
            "campaigns_detail": [c["campaign"] for c in items],
            "spend": total_spend if total_spend > 0 else None,
            "cost_per_result": _weighted_avg(items, "cost_per_result", "spend"),
            "cost_per_message": _weighted_avg(items, "cost_per_message", "spend"),
            "cpm": _weighted_avg(items, "cpm", "spend"),
            "roas": _weighted_avg(items, "roas", "spend"),
            "ctr": _weighted_avg(items, "ctr", "spend"),
            "frequency": _simple_avg(items, "frequency"),
            "report_date": items[0].get("report_date"),
        }
        results.append(result)

    results.sort(key=lambda x: x.get("spend") or 0, reverse=True)

    logger.info(
        "Aggregated %d campaigns → %d mã SP, tổng spend: %s VND",
        len(campaigns),
        len(results),
        f"{sum(r['spend'] or 0 for r in results):,.0f}",
    )

    return results


def compute_totals(campaigns: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Tính tổng cho section TỔNG trong MKT report.

    Returns:
        dict với keys: total_spend, avg_cost_per_message, avg_cost_per_result,
        avg_cpm, campaign_count.
    """
    if not campaigns:
        return {
            "total_spend": 0,
            "avg_cost_per_message": None,
            "avg_cost_per_result": None,
            "avg_cpm": None,
            "campaign_count": 0,
        }

    total_spend = sum(c["spend"] or 0 for c in campaigns)

    # Weighted average CPM (theo spend)
    avg_cpm = _weighted_avg(campaigns, "cpm", "spend")

    # Average giá mess (chỉ tính campaigns có data)
    avg_cost_message = _simple_avg(campaigns, "cost_per_message")

    # Average chi phí/kết quả
    avg_cost_result = _simple_avg(campaigns, "cost_per_result")

    return {
        "total_spend": total_spend,
        "avg_cost_per_message": avg_cost_message,
        "avg_cost_per_result": avg_cost_result,
        "avg_cpm": avg_cpm,
        "campaign_count": len(campaigns),
    }


def _safe_float(value: Any) -> float | None:
    """Convert sang float, None nếu không hợp lệ."""
    if value is None:
        return None
    try:
        result = float(value)
        return result if result != 0 else None
    except (ValueError, TypeError):
        return None


def _weighted_avg(
    items: list[dict], value_key: str, weight_key: str
) -> float | None:
    """Tính weighted average, bỏ qua items không có giá trị."""
    total_weight = 0.0
    total_value = 0.0
    for item in items:
        val = item.get(value_key)
        weight = item.get(weight_key)
        if val is not None and weight is not None:
            total_value += val * weight
            total_weight += weight
    if total_weight == 0:
        return None
    return total_value / total_weight


def _simple_avg(items: list[dict], key: str) -> float | None:
    """Tính average đơn giản, bỏ qua None."""
    values = [item[key] for item in items if item.get(key) is not None]
    if not values:
        return None
    return sum(values) / len(values)

