# MyFinder Device Battery — LeoZhang 独立发布版

本仓库是 `wushuai0802/myfinder-device-battery` 的**修改派生版**，由 **LeoZhang** 维护并以
`AGPL-3.0-only` 发布。产品名、图标、`AppId` 与包名沿用上游；**发布通道、验签公钥、程序内源码/文档链接
与署名已切换到本仓库**。完整署名、许可与修改声明见 [CREDITS.md](CREDITS.md)。

> 这是**非官方构建**，不接收上游签名发行包，也不由上游维护者背书。

## 当前状态（2026-11-06）

| 项 | 值 |
| --- | --- |
| 上游基线 | `3a2a63ecd981`（`release.json` = 1.3.9-beta.7） |
| 默认分支 | `fork/main`（通过 GitHub API 设置；新版 UI 在 Settings → General 底部） |
| 署名 | `Copyright (C) 2026 LeoZhang`，保留上游与第三方署名 |
| 定制策略 | 只新增文件 + 11 个已启用的声明式补丁（另 3 个默认关闭） |
| 自动同步 | `.github/workflows/fork-sync.yml` 每小时 17 分，`workflow_dispatch` 实测全绿 |
| 发行流水线 | `.github/workflows/fork-release.yml`（已建，尚未发布首个签名 Release） |
| 公钥 | `overlay/keys/public.xml`（入库）；私钥只在 `logs/fork/keys/private.xml`（已忽略） |
| 许可 | AGPL-3.0-only，`LICENSE` / `THIRD_PARTY_NOTICES.md` 原样保留 |

对外发布前必读：[docs/fork/COMPLIANCE.md](docs/fork/COMPLIANCE.md)。分阶段计划见
[docs/fork/ROADMAP.md](docs/fork/ROADMAP.md)。

## 两条链路（当前真实状态）

```
代码层：upstream/main ──fetch──> git rebase ──> fork/main ──> 构建/发行
                                    │
                                    └─> fork_overlay.py 重放 11 个补丁

二进制层：已安装的 LeoZhang 版 ──UpdateTrust.ApiUrl──> 本仓库 Releases API
                              ──> SHA256SUMS.txt.sig（LeoZhang 公钥）
                              ──> 只更新到本仓库的签名发行包
```

数据层（型号数据包 `device-pack`）仍从上游镜像/Release 拉取，由上游独立公钥验证——这是刻意保留的
兼容数据同步，与应用更新信任链互不相关。程序内「反馈问题」也仍走上游中继，见下文「已知决策项」。

## 快速开始（同步与自检）

在仓库根目录执行。Python 用本机 venv（仅标准库）：

```bash
PY="C:/Users/admin/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

$PY tools/test_fork_overlay.py          # 补丁机制自检（4 项）
$PY tools/fork_overlay.py verify        # fork 新增文件完整性
$PY tools/fork_overlay.py apply         # 重放补丁（幂等，可反复执行）
$PY tools/fork_sync.py --check          # 只读：上游版本情报 + 报告
$PY tools/fork_sync.py --sync           # fetch + rebase + 补丁重放 + 报告
$PY tools/fork_sync.py --status         # 打印同步状态
```

生成物在 `logs/fork/`（上游 `.gitignore` 已忽略）：`sync-state.json`、`last-report.md`、
`upstream-changelog.md`、`sync-history.jsonl`、`overlay-report.json`。

`fork_sync.py` 现在会把**补丁重放失败**判为同步失败，CI 不会推送缺少署名的源码。

## 出包与公开发布（在本机可运营的关键路径）

本机**没有 PowerShell 7**，上游 `tests/UpdateInstallerTests.ps1` 会失败，因此本机只能得到
「部分成功」的编译产物，**不能**从本机 `-Package` 出正式包。完整构建统一走 CI：

1. GitHub → Actions → **LeoZhang signed release** → Run workflow，`publish` 保持不勾选。
2. workflow 在 `windows-latest` 上依次执行：补丁自检 → `Build.ps1`（全量回归）→
   `Package.ps1` → `PackageSmoke.ps1` → 校验 `CREDITS.md` / `FORK-README.md` /
   `LICENSE` / `THIRD_PARTY_NOTICES.md` 确实在 ZIP 内 → 上传 artifact `leozhang-windows-x64`。
3. 下载 artifact 里的 `myfinder-device-battery-v<version>-windows-x64.zip`，解压后运行
   `一键安装自启.bat`，再用 `AtkBatteryProbe.exe --self-test` 与真机读数验证。
4. 验证通过后，在 Settings → Secrets and variables → Actions 添加 `RELEASE_SIGNING_KEY`，
   值为本机 `logs/fork/keys/private.xml` 全文：
   `gh secret set RELEASE_SIGNING_KEY < logs/fork/keys/private.xml`
   （私钥绝不入库、不进日志、不进 Release 附件；workflow 用完即删临时文件。）
5. 再次 Run workflow 并勾选 `publish`。workflow 会用该私钥签 `SHA256SUMS.txt`，创建
   `v<release.json version>` 标签，并附上四件东西：ZIP、`SHA256SUMS.txt`、
   `SHA256SUMS.txt.sig`、`source.zip`（`git archive HEAD`，满足 AGPL 对应源码要求）。
6. 一键更新要求这三件套**名称、数量、URL 完全匹配**，且 tag 必须等于 `v` + `release.json`
   的 version；workflow 已做强制校验。首个签名 Release 发布前，程序只会报告「未发现新版本」。

本机实测（补丁后的 C# 逻辑回归全绿）：51 项离线测试、106 项设备数据包发布检查、
283 项设备数据包检查、376 项更新器检查、463 项反馈检查、2027 项菜单检查、
85948 项配置契约检查等。唯一跑不完的是需要 `pwsh.exe` 的安装器跨版本回归。

## 已知决策项

| 项 | 现状 | 说明 |
| --- | --- | --- |
| 反馈中继 | 仍指向上游 Deno 服务，用户反馈会在**上游仓库**建 issue | 按「其他的就沿用现在的」保留。`overlay/patches/04`–`06` 已写好但默认关闭；启用前必须同步改写三个上游测试文件 |
| 型号数据包 | 仍从上游镜像/Release 拉取 | 上游公钥独立验签，建议保留 |
| 本机 PowerShell 7 | 缺失 | 不影响 CI 出包；如需本机完整回归，安装 PowerShell 7 后 `tools/fork_build.ps1` 即可跑完 |
| Actions 定时任务 | 已启用 | fork 仓库长期无活动时 GitHub 可能自动停用 schedule，偶尔检查 Actions 页 |

## 新增文件清单

| 路径 | 作用 |
| --- | --- |
| `fork-config.json` | 上游仓库、分支、同步策略、路径与 git 可执行文件位置 |
| `CREDITS.md` | 统一署名、许可、修改声明（随每个 ZIP 分发） |
| `tools/fork_sync.py` | 同步主控：情报、fetch、rebase、冲突回滚、补丁失败阻断、报告 |
| `tools/fork_overlay.py` | 声明式补丁重放与 fork 文件完整性校验 |
| `tools/fork_keys.ps1` | 生成 RSA 密钥对（公钥入库 / 私钥留本机） |
| `tools/fork_build.ps1` | 调用上游 `Build.ps1` / `Package.ps1` 的本机包装 |
| `overlay/` | 品牌元数据、公钥、14 个补丁描述符 |
| `docs/fork/` | 架构、合规清单、路线图 |
| `.github/workflows/fork-sync.yml` | 每小时自动同步 + 推送 + 上传报告 |
| `.github/workflows/fork-release.yml` | 构建、签名、对应源码与公开发布 |

## 本机环境适配（已固化进脚本）

| 问题 | 处理位置 |
| --- | --- |
| git 全局 `http.proxy` 指向离线代理 | `fork_sync.py` 对所有 git 调用强制清空代理 |
| PowerShell 的 `python` 解析到 Microsoft Store 存根 | `fork_build.ps1` 自动把真实 Python 目录前置到 PATH |
| 大小写重复的 `HTTP_PROXY` / `http_proxy` 触发 .NET 重复键异常 | `fork_build.ps1` 构建前清除所有代理变量 |
| PATH 里没有 git | `fork-config.json` 记录 PortableGit 绝对路径，脚本不依赖 PATH |

## 必须知道的三件事

1. **许可**：AGPL-3.0-only。再分发必须同许可开源、提供完整对应源码、保留全部原署名，不能闭源。
2. **私钥**：`logs/fork/keys/private.xml` 绝不入库；`overlay/keys/public.xml` 必须入库，否则 CI 无法重放验签补丁。换密钥会让所有已发布签名包失效。
3. **设备读数需真机验证**：上游兼容清单大量 C 级条目为「协议已接入、待实机验证」，同步只代表代码到位，不代表一定能读出正确电量。
