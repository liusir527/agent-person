# MR 合并报告 - {MR_NAME}

> 由 `mr_merge.py report` 自动生成。修改请同步更新 mr_state.json。

## 基本信息

| 项目                  | 值            |
| --------------------- | ------------- |
| MR 标识               | {MR_NAME}     |
| 目标分支              | {BASE_BRANCH} |
| 派生时间              | {CREATED_AT}  |
| 最后更新              | {UPDATED_AT}  |
| commit 总数           | {N_TOTAL}     |
| 自动 cherry-pick 成功 | {N_PICKED}    |
| 需人工介入            | {N_MANUAL}    |
| 人工介入已合入        | {N_MANUAL_RESOLVED} |
| check 阶段已校验      | {N_VERIFIED}  |

## 自动 cherry-pick 成功 / check 已通过

{PICKED_TABLE}

## 需人工介入

> 切到 MR 分支手动 cherry-pick 或解冲突后 `git cherry-pick --continue`，
> 处理完跑 `python3 mr_merge.py check --mr-name {MR_NAME}` 校验。
> 「处理状态」列：未处理 = 仍待人工；已人工合入 = 人工介入后 check 校验通过。

{MANUAL_TABLE}

## 最终校验（check 阶段输出）

> 校验方式：在 MR 分支上 `git log --grep="(cherry picked from commit <hash>)"`，命中即视为到达。

{VERIFIED_TABLE}

## 后续

- 全部 [OK] 后：`git push origin {MR_NAME}` 推到远端，发起 MR
- 部分 [WARN]：人工介入补完后再次 `check` 校验
- 完结：可手工 `rm -rf <项目根>/mr-state/{MR_NAME}` 清理工作区

## 相关

- skill 定义：<项目根>/.dsh/skills/mr-merge/SKILL.md
- 主脚本：<项目根>/.dsh/skills/mr-merge/mr_merge.py
- 状态文件：<项目根>/mr-state/{MR_NAME}/mr_state.json
