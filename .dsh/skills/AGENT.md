# skills/ · 技能分区说明

> 本目录存放可复用的技能定义，每个技能一个子目录，内含 `SKILL.md` 元数据定义 + 实现脚本/工具。
> 技能索引与导航见 [../init/skills-index.md](../init/skills-index.md)。

## 技能清单（13 个）

| 技能 | 目录 | 一句话用途 |
|------|------|-----------|
| bug-fix-workflow | [bug-fix-workflow/SKILL.md](bug-fix-workflow/SKILL.md) | 网络安全设备项目的端到端 BUG 修复工作流 |
| requirement-dev-workflow | [requirement-dev-workflow/SKILL.md](requirement-dev-workflow/SKILL.md) | 需求开发工作流（聚焦 VPP/npp 层）：需求澄清→设计→评审→实施→受限环境测试→交付，含状态机引擎与常态策略 |
| certificate-apply | [certificate-apply/SKILL.md](certificate-apply/SKILL.md) | 绿盟内部支持系统的证书申请全流程自动化 |
| deploy-build | [deploy-build/SKILL.md](deploy-build/SKILL.md) | 增量部署编译 NPP 项目（同步→编译→推送） |
| gdb-tools | [gdb-tools/SKILL.md](gdb-tools/SKILL.md) | 接入远程设备已 attach 到 VPP 的 GDB 会话 |
| gns-topo | [gns-topo/SKILL.md](gns-topo/SKILL.md) | GNS3 / EVE-NG 拓扑生成指南 |
| lightrag | [lightrag/SKILL.md](lightrag/SKILL.md) | LightRAG 知识图谱工具（CLI 交互） |
| memory-gen | [memory-gen/SKILL.md](memory-gen/SKILL.md) | 任务完成后生成经验沉淀文档 |
| memory-push | [memory-push/SKILL.md](memory-push/SKILL.md) | 将沉淀的知识推送到 git 仓库保存 |
| mr-merge | [mr-merge/SKILL.md](mr-merge/SKILL.md) | MR 合并 / 批量 cherry-pick 工具 |
| nf-auto-produce | [nf-auto-produce/SKILL.md](nf-auto-produce/SKILL.md) | NF 防火墙自动化生产 |
| nf-config-procedures | [nf-config-procedures/SKILL.md](nf-config-procedures/SKILL.md) | 绿盟 NF 防火墙配置流程库 |
| ssh-tools | [ssh-tools/SKILL.md](ssh-tools/SKILL.md) | Windows 平台轻量 SSH 工具 |

## 约定

- 每个技能一个独立子目录，含 `SKILL.md` + 配套脚本/模板
- 新增技能后同步更新 `../init/skills-index.md`
- 配套工具（如状态机引擎）放在技能自己的子目录内