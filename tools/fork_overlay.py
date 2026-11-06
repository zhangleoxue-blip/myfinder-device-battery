#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replay declarative overlay patches after every upstream sync.

The fork is additive: new files only. The rare case that must edit an upstream
source file is expressed as a patch descriptor under overlay/patches/ and is
re-applied automatically after each rebase, so upstream changes to that file
do not silently drop the fork's customization.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "fork-config.json"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def report_path(cfg):
    path = ROOT / cfg["paths"]["overlayReport"]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_text_preserving_bom(path):
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw.decode("utf-8-sig" if bom else "utf-8"), bom


def write_text_preserving_bom(path, text, bom):
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def apply_patch(spec):
    target = ROOT / spec["target"]
    if not target.is_file():
        raise RuntimeError("target file missing: {}".format(spec["target"]))
    text, bom = read_text_preserving_bom(target)
    matches = list(re.finditer(spec["pattern"], text))
    if len(matches) != 1:
        raise RuntimeError("anchor matched {} times (expected exactly 1); "
                           "upstream changed the file, review manually".format(len(matches)))

    values = dict(spec.get("values", {}))
    key_file_spec = spec.get("keyFile")
    if key_file_spec:
        key_file = ROOT / key_file_spec
        if not key_file.is_file():
            raise RuntimeError("key file missing: {} (run tools/fork_keys.ps1 first)".format(key_file_spec))
        key_xml = key_file.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"<RSAKeyValue>.*</RSAKeyValue>", key_xml, re.DOTALL):
            raise RuntimeError("public key file is not a valid RSAKeyValue XML blob")
        values["PUBLIC_KEY_XML"] = key_xml

    match = matches[0]
    # {MATCH} lets a descriptor append to an anchor without restating it.
    values["MATCH"] = match.group(0)
    replacement = spec["template"]
    for name, value in values.items():
        replacement = replacement.replace("{" + name + "}", value)

    # Append-style templates keep their anchor in the replacement, so the regex
    # would match again on the next run and insert the same lines twice. Treat
    # "the added text is already present" as an already-applied patch.
    appended = replacement.replace(match.group(0), "", 1).strip()
    if appended and appended in text:
        return "already-applied"

    updated = text[:match.start()] + replacement + text[match.end():]
    if updated == text:
        return "already-applied"
    write_text_preserving_bom(target, updated, bom)
    return "applied"


def command_apply(cfg):
    patches_dir = ROOT / cfg["paths"]["patches"]
    report = {"schema": 1, "utc": utcnow(), "total": 0, "applied": 0,
              "unchanged": 0, "skipped": 0, "failed": 0, "patches": []}
    for descriptor in sorted(patches_dir.glob("*.json")):
        spec = json.loads(descriptor.read_text(encoding="utf-8"))
        report["total"] += 1
        entry = {"id": spec.get("id", descriptor.stem), "result": ""}
        if not spec.get("enabled", False):
            entry["result"] = "skipped (disabled by policy)"
            report["skipped"] += 1
        else:
            try:
                entry["result"] = apply_patch(spec)
                if entry["result"] == "applied":
                    report["applied"] += 1
                elif entry["result"] == "already-applied":
                    report["unchanged"] += 1
            except Exception as exc:
                entry["result"] = "failed: {}".format(exc)
                report["failed"] += 1
        report["patches"].append(entry)

    path = report_path(cfg)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[overlay] total={} applied={} unchanged={} skipped={} failed={} -> {}".format(
        report["total"], report["applied"], report["unchanged"],
        report["skipped"], report["failed"], path))
    for entry in report["patches"]:
        print("  - {}: {}".format(entry["id"], entry["result"]))
    return 0 if report["failed"] == 0 else 1


def command_verify(cfg):
    branding = json.loads((ROOT / cfg["paths"]["overlay"] / "branding.json").read_text(encoding="utf-8"))
    missing = []
    for relative in branding.get("customFiles", []):
        if not (ROOT / relative).exists():
            missing.append(relative)
    print("[overlay] fork-owned files: {} checked, {} missing".format(
        len(branding.get("customFiles", [])), len(missing)))
    for item in missing:
        print("  MISSING: {}".format(item))
    return 0 if not missing else 1


def main():
    parser = argparse.ArgumentParser(description="Replay fork overlay patches.")
    parser.add_argument("action", choices=["apply", "verify"])
    args = parser.parse_args()
    cfg = load_config()
    if args.action == "apply":
        return command_apply(cfg)
    return command_verify(cfg)


if __name__ == "__main__":
    sys.exit(main())
