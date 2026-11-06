# Fork 定制层（overlay）

这一层是 fork 相对上游**新增**的全部内容，不修改上游任何已有文件。目的是让 `git rebase upstream/main` 时冲突概率降到最低。

## 目录约定

| 路径 | 作用 |
| --- | --- |
| `branding.json` | 品牌与策略元数据。当前仅作记录，不注入上游源码。 |
| `patches/*.json` | 必须修改上游文件时的**声明式补丁**，由 `tools/fork_overlay.py` 在每次同步后自动重放。 |
| `keys/public.xml` | LeoZhang 的 RSA **公钥**，纳入版本控制。CI 与本机都靠它重放 `trust-key.json`；公钥不是秘密。 |
| `defaults/` | 未来放本机默认配置模板（不进 Git 跟踪的上游运行状态文件目录）。 |

## 为什么坚持「只新增文件」

上游 `scripts/Package.ps1` 会把 `scripts/*.cs` 全部编入同一个程序集，并把每个源文件的 SHA256 写进 `build-info.json`；打包时逐一复验。因此：

1. **新增非 `.cs` 文件**（`.py` / `.json` / `.md` / `.yml`）不参与编译、不进发行包，完全安全。
2. **新增 `.cs` 文件会被自动编入主程序**（`Build.ps1` 用 `Get-ChildItem scripts -Filter *.cs`），这是未来做功能扩展的正规入口，但必须与上游命名空间 `AtkBattery` 的类名错开。
3. **修改任何上游 `.cs` 文件**都必须重新完整构建，且每次 rebase 有冲突风险。这类改动一律走 `patches/`，不要直接改。

## 补丁重放机制

`fork_overlay.py apply` 读取 `patches/*.json`：

- `enabled: false` → 跳过。当前有 3 个「反馈中继接管」补丁默认关闭，见下文。
- `enabled: true` → 按 `pattern` 正则定位目标文件，用 `template` 替换，替换前校验命中次数恰好为 1，避免误伤。
- `template` 支持 `{MATCH}`（原锚点文本）、`values` 字典里的任意占位符，以及带 `keyFile` 时的 `{PUBLIC_KEY_XML}`。无 `keyFile` 的纯文本补丁同样受支持。
- **幂等性**：追加型补丁（`{MATCH}` + 新增行）会检测新增文本是否已存在；替换型补丁的 `pattern` 同时兼容「改前」与「改后」文本，使 `updated == text` 时直接返回 `already-applied`。报告里 `unchanged` 即这类幂等命中。
- 每轮同步结束后自动重放一次；锚点消失时脚本报错，**`fork_sync.py` 会把补丁失败判为同步失败并阻止 CI 推送**。

## 当前已启用的补丁（2026-11-06，共 11 个）

| 描述符 | 目标 | 作用 |
| --- | --- | --- |
| `01-signature-assembly.json` | `scripts/Build.ps1` | 程序集元数据加入 `LeoZhang` 公司名与版权声明 |
| `02-signature-diagnostics.json` | `scripts/TrayApp.cs` | 程序内诊断/关于文本加入修改者与上游地址 |
| `03-release-channel.json` | `scripts/UpdateValidation.cs` | 源码地址与更新 API 指向本仓库 |
| `07-app-source-link.json` | `scripts/PopupPages.cs` | 「状态与诊断」页源码地址指向本仓库 |
| `08-start-download-link.json` | `scripts/Start.ps1` | 源码仓库缺 exe 时的下载提示指向本仓库 Releases |
| `09-compatibility-link.json` | `scripts/TrayApp.cs` | 兼容清单链接指向本仓库 `fork/main` |
| `10-package-credits.json` | `scripts/Package.ps1` | 把 `CREDITS.md` / `FORK-README.md` 打进发行 ZIP |
| `11-tests-update-repository.json` | `tests/UpdateTests.cs` | 测试夹具改用 `UpdateTrust.Repository`，否则更新器回归崩溃 |
| `12-tests-diagnostics-source-link.json` | `tests/UnadaptedDiagnosticTests.cs` | 同步源码地址断言 |
| `13-tests-support-url.json` | `tests/UiMenusTests.cs` | 同步兼容清单链接断言 |
| `trust-key.json` | `scripts/UpdateValidation.cs` | 验签公钥换成 LeoZhang 自有公钥 |

`03` 与 `trust-key` 共同完成「功能保留、发布主体换成 LeoZhang」：一键更新仍可用，但只接受本仓库签名包。副作用是**不再接受上游签名包**，这是独立发布的必要代价。完整署名与许可见根目录 `CREDITS.md`。

## 默认关闭的补丁（反馈中继接管）

`04-feedback-relay.json` / `05-feedback-issue-url.json` / `06-feedback-issue-base.json` 会把程序内「反馈问题」从上游 Deno 中继与上游 issue 列表切走。按用户「其他的就沿用现在的」决定暂时**保持上游原样**。它们带有 `blockedBy` 说明：启用前必须同步改写 `tests/FeedbackFormTests.cs`、`tests/FeedbackRepliesTests.cs`、`tests/CardsFeedbackTests.cs`，否则 CI 回归失败。

## 密钥

- 公钥 `overlay/keys/public.xml`：**必须提交**，CI checkout 后靠它重放 `trust-key.json`。
- 私钥 `logs/fork/keys/private.xml`：**绝不提交**（`logs/` 被上游 `.gitignore` 忽略），只能通过 `RELEASE_SIGNING_KEY` Secret 注入 `.github/workflows/fork-release.yml`。
- 重新生成密钥会使所有已发布签名包失效，仅应在私钥泄露时执行。
