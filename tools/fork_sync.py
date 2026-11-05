#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upstream sync controller for the MyFinder Device Battery fork.

Modes:
  --check   read-only: query GitHub, compare SHAs, refresh report and state
  --sync    fetch upstream, rebase fork/main onto upstream/main, replay overlay
            patches, refresh report/state/history/changelog
  --status  print the current state file

Design constraints:
  * Every fork-owned file is ADDITIVE. No upstream source file is edited by
    default, so `git rebase upstream/main` stays conflict-free.
  * This machine has a global git http.proxy pointing at an offline local
    proxy. Every git invocation clears it because direct HTTPS works here.
  * Standard library only; no third-party dependencies.
"""

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "fork-config.json"


class SyncError(Exception):
    pass


def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def localnow():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).replace(microsecond=0).isoformat()


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def output_path(cfg, key):
    path = ROOT / cfg["paths"][key]
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_executable(cfg):
    configured = cfg.get("gitExecutable", "")
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("git")
    if found:
        return found
    candidates = (
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\mingw64\bin\git.exe",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Programs\WorkBuddy\resources\vendor\PortableGit\mingw64\bin\git.exe"
        ),
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise SyncError("git executable not found; set gitExecutable in fork-config.json")


def git(cfg, *args, check=True):
    cmd = [git_executable(cfg)]
    if cfg["sync"].get("disableProxy", True):
        cmd += ["-c", "http.proxy=", "-c", "https.proxy="]
    cmd += list(args)
    env = os.environ.copy()
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                "ALL_PROXY", "all_proxy"):
        env[key] = ""
    proc = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:600]
        raise SyncError("git {} failed ({}): {}".format(" ".join(args), proc.returncode, detail))
    return proc


def http_json(cfg, endpoint):
    url = cfg["upstream"]["api"] + endpoint
    request = urllib.request.Request(url, headers={
        "User-Agent": "myfinder-fork-sync/1.0",
        "Accept": "application/vnd.github+json",
    })
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SyncError("GitHub API {} returned HTTP {}".format(endpoint, exc.code))
    except Exception as exc:
        raise SyncError("GitHub API {} failed: {}".format(endpoint, exc))


def http_raw(cfg, relative):
    upstream = cfg["upstream"]
    url = "{}/{}/{}/{}/{}".format(upstream["raw"], upstream["owner"],
                                  upstream["repo"], upstream["branch"], relative)
    request = urllib.request.Request(url, headers={"User-Agent": "myfinder-fork-sync/1.0"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=25) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        raise SyncError("raw fetch {} failed: {}".format(url, exc))


def collect_intel(cfg):
    """Best-effort GitHub intelligence. API failure never blocks a local sync."""
    upstream = cfg["upstream"]
    repo = "/repos/{}/{}".format(upstream["owner"], upstream["repo"])
    intel = {"remoteHeadSha": "", "recentCommits": [], "releases": [],
             "releaseJson": None, "apiError": ""}
    try:
        head = http_json(cfg, repo + "/commits/" + upstream["branch"])
        intel["remoteHeadSha"] = head.get("sha", "")
        commits = http_json(cfg, repo + "/commits?sha=" + upstream["branch"]
                            + "&per_page=" + str(cfg["sync"]["maxCommitsInReport"]))
        intel["recentCommits"] = [{
            "sha": item.get("sha", "")[:12],
            "date": (item.get("commit", {}).get("committer", {}) or {}).get("date", ""),
            "message": (item.get("commit", {}) or {}).get("message", "").splitlines()[0][:120],
        } for item in commits if isinstance(item, dict)]
        releases = http_json(cfg, repo + "/releases?per_page=10")
        intel["releases"] = [{
            "tag": item.get("tag_name", ""),
            "name": item.get("name", ""),
            "publishedAt": item.get("published_at", ""),
            "prerelease": bool(item.get("prerelease")),
        } for item in releases if isinstance(item, dict)]
        intel["releaseJson"] = json.loads(http_raw(cfg, "release.json"))
    except Exception as exc:
        intel["apiError"] = str(exc)
    return intel


def git_context(cfg):
    upstream_ref = cfg["upstream"]["remote"] + "/" + cfg["upstream"]["branch"]
    # Build artifacts are intentionally untracked. Only real fork source edits
    # should block a rebase, so filter known generated paths explicitly.
    status_lines = [line for line in git(cfg, "status", "--porcelain").stdout.splitlines()
                    if line.strip()]
    ignored = tuple(cfg["sync"].get("ignoreDirtyPaths", []))
    dirty_lines = [line for line in status_lines
                   if not any(line[3:].strip().startswith(prefix) for prefix in ignored)]
    ctx = {
        "branch": git(cfg, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
        "forkHead": git(cfg, "rev-parse", "HEAD").stdout.strip(),
        "upstreamSha": "",
        "customCommits": 0,
        "dirty": "\n".join(dirty_lines),
        "upstreamRef": upstream_ref,
    }
    probe = git(cfg, "rev-parse", upstream_ref, check=False)
    if probe.returncode == 0:
        ctx["upstreamSha"] = probe.stdout.strip()
        count = git(cfg, "rev-list", "--count", upstream_ref + "..HEAD", check=False)
        if count.returncode == 0 and count.stdout.strip().isdigit():
            ctx["customCommits"] = int(count.stdout.strip())
    return ctx


def ensure_upstream_remote(cfg):
    remotes = git(cfg, "remote").stdout.split()
    name = cfg["upstream"]["remote"]
    url = cfg["upstream"]["url"]
    if name in remotes:
        current = git(cfg, "remote", "get-url", name).stdout.strip()
        if current != url:
            git(cfg, "remote", "set-url", name, url)
        return "existing"
    git(cfg, "remote", "add", name, url)
    return "added"


def replay_overlay(cfg):
    script = ROOT / "tools" / "fork_overlay.py"
    proc = subprocess.run([sys.executable, str(script), "apply"],
                          cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    report_path = output_path(cfg, "overlayReport")
    if report_path.is_file():
        try:
            return json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"returncode": proc.returncode,
            "stdout": (proc.stdout or "").strip()[-800:],
            "stderr": (proc.stderr or "").strip()[-800:]}


def run_build(cfg):
    powershell = shutil.which("powershell.exe") or \
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    script = ROOT / "tools" / "fork_build.ps1"
    args = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
            "-OutputDirectory", str(ROOT / cfg["paths"]["buildOutput"])]
    if cfg["sync"].get("allowMissingPwsh", False):
        args.append("-AllowMissingPwsh")
    try:
        proc = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=900)
        return {"attempted": True, "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-12000:],
                "stderr": (proc.stderr or "")[-4000:]}
    except subprocess.TimeoutExpired:
        return {"attempted": True, "returncode": -1,
                "stdout": "", "stderr": "Build exceeded the 900 second timeout."}
    except Exception as exc:
        return {"attempted": True, "returncode": -1, "stdout": "", "stderr": str(exc)}


def load_state(cfg):
    path = output_path(cfg, "state")
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema": 1, "lastSyncedSha": "", "lastSyncUtc": "", "lastCheckUtc": ""}


def build_report(cfg, state, intel, ctx, action, conflicts, overlay, build):
    upstream = cfg["upstream"]
    latest = intel["releases"][0] if intel["releases"] else {}
    version = (intel["releaseJson"] or {}).get("version", "unknown")
    status_text = {
        "check": "只读检查（未改动工作区）",
        "up-to-date": "上游无新提交，无需 rebase",
        "rebased": "已 rebase 到上游最新提交",
        "conflict": "rebase 冲突，已自动回滚，需人工处理",
        "build-failed": "同步完成但构建失败",
        "error": "同步失败",
    }.get(action, action)

    lines = [
        "# 上游同步报告",
        "",
        "- 生成时间：{}（北京时间） / {}（UTC）".format(localnow(), utcnow()),
        "- 上游仓库：`{}/{}`，分支 `{}`".format(upstream["owner"], upstream["repo"], upstream["branch"]),
        "- 本地分支：`{}`".format(ctx["branch"]),
        "- 同步动作：**{}** — {}".format(action, status_text),
        "",
        "## 版本情报",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| 上游远端 HEAD | `{}` |".format(intel["remoteHeadSha"] or "API 不可用"),
        "| 本地 upstream 跟踪 | `{}` |".format(ctx["upstreamSha"] or "未建立"),
        "| fork HEAD | `{}` |".format(ctx["forkHead"]),
        "| 上次同步基线 | `{}` |".format(state.get("lastSyncedSha") or "无记录"),
        "| release.json 版本 | `{}` |".format(version),
        "| 最新 Release | {} |".format(
            "`{}` ({}, {})".format(latest.get("tag", "-"), latest.get("publishedAt", "-"),
                                   "预发布" if latest.get("prerelease") else "正式版")
            if latest else "-"),
        "| fork 定制提交数 | {} |".format(ctx["customCommits"]),
        "| 工作区 | {} |".format("干净" if not ctx["dirty"] else "有未提交改动"),
        "",
    ]
    if intel["apiError"]:
        lines += ["> GitHub API 读取失败：{}。本地 git 信息仍然有效。".format(intel["apiError"]), ""]

    lines += ["## 最近上游提交", ""]
    if intel["recentCommits"]:
        for item in intel["recentCommits"][:cfg["sync"]["maxCommitsInReport"]]:
            lines.append("- `{}` {} {}".format(item["sha"], item["date"][:19], item["message"]))
    else:
        lines.append("- 未取得提交列表。")
    lines.append("")

    lines += ["## 定制层重放", ""]
    if isinstance(overlay, dict) and "patches" in overlay:
        lines += [
            "- 补丁总数：{}；启用：{}；跳过：{}；失败：{}".format(
                overlay.get("total", 0), overlay.get("applied", 0),
                overlay.get("skipped", 0), overlay.get("failed", 0)),
            "- 策略：只新增文件，不改动上游源码（`overlay/patches/trust-key.json` 默认关闭）。",
        ]
        for item in overlay.get("patches", []):
            lines.append("  - `{}` → {}".format(item.get("id"), item.get("result")))
    else:
        lines.append("- 未取得补丁报告：{}".format((overlay or {}).get("stderr", "unknown")))
    lines.append("")

    if conflicts:
        lines += ["## 冲突文件", ""] + ["- `{}`".format(name) for name in conflicts] + [
            "", "已执行 `git rebase --abort`，工作区恢复到同步前状态。", ""]

    if build and build.get("attempted"):
        raw_lines = ((build.get("stdout") or "") + "\n" + (build.get("stderr") or "")).splitlines()
        signal = [line.strip() for line in raw_lines
                  if line.strip() and "warning CS" not in line
                  and any(word in line for word in
                          ("PASS", "FAIL", "PARTIAL", "succeeded", "failed", "checks,"))]
        summary = " / ".join(signal[-8:])[:700] or "无关键输出"
        lines += ["## 构建", "",
                  "- 返回码：`{}`".format(build.get("returncode")),
                  "- 关键结果：{}".format(summary),
                  ""]

    lines += [
        "## 两条同步链路",
        "",
        "1. **代码层**：本脚本把 `fork/main` rebase 到 `upstream/main`，上游功能与协议修复自动进入你的源码。",
        "2. **二进制层**：上游 `scripts/UpdateValidation.cs` 把 `UpdateTrust.ApiUrl` 与验签公钥硬编码为上游仓库，"
        "所以已安装的 fork 构建会直接检查并一键更新到上游官方 Release。保持 `AppId` / `ZipName` / `ApiUrl` 不变是这条链路生效的前提。",
        "",
        "## 合规与注意",
        "",
        "- 本 fork 派生自 `wushuai0802/myfinder-device-battery`，许可为 **AGPL-3.0-only**，"
        "再分发必须同许可开源并提供完整源码地址，不得闭源。",
        "- 不要替换签名公钥，除非你同时接管整条发布通道（详见 `overlay/patches/trust-key.json`）。",
        "- 上游新增设备多数标注「尚未实机验证」，同步后请以真机读数为准，不要直接对外宣称兼容。",
        "",
        "## 下一步",
        "",
        "- 有新提交时：运行 `python tools/fork_sync.py --sync --build`。",
        "- 配置自己的远端：设置 `fork-config.json` 的 `fork.origin` 后推送 `fork/main`。",
        "- 定时执行：启用 `.github/workflows/fork-sync.yml`。",
        "",
    ]
    return "\n".join(lines)


def write_changelog(cfg, intel):
    lines = ["# 上游近期变更（自动生成）", "",
             "来源：`{}/{}` 的 `{}` 分支，由 `tools/fork_sync.py` 通过 GitHub API 拉取。".format(
                 cfg["upstream"]["owner"], cfg["upstream"]["repo"], cfg["upstream"]["branch"]),
             "", "生成时间：{}".format(localnow()), ""]
    for item in intel["recentCommits"]:
        lines.append("- `{}` {} {}".format(item["sha"], item["date"][:19], item["message"]))
    if intel["releases"]:
        lines += ["", "## 最近 Release", ""]
        for rel in intel["releases"]:
            lines.append("- `{}` {} {} {}".format(
                rel["tag"], rel["name"], rel["publishedAt"][:19],
                "(prerelease)" if rel["prerelease"] else "(stable)"))
    lines.append("")
    return "\n".join(lines)


def persist(cfg, state, intel, ctx, action, conflicts, overlay, build):
    write_text(output_path(cfg, "state"), json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    write_text(output_path(cfg, "report"),
               build_report(cfg, state, intel, ctx, action, conflicts, overlay, build))
    write_text(output_path(cfg, "changelog"), write_changelog(cfg, intel))
    history = output_path(cfg, "history")
    record = {"utc": utcnow(), "action": action,
              "upstreamSha": ctx["upstreamSha"], "forkHead": ctx["forkHead"],
              "remoteHeadSha": intel["remoteHeadSha"],
              "version": (intel["releaseJson"] or {}).get("version", ""),
              "customCommits": ctx["customCommits"], "conflicts": conflicts}
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def command_check(cfg, args):
    intel = collect_intel(cfg)
    ctx = git_context(cfg)
    state = load_state(cfg)
    state["lastCheckUtc"] = utcnow()
    persist(cfg, state, intel, ctx, "check", [], {}, None)
    print("[check] action=check remote={} upstream={} fork={} custom={}".format(
        intel["remoteHeadSha"][:12] or "n/a", ctx["upstreamSha"][:12] or "n/a",
        ctx["forkHead"][:12], ctx["customCommits"]))
    print("[check] report -> {}".format(output_path(cfg, "report")))
    return 0


def command_sync(cfg, args):
    intel = collect_intel(cfg)
    state = load_state(cfg)
    ctx = git_context(cfg)
    overlay = {}
    build = None
    conflicts = []
    action = "error"

    try:
        remote_state = ensure_upstream_remote(cfg)
        ctx = git_context(cfg)
        if ctx["branch"] != cfg["fork"]["branch"]:
            raise SyncError("expected branch {} but found {}".format(cfg["fork"]["branch"], ctx["branch"]))
        if ctx["dirty"]:
            raise SyncError("worktree has uncommitted changes; commit or stash them before --sync")

        git(cfg, "fetch", cfg["upstream"]["remote"])
        ctx = git_context(cfg)
        target = ctx["upstreamSha"]
        if not target:
            raise SyncError("upstream tracking ref is missing after fetch")

        base = git(cfg, "merge-base", "HEAD", ctx["upstreamRef"]).stdout.strip()
        if base == target:
            action = "up-to-date"
        else:
            result = git(cfg, "rebase", ctx["upstreamRef"], check=False)
            if result.returncode != 0:
                conflict_out = git(cfg, "diff", "--name-only", "--diff-filter=U", check=False)
                conflicts = [line for line in conflict_out.stdout.strip().splitlines() if line]
                git(cfg, "rebase", "--abort", check=False)
                action = "conflict"
            else:
                action = "rebased"

        if action != "conflict":
            overlay = replay_overlay(cfg)
            if args.build or cfg["sync"].get("autoBuild", False):
                build = run_build(cfg)
                if build.get("returncode") not in (0,):
                    action = "build-failed"

        ctx = git_context(cfg)
        state["lastSyncUtc"] = utcnow()
        state["remoteState"] = remote_state
        if action in ("rebased", "up-to-date", "build-failed"):
            state["lastSyncedSha"] = target
        state["status"] = action
    except SyncError as exc:
        state["error"] = str(exc)
        action = "error"
        print("[sync] ERROR: {}".format(exc), file=sys.stderr)
    except Exception as exc:
        state["error"] = str(exc)
        action = "error"
        print("[sync] ERROR: {}".format(exc), file=sys.stderr)

    state["lastCheckUtc"] = utcnow()
    persist(cfg, state, intel, ctx, action, conflicts, overlay, build)
    print("[sync] action={} upstream={} fork={} custom={} conflicts={}".format(
        action, ctx["upstreamSha"][:12] or "n/a", ctx["forkHead"][:12],
        ctx["customCommits"], len(conflicts)))
    print("[sync] report -> {}".format(output_path(cfg, "report")))
    return 0 if action in ("check", "up-to-date", "rebased") else 1


def command_status(cfg, args):
    state = load_state(cfg)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Sync the fork with upstream.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only check")
    mode.add_argument("--sync", action="store_true", help="fetch and rebase")
    mode.add_argument("--status", action="store_true", help="print state")
    parser.add_argument("--build", action="store_true", help="run build after a successful sync")
    args = parser.parse_args()
    cfg = load_config()
    try:
        if args.check:
            return command_check(cfg, args)
        if args.sync:
            return command_sync(cfg, args)
        return command_status(cfg, args)
    except SyncError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
