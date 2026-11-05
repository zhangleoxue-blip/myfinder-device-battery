#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-check for the declarative overlay patch replayer.

Runs entirely inside a temporary directory, so no upstream source file in the
real repository is ever modified. Verifies three behaviours:
  1. an enabled patch replaces exactly one anchored constant;
  2. applying the same patch twice is idempotent;
  3. a vanished anchor is reported as a failure instead of being skipped.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_KEY = '<RSAKeyValue><Modulus>ORIGINAL</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>'
REPLACED_KEY = '<RSAKeyValue><Modulus>REPLACED</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>'


def build_fixture(root):
    (root / "tools").mkdir(parents=True)
    shutil.copy2(ROOT / "tools" / "fork_overlay.py", root / "tools" / "fork_overlay.py")

    config = {"schema": 1, "paths": {
        "patches": "overlay/patches",
        "overlayReport": "logs/fork/overlay-report.json",
        "keys": "logs/fork/keys",
        "overlay": "overlay",
    }}
    (root / "fork-config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    patch = {
        "schema": 1,
        "id": "test-public-key",
        "enabled": True,
        "target": "scripts/UpdateValidation.cs",
        "strategy": "regex-replace",
        "pattern": 'internal const string PublicKeyXml = @"[^"]+";',
        "template": 'internal const string PublicKeyXml = @"{PUBLIC_KEY_XML}";',
        "keyFile": "logs/fork/keys/public.xml",
    }
    (root / "overlay" / "patches").mkdir(parents=True)
    (root / "overlay" / "patches" / "test.json").write_text(
        json.dumps(patch, indent=2), encoding="utf-8")

    (root / "scripts").mkdir()
    (root / "scripts" / "UpdateValidation.cs").write_text(
        "namespace AtkBattery {\n    internal static class UpdateTrust {\n"
        '        internal const string PublicKeyXml = @"' + ORIGINAL_KEY + '";\n'
        "    }\n}\n", encoding="utf-8")

    (root / "logs" / "fork" / "keys").mkdir(parents=True)
    (root / "logs" / "fork" / "keys" / "public.xml").write_text(
        REPLACED_KEY, encoding="utf-8")


def run_apply(root):
    return subprocess.run(
        [sys.executable, str(root / "tools" / "fork_overlay.py"), "apply"],
        cwd=str(root), capture_output=True, text=True,
        encoding="utf-8", errors="replace")


def read_report(root):
    return json.loads((root / "logs" / "fork" / "overlay-report.json").read_text(encoding="utf-8"))


def main():
    with tempfile.TemporaryDirectory(prefix="fork-overlay-test-") as tmp:
        root = Path(tmp)
        build_fixture(root)
        failures = []

        first = run_apply(root)
        first_report = read_report(root)
        if first.returncode != 0 or first_report.get("applied") != 1 or first_report.get("failed") != 0:
            failures.append("first apply did not apply exactly one patch: {}".format(first_report))
        content = (root / "scripts" / "UpdateValidation.cs").read_text(encoding="utf-8")
        if REPLACED_KEY not in content or "ORIGINAL" in content:
            failures.append("public key constant was not replaced")

        second = run_apply(root)
        second_report = read_report(root)
        results = [item.get("result") for item in second_report.get("patches", [])]
        if second.returncode != 0 or results != ["already-applied"]:
            failures.append("second apply is not idempotent: {}".format(second_report))

        (root / "scripts" / "UpdateValidation.cs").write_text("anchor removed\n", encoding="utf-8")
        third = run_apply(root)
        third_report = read_report(root)
        if third.returncode == 0 or third_report.get("failed") != 1:
            failures.append("missing anchor was not reported as a failure: {}".format(third_report))

        for failure in failures:
            print("FAIL:", failure)
        if failures:
            return 1
        print("PASS 3 overlay patch checks: apply, idempotency, missing-anchor detection")
        return 0


if __name__ == "__main__":
    sys.exit(main())
