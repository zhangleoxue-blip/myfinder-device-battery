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

**注意**：不要用自有私钥给这个包签名。签名权属于上游，改用自有密钥会同时让程序内置的一键更新失效。

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

## 阶段 5 — 接管发布通道（默认不做）

仅当你需要发行与上游不同的功能版本时才考虑：

- 用 `tools/fork_keys.ps1` 生成 RSA 密钥对。
- 启用 `overlay/patches/trust-key.json` 替换 `PublicKeyXml`。
- 同时替换 `UpdateTrust.ApiUrl`、`Repository`、必要时 `ZipName`（需要新增补丁描述符）。
- 自建 Release 服务与签名流程，保证每次同步后补丁能重新贴上。

**代价**：程序不再接受上游签名包，二进制层的自动同步消失；上游每次改动 `UpdateValidation.cs` 都可能让补丁锚点失效；你需要独立承担全部发布与安全责任。除非有明确商业理由，建议保持现状。

## 当前不建议做的事

- 不要把 C 级设备适配直接写进对外宣传。
- 不要在未跑通阶段 2 之前分发 ZIP。
- 不要为了「改个名字」去动 `AppId` 或 `ZipName`——那会直接破坏上游一键更新的文件名匹配。
