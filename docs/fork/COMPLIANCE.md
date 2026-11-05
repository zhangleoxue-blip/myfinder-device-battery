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
- **私钥入库**：`tools/fork_keys.ps1` 把私钥写到 `logs/fork/keys/private.xml`（上游 `.gitignore` 已忽略 `logs/`）。私钥不得进入仓库、CI、Release 附件或构建日志。

## 数据与隐私边界

上游说明：程序内「反馈问题」会把诊断公开成 GitHub issue，诊断**不含序列号和文件路径**，且不需要 GitHub 账号。若你对外分发 fork 构建，注意：

1. 反馈仍会提交到**上游仓库**的 issue 列表，你无法控制其内容与展示位置。
2. 一键更新仍从**上游 Release** 下载，供应链信任对象是上游维护者的私钥。若这不符合你的风险偏好，只能走「接管发布通道」路线（见 `ROADMAP.md` 阶段 5），代价是失去自动同步。
3. 上游兼容清单里 C 级条目为「协议已接入、待实机验证」，不要据此向用户作兼容性保证。

## 一句话结论

这个 fork 可以自由使用、修改和再分发，但必须**同样开源、同样 AGPL-3.0-only、保留全部声明与源码地址**。如果你的目标是闭源商业产品，正确做法是放弃 fork 路线，改为不复制上游代码的独立实现。
