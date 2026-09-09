# 过程文件归属 Rule

> DSH 主 agent 在执行任何"会产出过程文件/中间产物"的任务时，必须遵守本规则。
> 这是踩坑教训的固化：见 2026-09-09 事件（npp 仓库被写入 `runtime/branch-check/`）。

## 核心规则（一句话）

**过程文件 / 中间产物 / scratch / 缓存 / 临时表格 / 调试 patch，只能写到 *当前会话所在的工作仓库* 的 `runtime/` 子目录下，不得写入任何其他项目的源码树。**

## "当前仓库"的定义

- 本会话开始时由用户通过 `workdir` 显式指定，或由引导路径默认决定的工作目录
- 本会话下 `pwd` / `Get-Location` / `git rev-parse --show-toplevel` 解析出的 **git 仓库根**
- 在 `agent-person` 仓 → `E:\数字永生\agent-person`
- 在 npp 仓 → `F:\software\NF605\npp\606\npp`

> 注意：DSH 一次会话通常只服务于 *一个* 项目。如果任务需要在 *另一个* 仓库（比如 npp）做
> 实际改动 / 写入 / 修改文件，那 **当前仓库必须切到那一个**；否则就该把所有操作限制在当前仓库内（包括只读查询外部仓库，然后把过程文件写到当前仓库 `runtime/`）。

## 允许的写法

| 场景 | 允许位置 | 备注 |
|------|---------|------|
| 任何任务的中间产物（CSV / XLSX / MD / patch / 截图 / 缓存 / log） | `<当前仓库根>/runtime/<子目录>/...` | 推荐命名：`<task-slug>-<date>/` 或 `<branch-or-bug-id>/` |
| 任务最终交付物（用户要求的报告、规格、PR 描述草稿） | `<当前仓库根>/runtime/<子目录>/` 或用户显式指定的目录 | 默认同上；用户另行指定则从其 |
| 用户明确说"放到桌面"、"放到某特定路径" | 用户指定路径 | 用户授权 > 默认规则 |

## 禁止的写法

| 禁止 | 反例 |
|------|------|
| 写入"非当前仓库"的源码树 | 在 npp 仓 `runtime/` 写本次任务的 CSV（即使 .gitignore 屏蔽、即使该路径被 dirs.json 登记过） |
| 写入其它用户工程的源码目录 | `E:\002. 工作记录\xxx\`、`E:\agent_assets\` 等其他项目根下 |
| 写到 `$HOME` 顶层、`C:\Windows`、`C:\Program Files` 等系统/用户根 | 除非用户明确授权 |
| 用 `workdir` 短暂切换后，把文件直接生成在 `workdir` 切换的目的仓库里 | 在 agent-person 切换到 npp 做查询，却在 npp 里 `git checkout` / 写文件 |

## 调试现场快照 / 日志 / crash dump

- 允许放在 `<当前仓库根>/runtime/<task-slug>/evidence/`
- 子目录命名可参考 `evidence/`、`logs/`、`patches/`、`tmp/`

## 跨仓库查询的合法模式（只读）

可以在 npp 仓库做 `git log` / `git rev-list` / `git show` 等**只读操作**，然后用以下任一方式把数据带回当前仓库：

1. **直接在对话里输出**（最常见，推荐）
2. 通过 `git -C <other-repo> ...` 跨仓调用，结果写到 `<当前仓库>/runtime/...`
3. 通过临时中转目录（如 `C:\Users\DELL\AppData\Local\Temp\dsh-scratch-<task-slug>\`），结束任务后清理

**禁止**：把临时中转目录直接放在被查询仓库内。

## 触发本规则的典型场景

- `analysis-only-workflow`、`bug-fix-workflow`、`requirement-dev-workflow` 落地报告 / patch
- `vpp-api-sync` 暂存 `*.api.json`
- `ssh-tools` / `gdb-tools` 抓的日志
- `deploy-build` 的同步状态报告
- 任何自定义的代码审查、commit 统计、bug 单归档、文档生成

## 验证 checklist（在声称任务完成前）

- [ ] `git status` 在被查询的仓库里**没有未跟踪的新文件**（除已被登记的 `runtime/` 自身和 `.claude/`）
- [ ] 所有本次产生的新文件都位于 `<当前仓库根>/runtime/...`
- [ ] `dirs.json` 中登记得当：`<当前仓库根>/runtime` 应已登记
- [ ] 不在 commit 里夹带这些过程文件

## 例外

- 用户**明确**指示写到指定路径 → 从其（但要在 `git status` 中确认不会脏 commit）
- DSH 自身 home（`$DSH_HOME` / `C:\Users\DELL\.dsh`）的写入由 DSH 自己管理，与本规则无关

## 修订记录

- 2026-09-09：创建。起因是 npp 仓库（任务查询目标）被写入 `runtime/branch-check/M19B00_liuxing5_commits.{md,csv}` 两个过程文件，已清理，但规则未明确导致误操作。