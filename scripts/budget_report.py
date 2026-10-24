#!/usr/bin/env python3
"""Compare captured official quotes; never estimate a missing quote."""

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import sys

CONTEXT_KEYS = ("storeCode", "beCode", "orderType", "beType", "reservationDate", "needTableware")


def whole(value, field, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"{field} 必须为整数")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number != number.to_integral_value() or number < minimum:
            raise ValueError(f"{field} 必须为不小于 {minimum} 的整数")
        return int(number)
    except InvalidOperation:
        raise ValueError(f"{field} 不是有效数字") from None


def yuan_to_fen(value):
    if isinstance(value, bool):
        raise ValueError("预算不是有效金额")
    try:
        amount = Decimal(str(value)) * 100
        if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
            raise ValueError("预算须大于零且精确到分")
        return int(amount)
    except InvalidOperation:
        raise ValueError("预算不是有效金额") from None


def quantities(items, code_key):
    if not isinstance(items, list) or not items:
        raise ValueError("餐品列表为空或缺失")
    result = Counter()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(code_key), str) or not item[code_key].strip():
            raise ValueError("餐品编码缺失")
        result[item[code_key]] += whole(item.get("quantity"), "quantity", minimum=1)
    return result


def compare(document):
    if not isinstance(document, dict):
        raise ValueError("输入必须为 JSON 对象")
    budget = yuan_to_fen(document.get("budget_yuan"))
    people = whole(document.get("people"), "people", minimum=1)
    context = document.get("context")
    if not isinstance(context, dict) or not isinstance(context.get("storeCode"), str) or not context["storeCode"].strip():
        raise ValueError("需要选定门店的 context")
    if (type(context.get("orderType")) is not int or type(context.get("beType")) is not int
            or (context.get("orderType"), context.get("beType")) not in ((1, 1), (2, 2))):
        raise ValueError("首版只比较到店自取或麦乐送")
    plans = document.get("plans")
    if not isinstance(plans, list) or not plans:
        raise ValueError("需要至少一个候选方案")
    accepted, rejected, signatures = [], [], set()
    for index, plan in enumerate(plans, start=1):
        label = plan.get("label", f"方案{index}") if isinstance(plan, dict) else f"方案{index}"
        try:
            if not isinstance(label, str) or not label.strip():
                raise ValueError("方案名称无效")
            if not isinstance(plan, dict) or plan.get("price_unit") != "fen":
                raise ValueError("须明确标记官方计价单位 price_unit=fen")
            request, response = plan.get("request"), plan.get("response")
            if not isinstance(request, dict) or not isinstance(response, dict):
                raise ValueError("缺少完整计价请求或业务响应")
            if any(request.get(key) != context.get(key) for key in CONTEXT_KEYS):
                raise ValueError("门店、取餐方式、预约时间或餐具上下文不一致")
            if response.get("success") is not True or response.get("code") != 200:
                raise ValueError("官方业务响应未成功")
            data = response.get("data")
            if not isinstance(data, dict):
                raise ValueError("官方业务响应缺少 data")
            requested = quantities(request.get("items"), "productCode")
            if quantities(data.get("productList"), "productCode") != requested:
                raise ValueError("返回餐品编码或数量与请求不一致")
            total = whole(data.get("price"), "data.price")
            signature = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if signature in signatures:
                raise ValueError("与已有方案的计价请求重复")
            quote_time = response.get("datetime")
            if not isinstance(quote_time, str) or not quote_time.strip():
                raise ValueError("缺少官方计价时间")
            signatures.add(signature)
            accepted.append({
                "label": label, "total_fen": total,
                "per_person_yuan": str((Decimal(total) / 100 / people).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
                "remaining_fen": budget - total, "within_budget": total <= budget,
                "quoted_at": quote_time,
                "items": [{"productName": item.get("productName", item["productCode"]),
                           "quantity": item["quantity"]} for item in data["productList"]],
            })
        except (ValueError, TypeError, KeyError) as error:
            rejected.append({"label": label, "reason": str(error)})
    accepted.sort(key=lambda row: row["total_fen"])
    return {"budget_fen": budget, "people": people,
            "plans": accepted, "rejected": rejected,
            "within_budget_count": sum(p["within_budget"] for p in accepted)}


def money(fen):
    return f"{Decimal(fen) / 100:.2f}"


def markdown(report):
    # Escape table delimiters and line breaks in upstream strings.
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = [f"总预算 ¥{money(report['budget_fen'])} · {report['people']} 人",
             "", "| 方案 | 官方总价 | 人均（四舍五入） | 预算余量 | 状态 | 计价时间 |",
             "|---|---:|---:|---:|---|---|"]
    for row in report["plans"]:
        state = "预算内" if row["within_budget"] else "超预算"
        lines.append(f"| {cell(row['label'])} | ¥{money(row['total_fen'])} | ¥{row['per_person_yuan']} | ¥{money(row['remaining_fen'])} | {state} | {cell(row['quoted_at'])} |")
    if not report["within_budget_count"]:
        lines.extend(["", "目前没有已成功核价且在预算内的方案。"])
    for row in report["rejected"]:
        lines.append(f"\n排除 {cell(row['label'])}：{cell(row['reason'])}。")
    lines.extend(["", "餐品份量、口味与逐人分配仍需对照用户需求确认。报价不代表已下单。"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = compare(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as error:
        print(f"无法核算（{type(error).__name__}），请检查输入格式。", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else markdown(report), end="\n" if args.json else "")
    return 0 if report["within_budget_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
