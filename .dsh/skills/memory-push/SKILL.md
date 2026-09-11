---
name: memory-push
description: "将沉淀的知识推送到 git 仓库进行保存。适用于 memory-gen 已生成经验文档（.dsh-memory/knowledge/experiences/sparse/*.md）后，需要把知识提交 git 并推送远程备份的场景。触发词包括：推送知识、git保存经验、提交沉淀、同步知识到git、知识入仓。"
scene: null
user-invocable: true
---

# 经验推送 git（memory-push）

用 git 把沉淀的知识提交到仓库并推送到远程备份。

**沉淀知识目录**（memory-gen 的输出，见其规范）：
`<workspace_root>/.dsh-memory/knowledge/experiences/sparse/`
（**路径锚定**：`<workspace_root>` = 当前 git 仓库根，由 LLM 在运行时通过 `git rev-parse --show-toplevel` 解析；
  `.dsh-memory/` 真身即在仓库根下，作为 git submodule 包含 v2 知识库；沉淀位于 v2 的 sparse 层）

**本仓库**：当前 git 工作目录的仓库（由 `git rev-parse --show-toplevel` 得到）；
远程 `origin` 与默认分支由用户在使用本仓库时配置，本 skill 不硬编码具体远端地址。

## 触发时机

- memory-gen 完成经验文档写入、更新了 `索引.md` 之后；
- 或用户直接要求「把经验推到 git / 提交保存」。

## 执行流程（N3：submodule 内提交 + checkout master + pull --rebase）

**关键认知**：`.dsh-memory` 是 git submodule。知识文件必须**在 submodule 内** add/commit/push，
在主仓根 `git add .dsh-memory/...` 只会更新 gitlink 指针（知识文件进不了 submodule 提交）。
标准顺序：**submodule 提交推送 → 主仓更新 gitlink → 主仓提交推送**。

1. **进入 submodule 并切到可写分支**（脱离 clone 时的 detached HEAD）：
   ```bash
   git -C .dsh-memory checkout master
   git -C .dsh-memory pull --rebase origin master   # push 前拉取最新，冲突自动重试（最多 3 次）
   ```

2. **核对改动**（确认只含沉淀相关文件）：
   ```bash
   git -C .dsh-memory status --short
   ```

3. **链接与索引校验（提交前必须 PASS，只扫本次变更文件）**：
   ```bash
   # 知识文件在 submodule 内暂存，用 --repo 指向 submodule 才能扫到
   python "$(git rev-parse --show-toplevel)/.dsh/tools/link_check.py" --repo .dsh-memory
   ```
   - 校验：本次变更知识文件的 frontmatter 必填字段（含 weight/decay_rate/weight_updated_at/knowledge_type）、
     IP/账号/绝对路径/会话号启发式检查、相对链接可达、索引行存在、scene 值定义；
   - 输出 `PASS` 才允许继续提交；`FAIL` 按提示修复后再提交。

4. **submodule 内暂存知识文件**（显式路径，禁用 `git add .`）：
   ```bash
   git -C .dsh-memory add knowledge/experiences/sparse/ \
                           knowledge/experiences/sparse/索引.md \
                           knowledge/experiences/refined/索引.md
   git -C .dsh-memory diff --cached --name-only   # 确认只含沉淀文件
   ```

5. **submodule 内提交 + 推送**（提交信息中文，说明沉淀内容）：
   ```bash
   git -C .dsh-memory commit -m "沉淀经验：<内容概要>"
   git -C .dsh-memory push origin master
   ```

6. **主仓更新 gitlink + 提交 + 推送**：
   ```bash
   git add .dsh-memory
   git commit -m "chore(memory): 同步 .dsh-memory 指针（<内容概要>）"
   git push origin master
   ```

## 常见坑

| 坑                         | 表现                     | 避坑方法                                                     |
| -------------------------- | ------------------------ | ------------------------------------------------------------ |
| 在主仓根 add submodule 路径 | 知识文件没进 submodule 提交，只更新 gitlink | 必须 `git -C .dsh-memory add/commit/push`（步骤 4-5）        |
| submodule 是 detached HEAD | push 丢分支、找不到提交   | 步骤 1 先 `git -C .dsh-memory checkout master`               |
| link_check 显示 FAIL       | 断链/索引不一致/环境残留  | 按提示修复（补链接/索引/去残留），重跑至 PASS 再提交          |
| link_check 扫 0 个文件     | 在主仓根跑，没扫到 submodule 内暂存 | 加 `--repo .dsh-memory`（步骤 3）                            |
| push 被拒（远端领先）      | 冲突                     | 步骤 1 的 `pull --rebase` 保证；仍冲突则手动解决后重试        |
| 提交信息不达意             | 远端历史无法检索         | 中文，说明"沉淀了什么知识"                                   |

## 判定 / 决策依据

- **提交范围**：只提交沉淀知识相关文件（`.dsh-memory/knowledge/` 下 + 索引）；其余一律不碰。
- **提交前置**：`link_check.py` 必须输出 `PASS`；新增 `.md` 必须写索引行、无环境残留。
- **提交顺序**：**先 submodule 后主仓**（gitlink 指针必须指向已推送的 submodule 提交）。
- **何时推送**：每次提交后立即 push，保证远端大脑最新（分散 agent 靠它拉取）。

## 相关

- 经验文档的生成与命名规范见 memory-gen skill
- 稀疏经验索引：`.dsh-memory/knowledge/experiences/sparse/索引.md`
- 链接与索引校验工具：[tools/link_check.py](../../tools/link_check.py)
- v2 知识库入口：[.dsh-memory/README.md](../../.dsh-memory/README.md)（按 refined > sparse > expired 优先级检索）
