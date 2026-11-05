# Fork 定制层（overlay）

这一层是 fork 相对上游**新增**的全部内容，不修改上游任何已有文件。目的是让 `git rebase upstream/main` 时冲突概率降到最低。

## 目录约定

| 路径 | 作用 |
| --- | --- |
| `branding.json` | 品牌与策略元数据。当前仅作记录，不注入上游源码。 |
| `patches/*.json` | 必须修改上游文件时的**声明式补丁**，由 `tools/fork_overlay.py` 在每次同步后自动重放。 |
| `defaults/` | 未来放本机默认配置模板（不进 Git 跟踪的上游运行状态文件目录）。 |

## 为什么坚持「只新增文件」

上游 `scripts/Package.ps1` 会把 `scripts/*.cs` 全部编入同一个程序集，并把每个源文件的 SHA256 写进 `build-info.json`；打包时逐一复验。因此：

1. **新增非 `.cs` 文件**（`.py` / `.json` / `.md` / `.yml`）不参与编译、不进发行包，完全安全。
2. **新增 `.cs` 文件会被自动编入主程序**（`Build.ps1` 用 `Get-ChildItem scripts -Filter *.cs`），这是未来做功能扩展的正规入口，但必须与上游命名空间 `AtkBattery` 的类名错开。
3. **修改任何上游 `.cs` 文件**都必须重新完整构建，且每次 rebase 有冲突风险。这类改动一律走 `patches/`，不要直接改。

## 补丁重放机制

`fork_overlay.py apply` 读取 `patches/*.json`：

- `enabled: false` → 跳过（默认）。
- `enabled: true` → 按 `pattern` 正则定位目标文件，用 `template` 替换，替换前先在临时副本上校验命中次数恰好为 1，避免误伤。
- 每轮同步结束后自动重放一次，因此即使上游改动了被补丁的文件，只要锚点仍在，补丁就能重新贴上。锚点消失时脚本报错并写入报告，不静默跳过。

当前唯一补丁 `trust-key.json` 默认关闭。原因见该文件 `risk` 字段：**上游把更新源和验签公钥都硬编码为上游自己的 Releases**，保持原样才是让 fork 版程序自动跟随上游发版的最省事做法。
