---
name: gns-topo
description: GNS3/EVE-NG 拓扑生成指南（通用规则，始终加载）
触发条件：生成拓扑，帮我创建一个拓扑，生成GNS3拓扑，生成EVE-NG拓扑
---

# GNS3 / EVE-NG 拓扑生成指南 — 通用规则

## ⚠️ NF605 防火墙管理口特殊处理（首要规则）

**NF605 的第一个接口 (adapter 0) 是管理口，必须连接到管理网络！**

生成包含 NF605 防火墙的拓扑前，**必须先询问用户**：

1. **是否需要 Cloud 节点作为管理网络出口？**
2. **NF605 管理口应连接到 Cloud 的哪个 eth 接口？**（如 `cloud_mgmt:0/0`）
3. **哪些 adapter 用于业务流量**（非管理网络）

```
检测到拓扑中包含 NF605 防火墙，其第一个接口 (adapter 0) 为管理口，必须接入管理网络。

请确认：
1. 是否需要 Cloud 节点作为管理网络出口？
2. NF605 管理口应连接到 Cloud 的哪个 eth 接口？(如:cloud_mgmt:0/0)
3. 哪些 adapter 用于业务流量？
```

---

## ⚠️ 管理网络端口扩容（平台差异）

**GNS3**: Cloud 节点的每个 eth 接口只能连接一台设备，需要交换机扩容：
```
[Cloud] ─── [管理交换机] ─── [HA-A管理口]
                          ─── [HA-B管理口]
                          ─── [其他设备管理口...]
```

**EVE-NG**: Cloud（pnet）本质是 host 上的桥接网络，多台设备可以直接接入同一个 Cloud，**不需要管理交换机**：
```
[Cloud(pnet1)] ─── [HA-A管理口]
               ─── [HA-B管理口]
               ─── [其他设备管理口...]
```

---

## 概述

本技能用于根据用户需求生成 GNS3/EVE-NG 网络仿真拓扑的 YAML 配置文件。生成的 YAML 可通过部署脚本自动创建 GNS3 工程或 EVE-NG 实验室。

本技能同时支持两类"交换机"表达方式：
- `huawei-ce6800`：交换机用途的 QEMU 虚拟机
- `ethernet_switch` / `ethernet_hub`：原生交换机节点（仅 GNS3）

两者的节点定义和连线规则不同，生成 YAML 时不得混用。

---

## 完整 YAML 结构

```yaml
name: "topology_name"
description: "拓扑描述信息"

project_settings:
  auto_start: false
  grid_increment_x: 50
  grid_increment_y: 50

nodes:
  # 节点定义列表（管理网络放上方，业务流量放下方）

links:
  # 链路定义列表
```

---

## 支持的节点类型

所有 YAML 节点**统一使用 GNS3 模板名**作为 `template` 字段，部署脚本负责将其转换为对应平台的模板名。

### 1. PC/服务器节点 (QEMU)
- **Template**: `linux-ubuntu22.04`
- **Image**: `ubuntu-22-04.qcow2` ⚠️ **必须用连字符，不能用点号！**
- **Node Type**: `qemu`

```yaml
- id: pc_client
  name: PC 客户端
  node_type: qemu
  template: linux-ubuntu22.04
  image: ubuntu-22-04.qcow2
  ram: 1024
  cpu_type: x86_64
  adapters: 1
  symbol: ":/symbols/pc.svg"
  left: 100
  top: 200
```

可选: `ram`(默认 1024), `cpu_type`(x86_64), `adapters`(1-8)

### 2. 防火墙节点 (QEMU)
- **Template**: `NF605`
- **Image**: `manual-produce-41768-test-2021-2-6.qcow2` 或 `nf605.qcow2`
- **Node Type**: `qemu`

**⚠️ adapter 0 是管理口**，必须连接到管理网络。业务流量使用 adapter 1+。

```yaml
- id: firewall
  name: 防火墙 NF605
  node_type: qemu
  template: NF605
  image: manual-produce-41768-test-2021-2-6.qcow2
  ram: 4096
  cpu_type: x86_64
  adapters: 6
  symbol: ":/symbols/firewall.svg"
  left: 500
  top: 275
```

可选: `ram`(建议 4096), `cpu_type`(x86_64), `adapters`(按实际口数)

### 3. CE6800 节点 (交换机用途的 QEMU 虚拟机)
- **Template**: `huawei-ce6800`
- **Image**: `ce6800.qcow2`
- **Node Type**: `qemu`

**关键约束**: QEMU 虚拟机，不是原生交换机。必须用 `adapters`，不能用 `ports`。一个 adapter 只有一个 port `0`，`sw1:0/1` 这类写法错误。

```yaml
- id: sw_access
  name: 接入交换机
  node_type: qemu
  template: huawei-ce6800
  image: ce6800.qcow2
  ram: 4096
  cpu_type: x86_64
  adapters: 4
  symbol: ":/symbols/ethernet_switch.svg"
  left: 300
  top: 200
```

### 4. 原生交换机节点（仅 GNS3）
- **Node Type**: `ethernet_switch` 或 `ethernet_hub`
- 简单二层转发、管理网络端口扩容场景
- 仅当用户明确要求时才生成

---

## 链路配置

### 统一连接格式
- **完整格式**: `node_id:adapter/port`
- **简化格式**: `node_id:adapter`

### CE6800 连线规则
适用对象 `template: huawei-ce6800`。格式 `node_id:adapter/0`，每个 adapter 只有一个 port `0`。

```yaml
links:
  - src: "pc1:0/0"
    dst: "sw_access:0/0"
  - src: "pc2:0/0"
    dst: "sw_access:1/0"
```

### 原生交换机连线规则
适用对象 `node_type: ethernet_switch` / `ethernet_hub`。端口号体现多个 port。

```yaml
links:
  - src: "pc1:0/0"
    dst: "sw_native:0/0"
  - src: "pc2:0/0"
    dst: "sw_native:0/1"
```

### 连线规则判定
1. `template: huawei-ce6800` → QEMU 连线规则
2. `node_type: ethernet_switch` / `ethernet_hub` → 原生交换机规则
3. 不得混用两套规则

### 链路属性
- `src`: 源节点及端口
- `dst`: 目标节点及端口
- `description`: 链路描述（可选）

---

## 拓扑布局规范

### 布局原则
1. **管理网络层在上方**（top 值较小）
2. **业务流量层在下方**（top 值较大）
3. **节点间距保持 150px 以上**，避免重叠
4. **画布整体居中排列**

### 倒V型布局（防火墙HA双机场景）

```
上方 - 管理网络层：
[Cloud] ─── [管理交换机]

下方 - 业务流量层（倒V型）：

      [HA-A防火墙] ← 顶端 (400, 200)
         /        \
[下联交换机]      [上联交换机]
(200, 300)        (600, 300)
    │                 │
[客户端PC]         [服务端PC]
(50, 300)          (750, 300)

    \               /
      [HA-B防火墙] ← 底部 (400, 450)
```

坐标模板：
```yaml
# 管理网络层（上方）
- id: cloud_mgmt:  left: 100, top: 50
- id: sw_mgmt:     left: 250, top: 50
# 倒V顶端 - 主防火墙
- id: fw_a:        left: 400, top: 200
# 倒V左侧腰
- id: sw_downlink: left: 200, top: 300
# 倒V右侧腰
- id: sw_uplink:   left: 600, top: 300
# 左侧终端
- id: pc_client:   left: 50,  top: 300
# 右侧终端
- id: pc_server:   left: 750, top: 300
# 倒V底部 - 备防火墙
- id: fw_b:        left: 400, top: 450
```

---

## 常用拓扑模板

### 1. 简单防火墙测试拓扑
```
[PC] -- [CE6800] -- [NF605] -- [PC Server]
```
→ 参考 `简单防火墙测试拓扑.yaml`

### 2. 防火墙高可用双机拓扑（倒V型）
→ 参考 `防火墙高可用双机拓扑.yaml`

### 3. 多层交换网络拓扑
```
[PC1]--[Access1]--|--[Core]--[NF605]--[互联网]
[PC2]--[Access2]--|
```
→ 参考 `多层交换网络拓扑.yaml`

### 4. 牧原场景测试拓扑
→ 参考 `牧原测试场景.yaml`

---

## 通用注意事项

- 每个节点的 `id` 必须唯一，建议英文小写+下划线
- `links.src` 和 `links.dst` 默认统一引用节点 `id`
- `left` 和 `top` 用于控制节点在画布上的位置
- CE6800 链路端口号不能超过 `adapters` 数量
- 原生交换机链路端口号不能超过其端口定义数量
- NF605 启动时间较长，Ubuntu 节点镜像需预先存在于环境中

### 关键镜像名称规范

| 节点类型 | GNS3 Template | GNS3 Image | EVE-NG Template key | 说明 |
|---------|---------------|------------|---------------------|------|
| PC/服务器 | `linux-ubuntu22.04` | `ubuntu-22-04.qcow2` | `linux` | Ubuntu Linux |
| 防火墙 | `NF605` | `nf605.qcow2` | `nsfocusnf` | 绿盟防火墙 |
| CE6800 | `huawei-ce6800` | `ce6800.qcow2` | `huaweice6800` | 华为交换机 |
| 管理交换机 | `ethernet_switch` | N/A | `huaweice6800` | GNS3原生/EVE用QEMU |

**⚠️ 警告**:
- `ubuntu-22-04.qcow2` 必须严格按此名称（**连字符**，非点号）
- 不得写成 `ubuntu-server-22.04.qcow2`

---

## 使用步骤

1. **需求分析**: 用户描述所需网络拓扑，包括设备类型、数量和连接关系
2. **平台选择**: **询问用户部署到 GNS3 还是 EVE-NG**（见下方）
3. **识别交换机模型**:
   - `huawei-ce6800` → QEMU 节点
   - `ethernet_switch` / `ethernet_hub` → 原生交换机（仅 GNS3）
4. **生成 YAML**: 所有 YAML 使用 GNS3 模板名，部署脚本自动转换平台
5. **验证输出**:
   - YAML 语法正确，节点 `id` 唯一，链路引用有效
   - CE6800 不使用 `ports`，不生成 `0/1`、`0/2` 端口
   - Ubuntu 镜像名: `ubuntu-22-04.qcow2`
6. **确认保存路径**:
   - 若用户未指定输出文件名或路径，必须主动询问
   - 仅允许存储于当前工作目录下，禁止写入子目录或外部路径
7. **导出文件**: 保存为 `.yaml`
8. **部署拓扑**: 根据平台选择，加载对应平台指南执行部署
   - **EVE-NG 部署必须使用 `evengsdk` 库**（禁止用 `requests` 直接调 API）
   - 部署前必须先验证 `evengsdk` 可导入，不可用则终止并提示安装

9. **部署完成后，主动询问是否要进行设备生产（恢复/刷写电子盘）：**

   ```
   拓扑已部署完成。检测到环境包含 NF605 防火墙设备。
   是否需要生产设备（刷写电子盘/配置管理口IP）？
   如需要，请提供串口服务器IP和端口等信息。
   ```

   - 若用户确认，调用 `nf-auto-produce` skill 执行设备生产流程
   - 让用户提供 `tel_ip`、`tel_port`、`mgt_ip`、`mgt_mask`、`mgt_gw`、`image` 等参数
   - 若用户拒绝，则正常结束

---

## ⚠️ 平台选择（关键分支点）

**生成拓扑前必须先询问用户部署平台：**

```
请问您希望将拓扑部署到哪个平台？
1. GNS3
2. EVE-NG
```

选 1 → **加载 `gns3.md`**（GNS3 特定规则、部署参数、脚本文档）
选 2 → **加载 `eve-ng.md`**（EVE-NG 特定规则、模板映射、接口名映射、踩坑笔记）
