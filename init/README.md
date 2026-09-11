# agent-person 工作区 —— 统一入口（init/）

> 这是整个工作区的**统一入口**。任何 agent 启动后的第一件事：读本目录。
> 通过 init/ 识别"当前工作目录是什么、当前场景是什么、知识大脑在哪、怎么用之前 agent 沉淀的知识"。

## 这是什么

本工作区是 DSH（DeepSeek Harness）环境 + 蜂巢大脑（Hive Brain）知识系统：

| 视图 | 位置 | 内容 |
|------|------|------|
| 工作区视图 | 仓库根 | DSH 配置（`.dsh/`）、NF 插件（`packages/`）、运行时产物（`runtime/`） |
| 大脑视图 | `.dsh-memory/`（submodule） | 全部知识：产品 / SKILL / 场景 / 经验 四类 |

## 快速开始（新 agent 加入共享）

```powershell
# 1. 克隆（含知识大脑 submodule）
git clone --recursive <主仓URL>
cd agent-person

# 2. 拉取最新大脑知识
git submodule update --remote --merge

# 3. 读统一入口
#    - init/manifest.yaml      → 工作区身份 + 当前场景
#    - init/scenes/<scene>.yaml → 场景说明
#    - .dsh-memory/hive.yaml   → 蜂巢能力清单（唯一事实源）

# 4. 检索知识（按场景）
python .dsh-memory/scripts/search.py "关键词" --scene debug
```

## 场景切换

当前场景在 `init/manifest.yaml` 的 `scene:` 字段。切换场景 = 改该字段 + 按场景检索：

```powershell
# 开发场景
python .dsh-memory/scripts/search.py "需求" --scene develop
# 调试场景
python .dsh-memory/scripts/search.py "死锁" --scene debug
# 全场景（蜂巢级）
python .dsh-memory/scripts/search.py "方法论" 
```

> 场景是**逻辑命名空间**（非 git 分支）：`knowledge/scenes/<scene>/` 目录 + skill frontmatter `scene:` 标签。
> 新增场景 = 新建 `init/scenes/<name>.yaml` + `knowledge/scenes/<name>/`，无需切分支。

## 沉淀知识（每个 agent 的义务）

1. **去毒**：沉淀前过"去毒四问"（通用/普适/非一次性/可验证）→ 见 `.dsh/rules/knowledge-sedimentation.md`
2. **生成**：memory-gen skill 写入 `knowledge/<类别>/`
3. **推送**：memory-push skill → `git -C .dsh-memory add/commit/push` → 主仓更新 gitlink → push

## 目录速览

```
init/                        ← 本目录（统一入口）
  manifest.yaml              工作区身份 + 场景 + 大脑引用
  scenes/*.yaml              场景定义
.dsh-memory/                 ← 中央大脑（submodule）
  hive.yaml                  蜂巢能力清单 + 权重参数
  knowledge/{product,skills,scenes,experiences}/   四类知识
.dsh/
  agents/                    蜂巢基座 + 派生 agent
  skills/                    DSH skills（平铺 + scene 标签）
  rules/                     沉淀门禁 / 过程文件规则
  tools/                     link_check / hive_spawn 等工具
```
