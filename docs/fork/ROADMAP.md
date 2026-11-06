# 实施路线图

## 阶段 0 — 同步骨架（本轮已交付）

- [x] 克隆上游，建立 `upstream` remote 与 `fork/main` 分支
- [x] `fork-config.json`、`tools/fork_sync.py`、`tools/fork_overlay.py`
- [x] 冲突自动回滚、补丁重放、版本情报与中文报告
- [x] 构建包装、密钥工具、定时同步 workflow
- [x] 架构、合规、本文档

**验收标准**：`--check` 能读到上游 `release.json` 与最新 Release；`--sync` 能完成 fetch/rebase 判定并生成报告；工作区在冲突时自动恢复。

## 阶段 1 — 让同步真正无人值守

1. 在 GitHub 上 fork 上游仓库到你自己的账号（浏览器操作，需要你的账号）。
2. 运行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\fork_bootstrap.ps1 -OriginUrl "<你的仓库地址>"`：自动更新 `fork-config.json` 的 `fork.origin`、添加 `origin` remote、推送 `fork/main`。无凭据时加 `-SkipPush` 只做本地配置。
3. 在仓库 Settings → Actions → General 把 Workflow permissions 设为 **Read and write**（对应 workflow 的 `contents: write`）。
4. 在 Actions 页启用 `.github/workflows/fork-sync.yml`（默认每小时第 17 分钟运行）。注意 fork 仓库的 scheduled workflow 默认是关闭的，必须手动启用。
5. 等下一次上游提交，验证一次真实 rebase：检查 `logs/fork/sync-history.jsonl` 是否出现 `action=rebased`，以及 `fork/main` 是否包含上游新提交。

**风险**：Actions 的定时调度在 fork 仓库默认可能是禁用状态，需手动启用；且 GitHub 对长时间无活动的仓库会暂停 schedule。

## 阶段 2 — 跑通本地构建与发行包

1. 执行 `tools/fork_build.ps1`（要求 Windows 10/11 x64 + 系统自带 .NET Framework 编译器）。
2. 确认 `outputs/fork-build/build-info.json` 里所有源文件哈希齐全。
3. 需要完整 ZIP 时执行 `-Package`：会调用 `Build-Backend.ps1`，需联网下载官方便携 Python 与 hidapi 并校验签名，是这阶段最容易因网络失败的一步。
4. 对照 `docs/fork/ARCHITECTURE.md` 第 5 节理解打包链，不要手工改 `build-info.json`。

**注意（2026-11-06 更新）**：本机因缺少 PowerShell 7，`tests/UpdateInstallerTests.ps1` 必然失败，所以 `tools/fork_build.ps1` 只能给出「部分成功」，**不能**用它产出的目录 `-Package`。完整构建与打包统一交给 `.github/workflows/fork-release.yml` 的 `windows-latest` runner（自带 pwsh）。本机已验证补丁后的全部 C# 逻辑回归通过（含 376 项更新器检查、463 项反馈检查、2027 项菜单检查）。

## 阶段 3 — 定制层（可选）

按冲突风险从低到高：

| 优先级 | 做法 | 冲突风险 |
| --- | --- | --- |
| 1 | 修改 `overlay/branding.json`，新增配置模板、文档、工具 | 无 |
| 2 | 新增 `.github/workflows/*.yml`、CI 脚本 | 无 |
| 3 | 在 `scripts/` 新增 `.cs`，实现独立类（命名空间避开 `AtkBattery` 现有类型名） | 低，会自动编入主程序 |
| 4 | 用 `overlay/patches/` 声明式补丁改上游文件 | 中，锚点变化时需人工复核 |
| 5 | 直接修改上游 `.cs` | 高，不推荐 |

第 3 项要注意：`Build.ps1` 会把所有 `scripts/*.cs` 编进同一程序集，`Package.ps1` 会把它们全部写进哈希清单，所以新增源码后必须重新完整构建，不能只复制 exe。

## 阶段 4 — 真机验证

上游兼容清单分 A / C / D 级证据，多数新适配是 C 级（协议已接入、待实机验证）。建议：

1. 以 `docs/compatibility.md` 与 `engine/compatibility.json` 为基准，列出你手上的设备。
2. 每台记录：VID/PID、连接方式（接收器 / 蓝牙 / 有线）、官方软件读数、fork 构建读数、偏差、充电与休眠表现。
3. 把你验证过的型号单独建一张证据表，只对你实测过的组合作兼容承诺。
4. 读数异常时用程序内「反馈问题」提交（注意会公开到上游 issue，见 `COMPLIANCE.md`）。

## 阶段 5 — 接管发布通道（2026-11-06 已启用）

用户确认目标是「基于开源内容做自己的软件、换上 LeoZhang 署名、未来发布给大众」，因此本阶段由「默认不做」改为**已实施**：

- [x] `tools/fork_keys.ps1` 生成 RSA 密钥对：公钥 `overlay/keys/public.xml` **入库**（CI 重放需要），私钥 `logs/fork/keys/private.xml` 被忽略。
- [x] 启用 `overlay/patches/trust-key.json` 替换 `PublicKeyXml`；`03-release-channel.json` 替换 `Repository` / `ApiUrl`。
- [x] `AppId` / `ZipName` 保持不变（不需要新补丁，也避免破坏更新文件名匹配）。
- [x] `CREDITS.md`、`FORK-README.md` 打进发行 ZIP；程序内源码/文档链接指向本仓库。
- [x] 修正三个硬编码上游 URL 的回归测试，保证 CI 全绿。
- [x] 见阶段 6：导入签名 Secret 并发布首个自有签名 Release（2026-11-06 已完成）。

**代价**：程序不再接受上游签名包，二进制层的自动同步消失；上游每次改动 `UpdateValidation.cs` 都可能让补丁锚点失效；你需要独立承担全部发布与安全责任。这是用户明确选择「自己开发一款、换署名、公开发布」后的必然后果。

## 阶段 6 — 签名出包并公开发布（2026-11-06 已完成）

- [x] `.github/workflows/fork-release.yml`：`workflow_dispatch`，全量回归 → `Package.ps1` → `PackageSmoke.ps1` → 校验 AGPL 声明入包 → `Sign-Release.ps1` → 可选发布 Release + `source.zip`。
- [x] `fork_sync.py` 现在把补丁重放失败判为同步失败，阻止 CI 推送未打补丁的源码。
- [x] 首次运行 `publish=false`（run `42184736960`），下载 artifact 在本机安装验证。
- [x] 通过 GitHub Secrets API 用 libsodium sealed box 注入 `RELEASE_SIGNING_KEY`；私钥只在本机内存，未进仓库 / CI 日志 / Release。
- [x] run `42189790580` 勾 `publish=true` → success，发布
  [`v1.3.9-beta.7`](https://github.com/zhangleoxue-blip/myfinder-device-battery/releases/tag/v1.3.9-beta.7)
  （prerelease，tag 指向 `69692c1`），4 个附件：ZIP / `SHA256SUMS.txt` / `SHA256SUMS.txt.sig` / `source.zip`。
- [x] 端到端验签：公钥验证 `.sig` 通过、自有私钥重签结果一致；16 并发下载 Release ZIP，
  SHA256 `093a87b3…` 与 `SHA256SUMS.txt` 完全一致；解包 148 文件、AGPL 声明齐全、
  程序署名 `LeoZhang`、`--self-test` PASS 51。
- [ ] 决定是否接管阶段 5 之外仍指向上游的「反馈中继」端点（见 `COMPLIANCE.md`）。

**以后每次发新版**：等 `Fork upstream sync` 带入新版本 → 确认补丁重放成功 →
Actions → `LeoZhang signed release` → 勾 `publish=true`。tag 必须等于 `v` + `release.json`
的 version；用同一版本号重发不会让用户端提示升级。

## 当前不建议做的事

- 不要把 C 级设备适配直接写进对外宣传。
- 不要在未跑通阶段 2 之前分发 ZIP。
- 不要为了「改个名字」去动 `AppId` 或 `ZipName`——那会直接破坏上游一键更新的文件名匹配。
