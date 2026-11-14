#!/usr/bin/env python3
"""Recalculate public price snapshots; does not verify live prices or capacity."""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

D = lambda value: Decimal(str(value))


def check(root: Path):
    rates = json.loads((root / "pricing/rates.json").read_text(), parse_float=Decimal)
    scenarios = json.loads((root / "pricing/scenarios.json").read_text(), parse_float=Decimal)
    sources = (root / "docs/SOURCES.md").read_text()
    errors, checks, results = [], 0, []

    def equal(label, calculated, expected, tolerance=Decimal("0.000001")):
        nonlocal checks
        checks += 1
        if abs(D(calculated) - D(expected)) > tolerance:
            errors.append(f"{label}: calculated={calculated}, expected={expected}")

    if rates["currency"] != "USD" or rates["as_of_date"] != scenarios["as_of_date"]:
        errors.append("price/scenario currency or date mismatch")
    for group in ("token_rates", "embedding_rates", "infrastructure_rates", "external_tool_rates"):
        for name, rate in rates[group].items():
            checks += 1
            if rate.get("source_id", "MISSING") not in sources:
                errors.append(f"{name}: missing source citation")
            for key in ("input_per_million", "output_per_million", "amount"):
                if key in rate and D(rate[key]) < 0:
                    errors.append(f"{name}: negative unit price")
    a = scenarios["assumptions"]
    for case in scenarios["monthly_cases"]:
        input_tokens = D(case["matters"]) * D(a["model_calls_per_matter"]) * D(a["input_tokens_per_call"]) * (1 + D(a["extra_token_budget_ratio"]))
        output_tokens = D(case["matters"]) * D(a["model_calls_per_matter"]) * D(a["billable_output_tokens_per_call"]) * (1 + D(a["extra_token_budget_ratio"]))
        hours = D(case["matters"]) * D(a["human_review_fraction"]) * D(a["minutes_per_human_review"]) / 60
        equal(f"{case['id']} input", input_tokens, case["expected_input_tokens"])
        equal(f"{case['id']} output", output_tokens, case["expected_billable_output_tokens"])
        equal(f"{case['id']} human", hours, case["expected_human_review_hours"])
        cost = {}
        for name, rate in rates["token_rates"].items():
            value = (input_tokens * D(rate["input_per_million"]) + output_tokens * D(rate["output_per_million"])) / 1_000_000
            equal(f"{case['id']} {name}", value, case["expected_model_cost_usd"][name])
            cost[name] = value
        for name, mix in scenarios["mixes"].items():
            equal(f"{name} shares", sum(map(D, mix["weights"].values())), 1)
            value = sum(cost[model] * D(weight) for model, weight in mix["weights"].items())
            equal(f"{case['id']} {name}", value, case["expected_mix_cost_usd"][name])
        results.append({"case": case["id"], "input_tokens": str(input_tokens), "output_tokens": str(output_tokens), "human_hours": str(hours)})
    for case in scenarios["infrastructure_cases"]:
        total = D(0)
        for component in case["components"]:
            name, quantity = component["rate_id"], D(component["quantity"])
            if quantity < 0 and "credit" not in name:
                errors.append(f"{case['id']}: negative quantity not a declared credit")
            total += D(rates["infrastructure_rates"][name]["amount"]) * quantity
        equal(f"{case['id']} infrastructure", total, case["expected_monthly_usd"])
        s = case["storage_assumption"]
        total_storage = sum(D(s[key]) for key in ("document_primary_gb_month", "document_backup_gb_month", "database_export_gb_month"))
        equal(f"{case['id']} total storage", total_storage, s["total_gb_month"])
        billed = max(D(0), total_storage - D(s["included_gb_month_applied_once"]))
        equal(f"{case['id']} billable storage", billed, s["billable_gb_month"])
        if D(s["included_gb_month_applied_once"]) > D(rates["infrastructure_rates"]["r2_standard_storage"]["included_gb_month_per_account"]):
            errors.append(f"{case['id']}: account free storage applied more than once")
        components = {item["rate_id"]: item["quantity"] for item in case["components"]}
        equal(f"{case['id']} charged R2 volume", components["r2_standard_storage"], billed)
        for kind in ("a", "b"):
            rate = rates["infrastructure_rates"][f"r2_standard_class_{kind}"]
            operations = D(s[f"class_{kind}_operations_per_account_month"])
            if operations > D(rate["included_operations_per_account_month"]):
                errors.append(f"{case['id']}: R2 operations exceed included quota but no charge is included")
    embedding = scenarios["embedding_case"]
    embedding_cost = D(embedding["one_time_input_tokens"]) * D(rates["embedding_rates"][embedding["rate_id"]]["input_per_million"]) / 1_000_000
    equal("embedding", embedding_cost, embedding["expected_one_time_usd"])
    return {"scope": "budget_arithmetic_not_live_prices_capacity_or_business_roi", "passed": not errors, "checks": checks, "results": results, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = check(args.root.resolve())
    except (KeyError, ValueError, OSError, ArithmeticError) as exc:
        result = {"passed": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
