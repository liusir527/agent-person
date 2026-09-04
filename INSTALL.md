# agent-person 安装手册（INSTALL.md）

> **本文档是 dsh 环境自动配置的执行依据**。Agent 在 clone 本仓库后
> 应阅读本手册，并按 "安装步骤" 执行 `setup.ps1`，完成整个数字人
> 环境的安装部署。本文档本身也可由人工按步骤操作。

---

## 1. 仓库结构

```
agent-person/                    # 数字人总仓（git）
├── 设计方案.md / 设计方案.v2.md  # 设计文档（v2 为当前有效版本）
├── 执行方案.md                    # 执行方案与状态追踪
├── INSTALL.md                    # 本文件：安装手册（agent 执行依据）
├── setup.ps1                     # 幂等安装脚本（可重复执行）
├── config/                       # 安装模板（setup.ps1 实例化）
│   ├── AGENTS.md.template        #   记忆规则指令模板
│   └── mcp-memory.patch.yml.template  #   MCP 服务器注册片段
└── .dsh-memory/                  # 记忆系统子仓（git submodule）
    ├── PERSONA.md                # 身份、偏好
    ├── config.yaml               # 索引配置
    ├── knowledge/                # 知识库（md 真源）
    ├── scripts/                  # 索引/检索/分词脚本
    ├── test_smoke.py             # 冒烟测试
    └── README.md                 # 子仓自身说明
```

## 2. 前置条件

| 组件 | 要求 | 验证命令 |
| :--- | :--- | :--- |
| git | ≥ 2.30 | `git --version` |
| python | ≥ 3.10（含 sqlite3 模块） | `python --version` |
| dsh | 已安装（0.1.x） | `dsh --version` |
| pip | 可用 | `python -m pip --version` |

## 3. 安装步骤

### 3.1 克隆仓库（含子仓）

```powershell
git clone --recursive <repo-url> agent-person
cd agent-person
```

> 若 clone 时未带 `--recursive`，或子仓为空，执行：
> `git submodule update --init --recursive`

### 3.2 运行安装脚本（幂等，可重复执行）

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` 依次完成（每步可独立验证）：

1. **校验前置条件**（git / python / dsh 存在）
2. **初始化子仓**（`git submodule update --init --recursive`）
3. **部署记忆库**：将 `.dsh-memory/` 子仓内容同步到
   `%USERPROFILE%\.dsh-memory`（默认；可用 `-MemoryDir` 覆盖）
4. **安装 Python 依赖**（`pip install jieba pyyaml`）
5. **写入 DSH 记忆规则**：由 `config/AGENTS.md.template` 生成
   `%USERPROFILE%\.dsh\AGENTS.md`（若不存在）
6. **注册 MCP 工具通道**（方案 B）：
   - 若 `@deepseek-ai/dsh-mcp-client` 未安装 → `dsh plugin --profile web add`
   - 若 `cordis.patch.yml` 无 `mcp-memory` 条目 → 从模板插入
   - 输出当前 profile 使用的插件注册片段（供人工粘贴到
     `%USERPROFILE%\.dsh\profiles\<profile>\cordis.patch.yml` 或由
     `-WritePatch` 自动写入）
7. **重建索引**：`python %USERPROFILE%\.dsh-memory\scripts\rebuild.py`
8. **冒烟验证**：跑 `test_smoke.py` + 一次中文检索查询
9. **输出安装报告**（成功项 / 失败项 / 后续人工步骤）

### 3.3 参数

| 参数 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `-MemoryDir` | `%USERPROFILE%\.dsh-memory` | 记忆库部署位置 |
| `-Profile` | `web` | 目标 dsh profile |
| `-ServerName` | `memory` | MCP serverName（工具名前缀 `mcp__<name>__`） |
| `-WritePatch` | `$false` | 自动把 MCP 注册写入 profile 的 cordis.patch.yml |
| `-SkipInstall` | `$false` | 跳过 pip 安装（已装好时加速） |
| `-SkipIndex` | `$false` | 跳过索引重建 |
| `-DryRun` | `$false` | 只打印将要执行的动作，不执行 |

## 4. 验证清单（安装完成后）

| # | 验证项 | 方法 |
| :--- | :--- | :--- |
| 1 | 记忆库就位 | `Test-Path "$env:USERPROFILE\.dsh-memory\scripts\query.py"` |
| 2 | 索引可检索 | `python "$env:USERPROFILE\.dsh-memory\scripts\query.py" '{"query":"容器"}'` |
| 3 | AGENTS.md 注入 | 新开会话，观察 system-reminder 是否含"记忆库使用规则" |
| 4 | MCP 工具可见 | 新开会话，工具列表应含 `mcp__memory__memory_search/save/read` |
| 5 | 冒烟测试全过 | `python "$env:USERPROFILE\.dsh-memory\test_smoke.py"` → 30/30 PASS |

## 5. 升级与维护

```powershell
# 拉取主仓更新
git pull
# 拉取子仓更新（随主仓版本）
git submodule update --init --recursive
# 重新部署（幂等）
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

> 子仓 URL 说明：`.gitmodules` 中的 url 指向记忆库远端仓库。
> 分发前请 `git submodule set-url .dsh-memory <你的远端地址>` 并把
> 记忆库推送至远端；新机器 `clone --recursive` 即自动带入。

## 6. 常见问题

- **submodule 为空**：`git submodule update --init --recursive`
- **MCP 工具不出现**：确认第 6 步注册片段已写入对应 profile 的
  `cordis.patch.yml`，并重启 dsh web 进程
- **中文检索无结果**：先跑 `python scripts/rebuild.py` 重建索引
- **pip 提示无权限**：用 `python -m pip install --user jieba pyyaml`
