---
name: mr-merge
description: "MR 合并 / 批量 cherry-pick 工具。输入 commit 列表 + 目标分支，从目标分支 HEAD 派生 XX-MR 分支，按 author-date 从早到晚排序后逐个 cherry-pick；通过文件变更集相交预测冲突，预测会冲突的 commit 汇总到「需人工介入」列表由人工处理，自动阶段成功的 commit 实时落账；人工介入完成后调用 check 子命令逐一校验每个 commit 是否完整到达 MR 分支。触发词：MR合并、合并MR、批量cherry-pick、cherry-pick多个commit、批量合入、分支合并、批量迁移commit、合入多个commit、批量提交迁移、批量 cherry-pick。"
user-invocable: true
---

# MR 合并 / 批量 cherry-pick 工具

把若干 commit 从一条源分支（如 develop）批量合入到目标分支（master / release）。本 skill 是**纯本地 git 操作**，不涉及 SSH / 远端推送 / 编译。

> **路径锚定（强制）**：`mr-state/`、`mr_state.json`、`report.md` 等所有"工作区/状态/报告"路径都相对**当前 git 仓库根**。
> 解析优先级（与 `mr_merge.py` 一致）：
> 1. 环境变量 `MR_PROJECT_ROOT`（显式指定，最优先；指向不存在目录会打印 warning 并回退）
> 2. `git rev-parse --show-toplevel`（在 cwd 或其父目录探测到的 git 根）
> 3. `os.getcwd()` 兜底（脚本被复制到非 git 目录调试时），会打印 warning 提示用户设置 `MR_PROJECT_ROOT`
>
> 本节含义：路径**不**相对当前工作目录、**不**相对 skill 所在目录；搬迁仓库无需改代码。

## 用户请求

$ARGUMENTS

## 工作区布局

```
<项目根>/                                    # git 仓库根（由 MR_PROJECT_ROOT / git 探测 / cwd 兜底确定）
├── mr-state/                                # MR 状态工作区（与 bug-fix-state 平级）
│   └── <MR-NAME>/                           # 例如 mr-state/NEWNF-12345-MR/
│       ├── mr_state.json                    # 状态文件（每个 commit 的状态）
│       └── report.md                        # 报告（成功/需人工/校验 三段式）
└── .dsh/skills/mr-merge/                 # 本 skill 自身
    ├── SKILL.md                             # 本文件
    ├── mr_merge.py                          # 主脚本（_resolve_project_root 实现锚定）
    └── templates/
        └── report.md                        # 报告模板
```

`<MR-NAME>` 通常命名为 `<BUG号>-MR`（如 `NEWNF-12345-MR`）或按团队习惯命名。

## 主流程（六步闭环）

1. **校验输入**：commit 列表中每个 hash 必须存在；目标分支必须存在；当前工作区必须干净（`git status --porcelain` 空）。
2. **排序**：按 `git log -1 --format=%aI <hash>` 取 author-date，升序排序。
3. **冲突预测**：对每个 commit 取 `git show --name-only --format= <hash>` 的文件集，与目标分支相对 base 改的文件集求交；非空即预测冲突，归入「需人工」列表。
4. **派生分支**：`git checkout -b <MR-NAME> <base>` 在本地创建 MR 分支。
5. **串行 cherry-pick**：对"预测安全"的 commit 跑 `git cherry-pick -x <hash>`，成功的写入 `mr_state.json`；失败的也归入「需人工」列表。
6. **人工介入** + **最终校验**：用户拿到"需人工"列表后，手动 cherry-pick --continue；处理完调用 `check` 子命令，脚本逐一 `git log --grep=<hash>` 校验每个 commit 是否完整到达。

## 子命令

| 子命令      | 必填参数                                             | 用途                                                         |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------ |
| `analyze`   | `--commits <id,id,...>` `--base <branch>`            | 只做冲突预测，不改分支不 cherry-pick，输出预测报告           |
| `start`     | `--commits <...>` `--base <branch>` `--mr-name <XX>` | 派生 MR 分支 + 跑自动 cherry-pick + 写状态文件               |
| `resume`    | `--mr-name <XX>`                                     | 跳过已成功的 commit，从中断处继续（配合 `start` 跑一半时用） |
| `check`     | `--mr-name <XX>`                                     | 人工介入完成后，校验 MR 分支上每个 commit 是否完整到达       |
| `status`    | `--mr-name <XX>`                                     | 打印当前 MR 状态摘要（成功 N / 需人工 N / 校验 N）           |
| `report`    | `--mr-name <XX>`                                     | 把状态文件渲染成 markdown 报告，写到 `mr-state/<XX>/report.md` |

> 注意：子命令本身**不带** `--` 前缀（`analyze` 而非 `--analyze`），这是 argparse 子命令的标准写法；`--commits`/`--base`/`--mr-name`/`--repo` 是参数名，带 `--` 前缀。

通用参数：

- `--commits`：commit 列表，逗号分隔或多次传入均可（脚本会合并去重）。
- `--base`：目标分支名（cherry-pick 目标），默认 `master`。
- `--mr-name`：MR 标识，会拼成 `<MR-NAME>` 作为分支名和状态目录名。**禁止包含 `/` `\` ` `（空格）**。
- `--repo <path>`：可选，指定 git 仓库根（默认当前目录）。

## 状态文件 schema（`mr_state.json`）

```json
{
  "mr_name": "NEWNF-12345-MR",
  "base_branch": "master",
  "created_at": "2026-08-26T10:00:00",
  "updated_at": "2026-08-26T10:15:00",
  "commits": [
    {
      "id": "abc1234",
      "title": "fix: ...",
      "author_date": "2026-08-20T15:30:00",
      "files_changed": ["src/foo.c", "src/bar.h"],
      "predicted_conflict": false,
      "conflict_reason": "",
      "status": "cherry_picked",
      "cherry_pick_log": "..."
    }
  ]
}
```

`status` 枚举：
- `pending`：未开始
- `cherry_picked`：自动 cherry-pick 成功
- `manual_required`：预测冲突或自动 cherry-pick 失败，需人工
- `verified`：check 阶段确认已到达 MR 分支

附加字段（向后兼容，旧状态文件无此字段）：
- `pick_method`：`auto` = 自动 cherry-pick 合入；`manual` = 人工介入后合入。由 `start`/`resume`/`check` 写入，供 `report` 区分统计口径。

## 典型调用

```bash
# 1) 先 dry-run 看哪些会冲突
python3 "$SKILL_DIR/mr_merge.py" \
  analyze --commits abc1234,def5678,ghi9012 --base master

# 2) 启动 MR 合并（派生分支 + 自动 cherry-pick 安全项）
python3 "$SKILL_DIR/mr_merge.py" \
  start --commits abc1234,def5678,ghi9012 --base master --mr-name NEWNF-12345-MR

# 3) 查看当前状态
python3 "$SKILL_DIR/mr_merge.py" status --mr-name NEWNF-12345-MR

# 4) 中途崩溃？跳过已成功项继续
python3 "$SKILL_DIR/mr_merge.py" resume --mr-name NEWNF-12345-MR

# 5) 人工介入后做最终校验
python3 "$SKILL_DIR/mr_merge.py" check --mr-name NEWNF-12345-MR

# 6) 输出完整报告
python3 "$SKILL_DIR/mr_merge.py" report --mr-name NEWNF-12345-MR
```

## 冲突预测原理

**核心思想**：commit 改的文件集 ∩ 目标分支（base 之后）改的文件集 ≠ ∅ → 预测冲突。

理由：两个 commit 改同一文件就可能冲突；按 author-date 升序排序后，先合入的 commit 已经把冲突解决掉，后合入的就不会再冲突。这是**静态分析**，不实际跑 cherry-pick。

**预测的边界**：
- ✅ **不会漏报引发数据丢失**：自动 cherry-pick 阶段兜底——失败的 commit 立即 abort 并把剩余未合的 commit 全部归入"需人工"列表。
- ⚠️ **可能误报**：把实际无冲突的 commit 列入"需人工"。误报无害：用户可手动 cherry-pick（多半能直接合上）；也可在人工介入时调用 `resume` 试一次。

## 人工介入流程

1. 跑完 `start`（或 `resume`）后，脚本输出"需人工"列表，每条含：commit hash、标题、改动文件、冲突原因。
2. 切到 MR 分支（`git checkout <MR-NAME>`）。**保持工作区干净**（`check` / `resume` 切分支时会拒绝脏工作区）。
3. 对每个"需人工"的 commit：
   - 如果预测冲突但实际合入没问题：直接 `git cherry-pick -x <hash>`（**务必带 `-x`**，否则 `check` 阶段无法识别该 commit）。
   - 如果 cherry-pick 中途冲突：解冲突 → `git add <files>` → `git cherry-pick --continue`。
4. 处理完通知 skill："已完成人工介入"。
5. 调用 `check` 做最终校验：脚本逐一 `git log --grep="cherry picked from commit <hash>"` 在 MR 分支上验证。
6. 调用 `report` 输出一份完整报告（含每条 commit 的最终状态 + 校验结果），写到 `<项目根>/mr-state/<MR-NAME>/report.md`。

## 报告输出

报告路径：`<项目根>/mr-state/<MR-NAME>/report.md`

结构（参见 `templates/report.md`）：

```markdown
# MR 合并报告 - <MR-NAME>

## 基本信息
- 目标分支: master
- 派生时间: 2026-08-26 10:00:00
- commit 总数: 5
- 自动 cherry-pick 成功: 3
- 需人工介入: 2（人工介入已合入: 1）

## 自动 cherry-pick 成功 (3)
| commit | 标题 | author-date | 改动文件数 |
|--------|------|-------------|-----------|
| abc1234 | ... | ... | ... |

## 需人工介入 (2)
| commit | 标题 | 冲突原因 | 处理状态 |
|--------|------|---------|---------|
| def5678 | ... | 改动文件 [src/foo.c, src/bar.h] 与目标分支改动文件重叠 | 未处理 |
| 9ijklmn | ... | 自动 cherry-pick 失败 | 已人工合入 |

## 最终校验 (check 阶段输出)
| commit | 状态 | MR 分支上是否到达 |
|--------|------|------------------|
| abc1234 | verified | ✅ |
| def5678 | verified | ✅ |
```

## 风险与约束

| 风险                     | 缓解                                                         |
| ------------------------ | ------------------------------------------------------------ |
| 静态冲突预测漏报         | 自动 cherry-pick 失败立即 abort，剩余 commit 全部归入"需人工" |
| 静态冲突预测误报         | 无害：用户可手动 cherry-pick 或 `resume` 试一次            |
| MR 分支与当前分支冲突    | 启动前强制 `git status --porcelain` 必须为空，否则拒绝       |
| 同名 MR 分支已存在       | `start` 检测到同名分支时拒绝并提示先删除或换名             |
| 脚本中途崩溃留半完成状态 | `mr_state.json` 每完成一个 commit 原子写一次；`resume` 跳过已完成项 |
| 跨平台中文文件名         | `git_cmd()` 用 `encoding="utf-8", errors="replace"`（沿用 deploy_build 的方案） |

## 与其他 skill 的关系

- **不依赖** `deploy_build`：本 skill 是纯本地 git 操作，不需要 SSH / 编译 / 安装。
- **不依赖** `bug-fix-workflow`：MR 合并是批处理流程，与单条 BUG 链路的状态机语义不同，强行套用会让两边都复杂。
- **风格** 借鉴 `deploy_build`：Python 脚本 + argparse 子命令 + UTF-8 subprocess + 报告输出。

## 触发词

`MR合并` / `合并MR` / `批量cherry-pick` / `cherry-pick多个commit` / `批量合入` / `分支合并` / `批量迁移commit` / `合入多个commit` / `批量提交迁移` / `批量 cherry-pick`
