# AGPL-3.0-only 合规清单

本仓库派生自 `wushuai0802/myfinder-device-battery`。上游 `LICENSE` 为 **GNU Affero General Public License v3.0（AGPL-3.0-only）**，README 明确「自有代码采用 AGPL-3.0-only，按现状提供，不提供任何担保」；1.3.4 及更早版本按 MIT 发布，改编自 HaloBattery 的部分保留其 MIT 声明，第三方组件见 `THIRD_PARTY_NOTICES.md`。

选择 fork 方案，等于同意以下义务。这不是建议，是许可条件。

## 再分发前必须做到

| # | 义务 | 本仓库对应做法 |
| --- | --- | --- |
| 1 | 保留完整许可证文本 | 不修改、不删除根目录 `LICENSE`；`docs/fork/` 与 `FORK-README.md` 均为新增文件 |
| 2 | 保留第三方声明 | 不修改 `THIRD_PARTY_NOTICES.md`，其中包含 HaloBattery 的 MIT 声明 |
| 3 | 保留源码中的许可与源码地址声明 | `UpdateValidation.cs` 的 `Repository` 常量、程序「状态与诊断」页里的许可证与源码地址，都不得移除 |
| 4 | 以同一许可提供完整对应源码 | 公开发布 fork 仓库，包含全部 `.cs`、`.ps1`、`engine/`、`tests/`、构建与打包脚本；只给二进制 ZIP 不合规 |
| 5 | 标注修改 | `fork/main` 的提交历史、`FORK-README.md` 的新增文件清单、`overlay/branding.json` 都明确标识了派生关系与改动范围 |
| 6 | 不得附加额外限制 | 不得对下游接收者增加 EULA、禁用反编译、禁止再分发等条款 |
| 7 | 网络交互条款（AGPL §13） | 主程序是本地托盘应用，但内置「反馈问题」与「一键更新」会联网。保守做法：公开可访问的 fork 仓库地址随发行包提供，确保交互用户能取得对应源码 |
| 8 | 无担保声明 | 保留上游「按现状提供、不提供担保」声明；不要把上游未实机验证的设备包装成确定承诺 |

## 本 fork 新增文件的许可处理

`tools/`、`overlay/`、`docs/fork/`、`FORK-README.md`、`fork-config.json`、`.github/workflows/fork-sync.yml` 属于派生作品的组成部分，**同样按 AGPL-3.0-only 提供**。不要单独给工具脚本挑一个宽松许可再混合分发，那会造成许可边界不清。

## 明确不能做的事

- **闭源**：不能以「二次开发」名义只发布可执行文件。
- **移除署名**：不能删掉源码地址、许可证页、上游作者信息。
- **接管签名后仍声称是官方构建**：替换 `PublicKeyXml` / `ApiUrl` 后，程序不再是上游签名信任链的一部分，必须向用户清晰说明发布主体已变更。
- **私钥入库**：`tools/fork_keys.ps1` 把私钥写到 `logs/fork/keys/private.xml`（上游 `.gitignore` 已忽略 `logs/`），公钥写到**纳入版本控制**的 `overlay/keys/public.xml`（公钥不是秘密，CI 重放补丁必须能读到）。私钥不得进入仓库、CI 日志或 Release 附件，只能通过 `RELEASE_SIGNING_KEY` Secret 注入。
- **只发二进制不附源码**：`fork-release.yml` 会把 `git archive HEAD` 的 `source.zip` 一起挂到 Release，并在 ZIP 内附 `CREDITS.md` / `FORK-README.md` / `LICENSE` / `THIRD_PARTY_NOTICES.md`；发布前由 workflow 强制校验这四个文件确实在包里。

## 数据与隐私边界

上游说明：程序内「反馈问题」会把诊断公开成 GitHub issue，诊断**不含序列号和文件路径**，且不需要 GitHub 账号。若你对外分发 fork 构建，注意：

1. 反馈仍会提交到**上游仓库**的 issue 列表，你无法控制其内容与展示位置。见下方「尚未接管的两个上游网络端点」。
2. 一键更新已经指向**本仓库 Release** 并用 LeoZhang 的公钥验签，供应链信任对象是你的私钥；上游签名包不再被接受。
3. 上游兼容清单里 C 级条目为「协议已接入、待实机验证」，不要据此向用户作兼容性保证。

## 一句话结论

这个 fork 可以自由使用、修改和再分发，但必须**同样开源、同样 AGPL-3.0-only、保留全部声明与源码地址**。如果你的目标是闭源商业产品，正确做法是放弃 fork 路线，改为不复制上游代码的独立实现。

## 独立发布版补充（LeoZhang，2026-11-06）

本仓库现在的定位是**对外发布的修改派生版**，署名 `LeoZhang`。新增 [`CREDITS.md`](../../CREDITS.md)
作为统一署名与修改声明，满足 AGPL §5(a) 的显著标注要求。

| 变动 | 合规判断 |
| --- | --- |
| 新增 `Copyright (C) 2026 LeoZhang` | 允许；属于添加署名 |
| 保留 `LICENSE`、`THIRD_PARTY_NOTICES.md`、上游源码地址（在 CREDITS 与程序内诊断页） | 必须，已做到 |
| 改 `AssemblyCompany` / `AssemblyCopyright` / 诊断页文字 | 允许；改动文件带修改声明与日期 |
| 把 `Repository` / `ApiUrl` 指向本仓库 | 允许；CREDITS 仍列出上游地址 |
| 替换 `PublicKeyXml` 为自有公钥 | 允许；但必须向用户说明**发布主体已变更**，不得自称官方构建 |
| 把程序内源码/文档/下载链接指向本仓库 | 允许；上游地址仍在 CREDITS、LICENSE、THIRD_PARTY_NOTICES 中保留 |
| `Package.ps1` 把 CREDITS / FORK-README 打进 ZIP | 满足 §5(a) 显著修改声明与 §6 随附许可声明 |
| Release 附 `source.zip`（`git archive HEAD`） | 满足 §6 完整对应源码与 §13 网络交互用户取源码 |
| `AppId` / `ZipName` 保持不变 | 减少冲突面，非许可要求 |

### 尚未接管的两个上游网络端点（发布前的已知决策项）

按用户「署名 LeoZhang，其他的就沿用现在的」的要求，以下两项**保持上游原样**，请在面向大众正式推广前决定是否处理：

| 端点 | 代码位置 | 影响 | 若决定接管 |
| --- | --- | --- | --- |
| 反馈中继 `myfinder-feedback-relay.wushuai0802.deno.net` | `scripts/FeedbackForm.cs` 的 `FeedbackRelay.Url`、`FeedbackClient.IssueUrl`；`scripts/GenericBattery.cs` 的 `IssueBase` | 用户点「反馈问题」会在**上游仓库**创建公开 issue；可能给上游维护者造成噪音 | `overlay/patches/04` / `05` / `06` 已写好但默认 `enabled: false`。启用前必须同步改写 `tests/FeedbackFormTests.cs` 的 `RelayConfiguration`、`tests/FeedbackRepliesTests.cs` 和 `tests/CardsFeedbackTests.cs`，否则 CI 回归会失败 |
| 型号数据包 `DevicePackTrust.Mirror` / `GitHub` | `scripts/DevicePackTrust.cs` | 应用仍从上游镜像/Release 拉取**由上游公钥验证**的设备兼容数据包 | 建议保持：这是用户最初要的「数据层同步」，且签名验证独立于应用更新信任链，不产生供应链风险 |

这是产品决策，不是 AGPL 合规缺陷：许可、署名、源码地址、对应源码均已齐备。

### 发布状态检查表

1. `.github/workflows/fork-release.yml` 已建立：`workflow_dispatch` 构建 → 全量回归 → 打包 → `PackageSmoke` → 校验 AGPL 声明入包 → 签名 → 可选发布。
2. 首次运行 `publish=false`（run `42184736960`）已下载 artifact 在本机验证；该产物未签名。
3. `RELEASE_SIGNING_KEY` 已通过 GitHub Secrets API + libsodium sealed box 写入仓库 Secret；
   值来自 `logs/fork/keys/private.xml`，全程不打印、不进入仓库、CI 日志或 Release 附件。
   （本机无 `gh` CLI；也可用网页 Settings → Secrets and variables → Actions 添加。）
4. 发布时 workflow 会强制要求 tag 等于 `v` + `release.json` 的 version，否则一键更新会拒绝该 Release。
5. Release 必须同时含 `myfinder-device-battery-v<version>-windows-x64.zip`、`SHA256SUMS.txt`、`SHA256SUMS.txt.sig` 三个附件；`UpdateCatalog.ValidateAssets` 会逐个校验名称与 URL。
6. 私钥绝不进入仓库、CI 日志、artifact 或 Release；workflow 用完后立即删除临时私钥文件。
7. 每次上游改动被补丁命中的文件，rebase 会失败并自动 abort；`fork_overlay.py` 锚点消失会报错，且 `fork_sync.py` 现在会把补丁失败判为同步失败、阻止 CI 推送。

**首个签名 Release 实际核验（2026-11-06，全部通过）**

- [`v1.3.9-beta.7`](https://github.com/zhangleoxue-blip/myfinder-device-battery/releases/tag/v1.3.9-beta.7)
  为 prerelease，tag 指向 `69692c1`；附件为 ZIP 13,555,925 B、`SHA256SUMS.txt` 121 B、
  `SHA256SUMS.txt.sig` 256 B、`source.zip` 1,873,178 B —— 三件套 + 对应源码齐备。
- 用 `overlay/keys/public.xml` 验证 `SHA256SUMS.txt.sig` 通过；用自有私钥重签得到完全一致的签名，
  确认签名确属本仓库而非上游密钥。
- Release ZIP 的 SHA256 `093a87b3…` 与 `SHA256SUMS.txt` 一致；解包 148 文件含全部 4 个
  AGPL 声明文件；程序集署名 `LeoZhang`；`--self-test` PASS 51。
- Release notes 明确标注「unofficial modified build published by LeoZhang」、AGPL-3.0-only、
  非官方构建、非上游密钥签名，并指向 `source.zip` 与发布 tag 的源码。

**一句话**：可以以 AGPL-3.0-only 对外发布，但必须继续开源、公开完整对应源码、保留全部原署名，并明确标注「非官方构建，由 LeoZhang 发布」。
