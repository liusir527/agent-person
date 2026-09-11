---
name: device-platform-detect
description: "获取NF设备型号/电子盘类型/平台类型，确定 nsbuild-git -p 平台参数与 setup 选择。通过询问用户或 SSH 查看目标设备（cat /opt/nsfocus/etc/version.txt | grep packet_version）解析 packet_version（[项目名称]_[硬件架构]_[校验号]_[编译时间]），映射到 X86/C621/C621双、E2000Q、海光3/海光5 等平台；无法确定时把原始 packet_version 发给用户询问类型。触发词：设备型号、电子盘类型、平台类型、nsbuild-git -p、packet_version、version.txt、setup选择。"
scene: debug
user-invocable: true
---

# 设备平台类型探测（device-platform-detect）

在需要确定 NF 设备**型号 / 电子盘类型 / 平台类型**、或执行 `nsbuild-git -p` 前必须确定平台参数时使用。

## 触发场景

- 需要获取设备的**型号**
- 需要确定**电子盘类型**对应的 setup
- 准备执行 **`nsbuild-git -p <平台>`**，需要先确定平台参数
- 需要选择 **setup**（`X86_CNEOS_3.16.35` / `ARM64_CNEOS_5.4.18` / `X86_CNEOS_5.4.18`）

## 平台类型获取方式（二选一）

### 方式 A：询问用户（优先）

用户能直接告知设备型号 / 平台（如 X86/C621、E2000Q、海光3/海光5）时，直接采用用户给出的类型，跳过设备查询。

### 方式 B：从目标设备获取

先加载 `ssh-tools` skill（`<项目根>/.dsh/skills/ssh-tools/`，按该 SKILL.md 方式 SSH 登录设备），执行：

```bash
cat /opt/nsfocus/etc/version.txt | grep packet_version
```

## packet_version 解析

命令输出示例：

```
packet_version=NF606F02M02B00_x86_cc97e1d0_20260818143639
```

去掉 `packet_version=` 或 `packet_version:` 前缀（实测两种分隔符均可能出现）后，按 `_` 下划线分段，格式为：

```
[项目名称]_[硬件架构]_[校验号]_[编译时间]
```

| 段 | 含义 | 示例值 |
|----|------|--------|
| 项目名称 | 产品项目代号 | NF606F02M02B00 |
| 硬件架构（平台段） | 决定 nsbuild-git -p 平台 | x86 |
| 校验号 | 代码校验号 | cc97e1d0 |
| 编译时间 | 打包编译时间（YYYYMMDDHHMMSS） | 20260818143639 |

## 平台映射表

| packet_version 平台段 | nsbuild-git -p 平台 | setup 选择 | 俗称 |
|------------------------|---------------------|------------|------|
| x86 | X86 | X86_CNEOS_3.16.35 | X86 / C621 / C621双 |
| ft_2000s_arm64 | fte2000q | ARM64_CNEOS_5.4.18 | E2000Q / e2000q |
| HG_x86 | HG_X86 | X86_CNEOS_5.4.18 | 海光3 / 海光5 |

实测示例对照：

| packet_version | 平台 | setup |
|----------------|------|-------|
| NF606F02M02B00_x86_cc97e1d0_20260818143639 | X86 | X86_CNEOS_3.16.35（俗称 X86/C621/C621双） |
| NF606F02M19B00_ft_2000s_arm64_00569312_20260828111801 | fte2000q | ARM64_CNEOS_5.4.18（俗称 E2000Q/e2000q） |
| NF606F02M19B00_HG_x86_05f1fd5d_20260827185040 | HG_X86 | X86_CNEOS_5.4.18（俗称 海光3/海光5） |

## 判定流程

1. 先询问用户是否已知设备平台类型；不知道时走方式 B 设备查询。
2. 解析 packet_version 平台段，查平台映射表得到 `nsbuild-git -p` 平台参数与 setup 选择。
3. **无法确定时**（平台段不在映射表、命令无输出、设备不可达）：把原始 `packet_version` 原样发给用户，明确询问属于哪一种类型，并附上已知选项（X86/C621/C621双、E2000Q/e2000q、海光3/海光5），等待用户确认后再继续。

## 注意事项

- `version.txt` 路径固定为 `/opt/nsfocus/etc/version.txt`，不要猜测其他路径。
- 平台段大小写敏感（`HG_x86` ≠ `x86`），按下划线精确分段后逐段比对。
- 校验号、编译时间仅用于唯一标识某一版本的构建，不参与平台判定。
- 电子盘（edisk）类型与平台绑定，先定平台再选对应 setup / 电子盘，不要反推。

## 相关

- SSH 登录设备执行命令：[../ssh-tools/SKILL.md](../ssh-tools/SKILL.md)
- 平台参数用于增量部署编译 NPP：[../deploy-build/SKILL.md](../deploy-build/SKILL.md)
- 技能索引：[../../init/skills-index.md](../../init/skills-index.md)
