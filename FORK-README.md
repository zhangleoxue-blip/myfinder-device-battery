# MyFinder Device Battery — 同步型 Fork

这是 `wushuai0802/myfinder-device-battery` 的一个**自动同步 fork**。目标不是重写一款软件，而是：上游每发布一次功能或设备适配，这份代码自动 rebase 到最新基线；已经安装在电脑上的 fork 构建，也继续通过上游自带的一键更新通道升级。

## 当前状态（2026-11-05）

| 项 | 值 |
| --- | --- |
| 上游基线提交 | `d7bd6641dbe0618fab05b31aaadfdb9b66451f83` |
| 基线提交时间 | 2026-11-05 16:04（北京时间） |
| 上游 `release.json` 版本 | `1.3.8-beta.5` |
| 本地分支 | `fork/main` |
| 上游 remote | `upstream` |
| 定制策略 | **只新增文件**，不改动上游任何已有源码 |

上游迭代很快：11 月 4 日到 5 日一天内发了 `v1.3.6-beta.1` 至 `v1.3.8-beta.4` 多个版本，源码版本已到 `1.3.8-beta.5`。这也是同步链路必须先做的原因。

## 快速开始

所有命令在仓库根目录执行。Python 用本机 venv（标准库即可，无第三方依赖）：

```bash
PY="C:/Users/admin/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

$PY tools/fork_sync.py --check     # 只读：查上游版本、比对 SHA、生成报告
$PY tools/fork_sync.py --sync      # fetch + rebase + 重放补丁 + 生成报告
$PY tools/fork_sync.py --sync --build   # 同步后调用上游 Build.ps1
$PY tools/fork_sync.py --status    # 打印同步状态 JSON
$PY tools/fork_overlay.py verify  # 检查 fork 新增文件是否齐全
```

生成物（已被上游 `.gitignore` 忽略，不会污染工作区）：

| 文件 | 内容 |
| --- | --- |
| `logs/fork/sync-state.json` | 最近检查/同步时间、基线 SHA、状态 |
| `logs/fork/last-report.md` | 每次同步的中文报告（版本情报、最近提交、补丁结果、合规提示） |
| `logs/fork/upstream-changelog.md` | 上游近期提交与 Release 列表 |
| `logs/fork/sync-history.jsonl` | 每次同步一行，便于做趋势与告警 |
| `logs/fork/overlay-report.json` | 补丁重放明细 |

## 两条同步链路

```
代码层：GitHub upstream/main ──fetch──> git rebase ──> fork/main ──> 你的构建/发行
                                            │
                                            └─> fork_overlay.py 重放声明式补丁

二进制层：已安装的 fork 程序 ──UpdateTrust.ApiUrl──> 上游 Releases API
                              ──> 校验 SHA256SUMS.txt.sig（上游公钥）
                              ──> 一键更新到上游官方发行包
```

第二条是上游自带的，不是我们写的：`scripts/UpdateValidation.cs` 把更新地址与验签公钥都硬编码为上游仓库。**保持 `AppId`、`ZipName`、`ApiUrl`、验签公钥不变**，fork 构建就能持续跟随上游发版。反过来，替换公钥就会同时切断这条链路。详见 `docs/fork/ARCHITECTURE.md`。

## 新增文件清单

| 路径 | 作用 |
| --- | --- |
| `fork-config.json` | 上游仓库、分支、同步策略、路径与 git 可执行文件位置 |
| `tools/fork_sync.py` | 同步主控：版本情报、fetch、rebase、冲突回滚、报告 |
| `tools/fork_overlay.py` | 声明式补丁重放与 fork 文件完整性校验 |
| `tools/fork_build.ps1` | 调用上游 `Build.ps1` / `Package.ps1` 的薄包装 |
| `tools/fork_keys.ps1` | 生成自有 RSA 签名密钥（默认不需要） |
| `overlay/` | 品牌元数据与补丁描述符 |
| `docs/fork/` | 架构、合规、路线图 |
| `.github/workflows/fork-sync.yml` | 每小时自动同步 + 推送 + 上传报告 |

## 必须知道的三件事

1. **许可**：AGPL-3.0-only。再分发必须同许可开源并提供完整源码地址，不能闭源。清单见 `docs/fork/COMPLIANCE.md`。
2. **不要改公钥**：`overlay/patches/trust-key.json` 默认关闭，启用它会破坏与上游签名发行包的兼容性，并制造持续的 rebase 冲突。
3. **设备读数需真机验证**：上游大量新增型号标注「尚未实机验证」。同步只代表代码到位，不代表你的鼠标/耳机一定能读出正确电量。

## 后续

`fork-config.json` 的 `fork.origin` 填上你自己的 GitHub 仓库地址后，把 `fork/main` 推上去并启用 `fork-sync.yml`，即可实现无人值守同步。分阶段计划见 `docs/fork/ROADMAP.md`。
