---
name: knowledge-sedimentation
order: 40
description: 知识沉淀去毒门禁。任何 agent 向 knowledge/ 沉淀知识前，必须经过"去毒四问"自审；沉淀格式遵循 frontmatter 规范（含 weight/decay_rate/knowledge_type 等字段），提交前必须通过 link_check.py 校验。
---

# 知识沉淀去毒门禁（Hive Brain M5）

## 去毒四问（沉淀任何知识前必过）

每个 agent 在向 `knowledge/` 沉淀知识前，必须逐条自审以下四问，**任一不通过即丢弃**：

1. **通用**：换一个 agent 做同类任务，这条知识还成立吗？
2. **普适**：换一台设备 / 一个环境，它还成立吗？（无 IP/账号/密码/临时路径残留）
3. **非一次性**：它是可复用的规律/流程/判断标准，还是一次性操作记录？
4. **可验证**：下一个人按它操作，能复现出结论吗？（有"怎么做"和"为什么"）

## 沉淀落点（四类分区）

| 类别 | 路径 | 内容 | 默认 decay_rate |
|------|------|------|----------------|
| 产品知识 | `knowledge/product/` | 产品架构、协议、领域事实 | 0.0005/天 |
| SKILL 工具信息 | `knowledge/skills/` | 某工具/技能的使用经验与坑 | 0.005/天 |
| 场景信息 | `knowledge/scenes/<scene>/` | 一个问题一个场景（现象/触发链路/解法/复盘） | 0.02/天 |
| Agent 采集经验 | `knowledge/experiences/`（sparse 层入口） | 通用方法论/流程/判断标准 | 0.01/天 |

## frontmatter 规范（必填字段）

```yaml
id: exp-YYYYMMDD-NNN
summary: 一句话概述
tier: sparse            # experiences 类
category: decision      # 或 methodology/tool/etc
severity: medium
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
weight: 0.5             # 连续权重 0~1（新知识初始 0.5）
decay_rate: null        # null=按类型取默认；可显式覆盖
weight_updated_at: ...  # 权重基准时刻（衰减起算点）
knowledge_type: experience  # product | skill | scene | experience
scene: null             # 场景（product/skills/experience 通用可为 null）
problem_id: null        # 场景知识去重键（同一问题合并用）
```

## 提交门禁

- 提交前运行 `python .dsh/tools/link_check.py`，必须输出 **PASS**；
- link_check 只扫描**本次变更文件**（存量豁免），校验：frontmatter 必填字段齐全、索引行存在、相对链接可达、IP/账号/绝对路径/会话号启发式检查；
- 场景知识 `scene` 值必须存在于 `init/scenes/*.yaml` 定义。

## 强制力边界（如实声明）

- 本门禁 = **格式 + 启发式语义强制**（link_check 硬校验）+ **内容质量软约束**（本规则注入引导 + agent 自审）；
- link_check 能拦截 IP/账号/路径残留与字段缺失，但无法判定"这条知识是否真的通用"——后者依赖 agent 自审诚实度；
- 关键场景沉淀（高风险操作、生产环境）建议额外过 design-reviewer。
