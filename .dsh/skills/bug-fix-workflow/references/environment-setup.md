# 修复环境搭建（worktree 工作区 + codegraph 索引 + dirs.json 放行）

> 接 BUG 单开工前，先在本地 npp 仓库派生隔离工作区（git worktree），在 worktree 内执行
> `codegraph init` 建立代码索引，并把工作区登记进 `dirs.json` 开放读写权限。
> 修复全程在该工作区内进行，不直接改主仓库。

## 适用场景

- 开始新的 BUG 修复，需要在隔离工作区编码（不直接改主仓库，如 `npp/606/npp`）
- 需要把工作区登记进 DSH 可读写清单：restricted 模式下文件工具只放行清单目录，
  不登记的工作区一律 MISS 拒绝

## 前置参数（缺失则向用户确认，不猜默认）

| 参数 | 示例 | 说明 |
| ---- | ---- | ---- |
| 本地仓库目录 | `F:/software/NF605/npp/606/npp` | git 仓库本体（remote=gitlab.inone.nsfocus.com/nf/newnf/npp.git） |
| 基础分支 | `release/V6.0R06F02_M02B00` | worktree 派生基准；由 `deploy_config.json` 或用户确认（见 deploy-build SKILL） |
| BUG 单号 | `NEWNF-54398` | 用于命名 fix 分支与工作区 |

> 本机仓库/工作区布局：主仓库 `F:/software/NF605/npp/606/npp`，
> 工作区统一放 `F:/software/NF605/npp/606/npp.worktrees/<名称>`。
> 分支命名习惯：`fix-<BUG单号>`（历史亦有 `bugfix-<单号>`）。

## 步骤

### 1. 确认仓库与基础分支

```bash
git -C <本地仓库> rev-parse --abbrev-ref HEAD   # 当前分支
git -C <本地仓库> branch -r | grep <基础分支>   # 确认 origin 上存在
git -C <本地仓库> worktree list                  # 确认同名工作区未占用
```

### 2. git pull 更新仓库（保证派生基线最新）

```bash
git -C <本地仓库> fetch origin
git -C <本地仓库> checkout <基础分支>
git -C <本地仓库> pull
```

> 拉取后主仓库停在基础分支；也可不切分支，直接从远端跟踪引用派生
> （`git worktree add -b fix-<ID> <path> origin/<基础分支>`），步骤 2 只需 `fetch`。

### 3. 派生 fix-XX 分支 + 工作区

```bash
git -C <本地仓库> worktree add -b fix-<BUG单号> \
  <本地仓库>/npp.worktrees/fix-<BUG单号> <基础分支>
```

- `-b` 自动从基础分支创建并检出 `fix-<BUG单号>` 分支；同一分支不能被两个 worktree
  同时检出，分支已存在时 `worktree add -b` 会失败（先改名/复用/删除）。
- 工作区目录与分支名统一为 `fix-<BUG单号>`，便于按单追溯。

### 4. 在 worktree 内初始化 codegraph 索引

> worktree 是全新派生的代码副本，`.codegraph/` 不在 git 里、不会随 worktree 继承，
> 必须在新建 worktree 后重建索引，后续的符号定位、调用链、影响面分析才有数据。

```bash
codegraph init <worktree>   # 例如 F:/software/NF605/npp/606/npp.worktrees/fix-<BUG单号>
```

- 索引基于 worktree 当前检出分支（`fix-<BUG单号>`）的 HEAD；首次索引大型仓库（如 npp）
  耗时几分钟属正常，后台等待完成即可。
- 开始修改后，用 `codegraph sync` 增量更新索引，不必重复 `init`（init 是全量重建）。
- 索引产物 `.codegraph/` 仅用于本地查询，不要纳入提交（仓库未忽略时提交前排除）。
- 索引建好后，理解架构/定位符号/分析影响面优先走 CodeGraph（`codegraph explore/node/callers/callees/impact`），
  而不是纯文本搜索。

### 5. 开放 dirs.json 读写权限

restricted 模式下工作区必须登记后才能被文件工具读写：

- `python .dsh/tools/writable_dirs.py add <path>` **只接受 workspace 相对路径**，
  对盘符绝对路径（`F:/...`）直接编辑 `.dsh/rules/dirs.json`
  （`.dsh` 目录始终可读写，可用 `edit` 工具修改）。
- 把 worktree 绝对路径追加到 `dirs` 数组即可（无顶层 `worktree` 字段——该字段已于
  2026-09 移除，门控只读 `mode` + `dirs[]`；并行时多个 worktree 各自追加一项，
  互不冲突）：

```json
{
  "mode": "restricted",
  "dirs": [
    { "path": "bug-fix-state", "note": "…" },
    { "path": "runtime", "note": "…" },
    { "path": "F:/software/NF605/npp/606/npp.worktrees/fix-<BUG单号>",
      "note": "fix-<BUG单号> 修复工作区" }
  ],
  "placeholders": []
}
```

- 自检：`python .dsh/tools/writable_dirs.py list` 能看到新目录；对 workspace 内路径用
  `python .dsh/tools/writable_dirs.py check <相对路径>` 判定 HIT/MISS。

### 6. 修复全程在 worktree 内进行

- 分析、编码、自测产物都在 `<worktree>` 下完成，与主仓库隔离。
- 提交：`git -C <worktree> add/commit`；推送：`git -C <worktree> push -u origin fix-<BUG单号>`。

### 7. 收尾清理（可选）

修复合入后：`git -C <本地仓库> worktree remove <worktree>`，并从 `dirs.json` 移除登记项。

## 坑 / 注意

1. **worktree 是全新派生**：`.nsbuild/` 平台配置不在 git 里，编译前需先 `nsbuild-git -p <平台>`
   （平台名查原仓库 `nf/.nsbuild/cur_platform`；详见 deploy_build_worktree编译避坑-20260825.md）。
2. **restricted 门控**：不登记 `dirs.json`，文件工具对工作区一律 MISS 拒绝，无法落盘。
3. **绝对路径登记**：`writable_dirs.py` 拒绝盘符绝对路径，只能直接编辑 `dirs.json`，
   改完注意 JSON 合法（可用 `python writable_dirs.py list` 复验）。
4. **分支占用**：`fix-<BUG单号>` 分支已存在于本地/远端时，`worktree add -b` 失败，
   需改名或先清理。
5. **pull 语义**：主仓库 HEAD 默认跟踪 `origin/master`，直接 `git pull` 拉的是 master；
   要保证基础分支最新须先 `checkout <基础分支>` 再 pull，或仅 `fetch` 后用
   `origin/<基础分支>` 派生。
6. **worktree 需单独建索引**：`.codegraph/` 不进 git、不随 worktree 继承，每个新 worktree
   必须 `codegraph init` 一次；修改期间用 `codegraph sync` 增量同步，不要对主仓库重复全量 init。
   若 `codegraph init` 卡住/中断后无法继续，先 `codegraph status` 或 `codegraph unlock`
   清理陈旧锁文件再重试。
7. **禁止绕道读代码（教训 NEWNF-54251）**：worktree 状态异常（locked/文件缺失）时，必须先修复
   （`worktree unlock` → `remove --force` → 重新 `add -B fix-<ID> <path> origin/master`）再继续，
   **不得**用 `git show <branch>:<path>` / `git grep <branch>` 等 git 对象快照方式替代 worktree 内分析
   ——绕道会失去 codegraph 的调用链/影响面支撑，且分析上下文与修改上下文脱节。
   分析优先级：`codegraph explore/node/callers/callees/impact` > 文本 grep。
