# 需求开发环境搭建（worktree 工作区 + codegraph 索引 + dirs.json 放行）

> 接需求单开工前，先在本地 npp 仓库派生隔离工作区（git worktree），在 worktree 内执行
> `codegraph init` 建立代码索引，并把工作区登记进 `dirs.json` 开放读写权限。
> 开发全程在该工作区内进行，不直接改主仓库。分支/工作区命名统一 `feature-<需求单号>`。

## 适用场景

- 开始新的需求开发，需要在隔离工作区编码（不直接改主仓库，如 `npp/606/npp`）
- 需要把工作区登记进 DSH 可读写清单：restricted 模式下文件工具只放行清单目录

## 前置参数（缺失则向用户确认，不猜默认）

| 参数 | 示例 | 说明 |
| ---- | ---- | ---- |
| 本地仓库目录 | `<本地npp仓库根>`（如 npp/606/npp） | git 仓库本体（remote=gitlab.inone.nsfocus.com/nf/newnf/npp.git） |
| 基础分支 | `release/V6.0R06F02_M02B00` | worktree 派生基准；由 `deploy_config.json` 或用户确认 |
| 需求单号 | `NEWNF-54398` | 用于命名 feature 分支与工作区 |

## 步骤

### 0. 检测是否已隔离（吸收 superpower-using-git-worktrees）

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
git rev-parse --show-superproject-working-tree 2>/dev/null   # 非空=子模块，按常规仓库处理
```
- `GIT_DIR != GIT_COMMON` 且非子模块 → 已在 worktree 中，跳过派生（注意：平台原生 worktree 工具优先，
  无原生工具才手动 `git worktree add`）。

### 1. 确认仓库与基础分支

```bash
git -C <本地仓库> rev-parse --abbrev-ref HEAD   # 当前分支
git -C <本地仓库> branch -r | grep <基础分支>   # 确认 origin 上存在
git -C <本地仓库> worktree list                  # 确认同名工作区未占用
```

### 2. git pull 更新仓库（保证派生基线最新）

```bash
git -C <本地仓库> fetch origin
```
（不切分支，直接从远端跟踪引用派生：`git worktree add -b feature-<ID> <path> origin/<基础分支>`）

### 3. 派生 feature-XX 分支 + 工作区

```bash
git -C <本地仓库> worktree add -b feature-<需求单号> \
  <本地仓库>/npp.worktrees/feature-<需求单号> origin/<基础分支>
```
- 工作区目录与分支名统一为 `feature-<需求单号>`，便于按单追溯。

### 4. 在 worktree 内初始化 codegraph 索引

```bash
codegraph init <worktree>   # 例如 <本地npp仓库根>/npp.worktrees/feature-<需求单号>
```
- worktree 是全新派生的代码副本，`.codegraph/` 不进 git、不随 worktree 继承，必须新建后 init；
- 修改期间用 `codegraph sync` 增量更新，不必重复 init；
- 若 init 卡住/中断，先 `codegraph status` 或 `codegraph unlock` 清理陈旧锁文件再重试。

### 5. 开放 dirs.json 读写权限

> 说明：早期用 `python .dsh/tools/writable_dirs.py add` 登记，该工具已不存在；现统一直接编辑
> `.dsh/rules/dirs.json`（restricted 门控只读 `mode` + `dirs[]`）。状态目录默认落 `runtime/` 下，
> `runtime` 已在 dirs.json 登记（L2 硬门禁前置），worktree 等额外目录需手动追加。

- 编辑 `.dsh/rules/dirs.json`，把 worktree 绝对路径（或相对路径）追加到 `dirs` 数组（`.dsh` 目录始终可读写）；
- 自检：`python .dsh/tools/path_guard.py validate-path <路径>` 校验落点是否合规（runtime/ 子目录）；restricted 放行以 dirs.json 实际登记为准。

### 6. 验证干净基线（吸收 superpower-using-git-worktrees）

```bash
git -C <worktree> status --porcelain      # 应干净
# 按项目实际测试命令跑基线（若有）：确保后续失败可定位
```
- 脏基线会让后续所有失败无法定位；基线测试失败时报告用户决定是否带病继续。

### 7. 开发全程在 worktree 内进行

- 分析、编码、自测产物都在 `<worktree>` 下完成，与主仓库隔离。
- 提交：`git -C <worktree> add/commit`；推送：`git -C <worktree> push -u origin feature-<需求单号>`。

### 8. 收尾清理（可选）

需求合入后：`git -C <本地仓库> worktree remove <worktree>`，并从 `dirs.json` 移除登记项。

## 坑 / 注意

1. **worktree 是全新派生**：`.nsbuild/` 平台配置不在 git 里，编译前需先 `nsbuild-git -p <平台>`
   （平台名查原仓库 `nf/.nsbuild/cur_platform`）。
2. **restricted 门控**：不登记 `dirs.json`，文件工具对工作区一律 MISS 拒绝，无法落盘。
3. **分支占用**：`feature-<需求单号>` 分支已存在时 `worktree add -b` 失败，需改名或先清理。
4. **禁止绕道读代码**：worktree 状态异常时先修复（`worktree unlock` → `remove --force` → 重新 `add -B`），
   不得用 `git show <branch>:<path>` / `git grep <branch>` 替代 worktree 内分析——绕道失去 codegraph 支撑，
   分析上下文与修改上下文脱节。
5. 分析优先级：`codegraph explore/node/callers/callees/impact` > 文本 grep。
