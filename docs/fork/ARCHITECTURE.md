# 架构与同步机制

## 1. 为什么选「只新增文件」的 fork 结构

上游不是一个带插件接口的应用，而是**单体编译**：`scripts/Build.ps1` 第 32 行用

```powershell
Get-ChildItem $PSScriptRoot -Filter '*.cs' -File | Where-Object {$_.Name -notin @('Probe.cs','Tests.cs','AssemblyInfo.cs')}
```

把 `scripts/` 下几乎所有 `.cs` 一起交给系统自带的 .NET Framework 编译器，编成 `AtkMouseBattery.exe`。同时 `scripts/Package.ps1` 第 22–25 行会用 `build-info.json` 里记录的所有源文件 SHA256 逐个复验，源码在验证后被改动就拒绝打包。

由此得到三条工程约束：

| 动作 | 后果 | 结论 |
| --- | --- | --- |
| 新增 `.py` / `.json` / `.md` / `.yml` | 不参与编译、不进发行包 | 安全，作为 fork 主体 |
| 新增 `.cs` 到 `scripts/` | 会被自动编进主程序，也会进哈希清单 | 未来做功能扩展的正规入口，类名需避开 `AtkBattery` 现有类型 |
| 直接修改上游 `.cs` / `.ps1` | 必须重编译，且每次 rebase 有冲突风险 | 一律改为 `overlay/patches/*.json` 声明式补丁 |

因此本 fork 的所有内容都是新增文件，`fork/main` 上的定制提交可以稳定地 rebase 到任意新版本的上游基线。

## 2. 代码层同步：rebase 流程

`tools/fork_sync.py --sync` 的执行顺序：

1. `ensure_upstream_remote()`：确保 `upstream` remote 指向上游仓库（CI 环境尤为重要）。
2. 前置检查：当前分支必须是 `fork/main`，`git status --porcelain` 必须干净；脏工作区直接拒绝，避免 rebase 中途失败。
3. `git fetch upstream`：所有 git 调用都带 `-c http.proxy= -c https.proxy=`，因为本机全局 `http.proxy` 指向离线的 `127.0.0.1:7890`，而直连 GitHub 可用。这一步是本机能跑通的关键。
4. 比较 `git merge-base HEAD upstream/main` 与 `upstream/main`：相同则无需 rebase，不同则执行 `git rebase upstream/main`。
5. 冲突处理：rebase 失败时收集 `git diff --name-only --diff-filter=U`，立即 `git rebase --abort` 回滚，把冲突文件写进报告并置状态为 `conflict`。**不会留下半完成的 rebase 状态**。
6. `fork_overlay.py apply`：重放声明式补丁。
7. 可选 `--build`：调用 `tools/fork_build.ps1`。
8. 写出 state / report / changelog / history。

## 3. 二进制层同步：上游自带的更新通道

这是最容易被忽略、但对本需求最有价值的一点。`scripts/UpdateValidation.cs` 第 17–25 行定义了：

| 常量 | 值 | 影响 |
| --- | --- | --- |
| `PublicKeyXml` | 上游 RSA 公钥 | 只接受上游私钥签名的 `SHA256SUMS.txt.sig` |
| `ApiUrl` | `api.github.com/repos/wushuai0802/myfinder-device-battery/releases` | 程序内一键更新直接查上游 Release |
| `AppId` / `ZipName` | `myfinder-device-battery` / 固定命名规则 | 决定下载哪个 ZIP |

也就是说，**fork 出来的程序，天然会继续跟随上游官方发版**。两份公钥与地址都保持不变时，用户装的是你的构建，但升级用的是上游的签名发行包——这是"他更新、你的软件也同步更新"的最短路径。

代价是：你不能用自有私钥签名自己的发行包。`Sign-Release.ps1` 第 7–20 行会从 `UpdateValidation.cs` 正则提取内置公钥，并验证私钥与之匹配，不匹配直接拒绝写签名。要接管发布通道，必须同时替换公钥、`ApiUrl`、`ZipName` 并维护自己的 Release 服务——这正是 `overlay/patches/trust-key.json` 默认 `enabled: false` 的原因。

## 4. 声明式补丁机制

`tools/fork_overlay.py` 不存 diff，而存**锚点**：

- `pattern`：定位目标文件中唯一的一处文本。
- `template`：替换模板，占位符由外部文件填充（如 `{PUBLIC_KEY_XML}`）。
- 应用前先在内存里校验正则命中次数**恰好为 1**；锚点消失时报错并写入报告，绝不静默跳过。
- 保留原文件的 UTF-8 BOM 状态，避免破坏编译。
- 每次同步后自动重放，因此上游改动被补丁的文件，只要锚点仍在就不会丢失定制。

当前唯一补丁指向 `scripts/UpdateValidation.cs` 的公钥常量，默认关闭。

## 5. 构建与打包链

```
tools/fork_build.ps1
  └─ scripts/Build.ps1            # csc 编译 + --self-test + --preview + tests/Run.ps1
       └─ outputs/fork-build/build-info.json   # 版本 + 所有源文件 SHA256
  └─（可选 -Package）scripts/Package.ps1
       ├─ 复验 build-info.json 里每个源文件哈希
       ├─ scripts/Build-Backend.ps1            # 准备便携 Python 读取引擎（需联网下载）
       └─ ZIP + SHA256SUMS.txt
```

`Sign-Release.ps1` 是发布时在本机用私钥签名校验和文件的最后一步，私钥不得进仓库。本 fork 默认不签名自己的包，签名权仍在上游。

## 6. 失败模式与边界

| 场景 | 行为 |
| --- | --- |
| GitHub API 限流 / 断网 | 版本情报标为不可用，本地 git 信息仍有效，同步照常进行 |
| 工作区有未提交改动 | 拒绝 sync，不破坏现场 |
| rebase 冲突 | 自动 abort，报告列出冲突文件，状态置 `conflict` |
| 补丁锚点消失 | 报告标 `failed`，退出码非 0，需人工复核 |
| 上游改了 `Package.ps1` 的哈希清单规则 | 新增的非 `.cs` 文件不受影响；新增 `.cs` 会进清单，属预期行为 |
| 上游把 `ApiUrl` 改成自己的新地址 | 二进制层同步自动跟随，无需 fork 侧改动 |

## 7. 尚未覆盖的部分

- 本轮未实现独立的设备协议读取器。所有设备支持仍来自上游代码，这是 fork 方案的预期结果。
- 未接管签名与发布通道（按设计刻意不做）。
- 未做真机硬件验证。上游兼容清单里大量型号为 C 级（协议已接入、待实机验证），同步后必须自行核验。
