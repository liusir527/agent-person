# 经验抽取（lite 版）

> bug-fix-workflow `references/reasoning-extraction.md` 的 lite 版。**lite 流程不强制 memory-gen 沉淀**，但鼓励在结论文档中保留可复用思路。

## 1. 何时沉淀

满足下列任一条件，**建议**沉淀到 `.dsh-memory/knowledge/experiences/sparse/`：

- 找到了非显然的根因（不是表面报错）
- 修复模式可复用到同类问题
- 反模式（要避免的）值得记录
- 涉及多个模块的协同逻辑

**不强制的理由**：lite 流程是临时性、轻量分析，不是产线 BUG 修复，长期价值密度可能低。

## 2. 沉淀方法

按 bug-fix-workflow / memory-gen 的标准流程：

```bash
# 1) 生成经验文档（手动或调用 memory-gen skill）
# 命名格式：<知识概要>-YYYYMMDD.md
# 路径：<workspace_root>/.dsh-memory/knowledge/experiences/sparse/

# 2) 更新索引（手动或 memory-gen 自动）

# 3) 推 git（手动或调用 memory-push skill）
```

**不要**在结论文档中粘贴完整经验文档——结论文档放精简版，详细经验放稀疏经验库。

## 3. 结论文档应保留的可复用思路

- 一句话根因
- 关键代码位置（路径 + 行号）
- 修复模式（如"在 XXX 处加 NULL 检查"）
- 边界态覆盖情况
- 未解决问题（如有）

## 4. 不沉淀的场景

- 一次性临时分析
- 与已有经验重复
- 用户未要求沉淀
- 改动仅限配置项 / 临时调参

## 5. 与 bug-fix-workflow 沉淀差异

| 维度 | bug-fix-workflow | analysis-only-workflow |
|------|------------------|------------------------|
| close 强制校验 | 是 | 否（建议但不强制） |
| 经验文档格式 | 严格按 EXPERIENCE-FORMAT.md | 灵活（精简版即可） |
| 推送 git 强制 | 是 | 否 |
| 索引更新强制 | 是 | 否 |