---
name: memory-push
description: "将沉淀的知识推送到 git 仓库进行保存。适用于 memory-gen 已生成经验文档（.dsh-memory/knowledge/experiences/sparse/*.md）后，需要把知识提交 git 并推送远程备份的场景。触发词包括：推送知识、git保存经验、提交沉淀、同步知识到git、知识入仓。"
user-invocable: true
---

  # 经验推送 git（memory-push）

  用 git 把沉淀的知识提交到仓库并推送到远程备份。

  **沉淀知识目录**（memory-gen 的输出，见其规范）：
  `<workspace_root>/.dsh-memory/knowledge/experiences/sparse/`
  （**路径锚定**：`<workspace_root>` = 当前 git 仓库根，由 LLM 在运行时通过 `git rev-parse --show-toplevel` 解析；
    `.dsh-memory/` 真身即在仓库根下，作为 git submodule 包含 v2 知识库；沉淀位于 v2 的 sparse 层）

  **本仓库**：当前 git 工作目录的仓库（由 `git rev-parse --show-toplevel` 得到）；
  远程 `origin` 与默认分支由用户在使用本仓库时配置，
  本 skill 不硬编码具体远端地址。

  ## 触发时机

  - memory-gen 完成经验文档写入、更新了 `索引.md` 之后；
  - 或用户直接要求「把经验推到 git / 提交保存」。

  ## 执行流程

  1. **核对改动**：确认要提交的内容只含沉淀相关文件——
     ```bash
     # 在仓库根（或其任意子目录）下执行：
     git status --short
     ```
     或显式锚定：
     ```bash
     cd "$(git rev-parse --show-toplevel)"
     git status --short
     ```
     期望看到：`.dsh-memory/knowledge/experiences/sparse/*.md`、`.dsh-memory/knowledge/experiences/refined/索引.md`、
     两个 memory skill 定义。仓库已无未登记 gitlink（`nf-auto-produce` 已并入主仓为普通目录），
     但为规避无关改动仍**用显式路径 add，禁用 `git add .` / `add -A`**。

  2. **链接与索引校验（提交前必须 PASS）**：
     ```bash
     # 在仓库根下执行；显式锚定时可写：
     python "$(git rev-parse --show-toplevel)/.dsh/tools/link_check.py"
     ```
     - 校验全部 `.md` 相对链接可达、`init/` 索引与各分区内容一致；
     - 输出 `PASS` 才允许继续提交；`FAIL` 按提示修复后再提交。

  3. **只暂存知识文件**（避免误提交无关改动）：
     ```bash
     # 只暂存知识文件（避免误提交无关改动）；v2 知识库真实路径：
     git add ".dsh-memory/knowledge/experiences/sparse/" \
             ".dsh-memory/knowledge/experiences/sparse/索引.md" \
             ".dsh-memory/knowledge/experiences/refined/索引.md" \
             ".dsh/skills/memory-gen/SKILL.md" \
             ".dsh/skills/memory-push/SKILL.md"
     ```

  4. **确认暂存内容**（只看暂存区，避免工作区残留干扰判断）：
     ```bash
     git diff --cached --name-only
     # 应只列出上述沉淀相关文件（.dsh-memory/...）
     ```

  5. **提交**（提交信息用中文，说明沉淀内容）：
     ```bash
     git commit -m "沉淀经验：<内容概要>"
     ```
     示例：`git commit -m "沉淀经验：GateGuard拦截应对与SKILL编写规范"`

  6. **推送到远程**：
     ```bash
     git push
     ```

  ## 常见坑

  | 坑                         | 表现                     | 避坑方法                                                     |
  | -------------------------- | ------------------------ | ------------------------------------------------------------ |
  | link_check 显示 FAIL       | 有断链或索引与内容不一致 | 按提示修复（补链接目标 / 在索引追加一行），重跑至 PASS 再提交 |
  | 提交信息不达意             | 远端历史无法检索         | 中文，说明"沉淀了什么知识"，可参考触发词/经验概要            |
  | 用 `git status` 判定暂存   | 工作区残留干扰判断       | 改看 `git diff --cached --name-only`，只对暂存区             |
  | 把 `3rd/` 等无关目录当沉淀 | 第三方产物入库           | 只 add 列表内的沉淀文件，其余忽略                            |

  ## 判定 / 决策依据

  - **提交范围**：只提交沉淀知识相关文件（v2 知识库 `.dsh-memory/knowledge/experiences/sparse/` 与 `refined/` 索引、两个 memory skill 定义）；其余一律不碰。
  - **提交前置**：`link_check.py` 必须输出 `PASS`；新增的 `.md` 相对链接必须可达，新增技能/经验必须同步写索引。
  - **何时推送**：每次提交后立即 `push origin main`，保证远端备份最新。

  ## 相关

  - 经验文档的生成与命名规范见 memory-gen skill
  - 稀疏经验索引：`.dsh-memory/knowledge/experiences/sparse/索引.md`
  - 链接与索引校验工具：[tools/link_check.py](../../tools/link_check.py)
  - v2 知识库入口：[.dsh-memory/README.md](../../.dsh-memory/README.md)（按 refined > sparse > expired 优先级检索）
