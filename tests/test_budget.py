"""Synthetic regression cases; these do not replace a live MCP quote."""

import asyncio
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest


def module(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


budget = module("budget_report")
client = module("mcd_readonly")


def sample(total=3000, code="sample-burger"):
    context = {"storeCode": "1234567", "orderType": 1, "beType": 1,
               "needTableware": False}
    request = dict(context, items=[{"productCode": code, "quantity": 2}])
    response = {"success": True, "code": 200, "datetime": "2026-10-24 12:00:00",
                "data": {"price": total, "deliveryPrice": 600, "tablewarePrice": 10,
                         "productList": [{"productCode": code, "productName": "模拟餐品",
                                          "quantity": 2}]}}
    return {"budget_yuan": "30.00", "people": 2, "context": context,
            "plans": [{"label": "模拟A", "price_unit": "fen", "request": request,
                       "response": response}]}


class QuoteComparisonTests(unittest.TestCase):
    def test_total_already_includes_fees_and_exact_budget(self):
        result = budget.compare(sample())
        self.assertEqual(result["plans"][0]["total_fen"], 3000)
        self.assertEqual(result["plans"][0]["remaining_fen"], 0)
        self.assertEqual(result["plans"][0]["per_person_yuan"], "15.00")
        self.assertEqual(result["within_budget_count"], 1)

    def test_one_cent_over_budget_not_recommended(self):
        result = budget.compare(sample(3001))
        self.assertEqual(result["within_budget_count"], 0)
        self.assertFalse(result["plans"][0]["within_budget"])

    def test_failed_business_response_never_accepted(self):
        data = sample()
        data["plans"][0]["response"]["success"] = False
        self.assertEqual(budget.compare(data)["plans"], [])

    def test_missing_price_never_estimated_from_items(self):
        data = sample()
        del data["plans"][0]["response"]["data"]["price"]
        self.assertEqual(budget.compare(data)["plans"], [])

    def test_wrong_product_and_quantity_rejected(self):
        for key, value in (("productCode", "different-code"), ("quantity", 1)):
            with self.subTest(key=key):
                data = sample()
                data["plans"][0]["response"]["data"]["productList"][0][key] = value
                self.assertEqual(budget.compare(data)["plans"], [])

    def test_store_fulfillment_time_and_tableware_must_match(self):
        for key, value in (("storeCode", "another-store"), ("orderType", 2),
                           ("beType", 2), ("reservationDate", "2026-10-25 12:00"),
                           ("needTableware", True)):
            with self.subTest(key=key):
                data = sample()
                data["plans"][0]["request"][key] = value
                self.assertEqual(budget.compare(data)["plans"], [])

    def test_invalid_amounts_do_not_become_zero(self):
        for value in (None, True, -1, "NaN", "Infinity", 2.5):
            with self.subTest(value=value):
                data = sample(value)
                self.assertEqual(budget.compare(data)["plans"], [])

    def test_invalid_budget_and_people_rejected(self):
        for key, value in (("budget_yuan", "0"), ("budget_yuan", "0.001"),
                           ("budget_yuan", "NaN"), ("people", 0),
                           ("people", True), ("people", 1.5)):
            with self.subTest(key=key, value=value):
                data = sample()
                data[key] = value
                with self.assertRaises(ValueError):
                    budget.compare(data)

    def test_bad_candidate_does_not_hide_success(self):
        data = sample()
        bad = deepcopy(data["plans"][0])
        bad["response"]["success"] = False
        data["plans"].insert(0, bad)
        self.assertEqual(budget.compare(data)["within_budget_count"], 1)

    def test_duplicate_requests_are_not_distinct_choices(self):
        data = sample()
        data["plans"].append(deepcopy(data["plans"][0]))
        self.assertEqual(len(budget.compare(data)["plans"]), 1)

    def test_missing_quote_time_does_not_poison_later_valid_quote(self):
        data = sample()
        bad = deepcopy(data["plans"][0])
        del bad["response"]["datetime"]
        data["plans"].insert(0, bad)
        self.assertEqual(len(budget.compare(data)["plans"]), 1)

    def test_explicit_unit_required(self):
        data = sample()
        data["plans"][0]["price_unit"] = "yuan"
        self.assertEqual(budget.compare(data)["plans"], [])


class ClientBoundaryTests(unittest.TestCase):
    def test_write_tools_rejected_before_network_or_imports(self):
        for tool in ("create-order", "cancel-order", "draw-lottery", "auto-bind-coupons"):
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                asyncio.run(client.invoke("call", "synthetic-only", tool, {}))

    def test_mcp_error_cannot_be_unwrapped_as_success(self):
        result = {"isError": True, "structuredContent": {"success": True, "code": 200}}
        self.assertIsNone(client.business_payload(result))

    def test_json_text_is_unwrapped_but_ambiguous_objects_are_not(self):
        block = {"type": "text", "text": json.dumps({"success": True, "code": 200})}
        self.assertTrue(client.business_payload({"content": [block]})["success"])
        self.assertIsNone(client.business_payload({"content": [block, block]}))

    def test_private_results_do_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            client.private_write(path, {"example": 1})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(FileExistsError):
                client.private_write(path, {"example": 2})
            self.assertEqual(json.loads(path.read_text()), {"example": 1})


if __name__ == "__main__":
    unittest.main()
