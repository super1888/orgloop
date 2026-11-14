"""Regression controls for demonstrated static-check blind spots, not app tests."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DesignCheckRegression(unittest.TestCase):
    def setUp(self):
        local = ROOT / ".local" / "checker-tests"
        local.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=local)
        self.root = Path(self.temp.name) / "case"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", ".local", ".venv", "node_modules", "__pycache__"))

    def tearDown(self):
        self.temp.cleanup()

    def edit_json(self, name, change):
        path = self.root / name
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def expect(self, exit_code, checker="check_docs.py"):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / checker), "--root", str(self.root)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, exit_code, result.stdout[-2500:] + result.stderr[-1000:])
        return result

    def test_valid_baseline(self):
        self.expect(0)

    def test_missing_inherited_authentication_is_rejected(self):
        self.edit_json("contracts/openapi.json", lambda spec: spec.pop("security"))
        self.expect(1)

    def test_route_requirement_drift_is_rejected(self):
        self.edit_json("contracts/openapi.json", lambda spec: spec["paths"]["/v1/work-items"]["post"].update({"x-requirements": ["REQ-002"]}))
        self.expect(1)

    def test_missing_if_match_is_rejected(self):
        def change(spec):
            operation = spec["paths"]["/v1/work-items/{id}"]["patch"]
            operation["parameters"] = [p for p in operation["parameters"] if p.get("$ref") != "#/components/parameters/IfMatch"]
        self.edit_json("contracts/openapi.json", change)
        self.expect(1)

    def test_fabricated_application_pass_is_rejected(self):
        self.edit_json("evals/scenarios.json", lambda suite: suite["cases"][0].update({"execution_status": "passed"}))
        self.expect(1)

    def test_missing_delegatee_requirement_is_rejected(self):
        self.edit_json("contracts/openapi.json", lambda spec: spec["components"]["schemas"]["AuthorizationCreate"]["required"].remove("delegatee_id"))
        self.expect(1)

    def test_missing_receipt_route_is_rejected(self):
        self.edit_json("contracts/openapi.json", lambda spec: spec["paths"].pop("/v1/action-receipts/{id}"))
        self.expect(1)

    def test_broken_document_link_is_rejected(self):
        path = self.root / "README.md"
        path.write_text(path.read_text() + "\n[broken](docs/not-present.md)\n")
        self.expect(1)

    def test_incorrect_budget_is_rejected(self):
        self.edit_json("pricing/scenarios.json", lambda values: values["monthly_cases"][0]["expected_model_cost_usd"].update({"openai_luna_standard_short": 6.07}))
        self.expect(1, "check_costs.py")

    def test_legitimate_neighboring_title_change_is_allowed(self):
        self.edit_json("contracts/examples.json", lambda examples: examples["examples"][0]["value"].update({"title": "另一项合法的合成目标"}))
        self.expect(0)


if __name__ == "__main__":
    unittest.main()
