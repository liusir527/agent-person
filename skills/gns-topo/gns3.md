# GNS3 平台特定规则

> 此文件仅在用户选择 GNS3 平台后加载。通用规则见 `skill.md`。

---

## GNS3 原生交换机

### 管理交换机配置（EthernetSwitch）

GNS3 的管理交换机使用 `node_type: ethernet_switch`，适用于管理网络端口扩容：

```yaml
- id: sw_mgmt
  name: 管理交换机
  node_type: ethernet_switch
  symbol: ":/symbols/ethernet_switch.svg"
  left: 250
  top: 50
  properties:
    ports_mapping:
      - name: Ethernet0      # 连接 Cloud
        port_number: 0
        type: access
        vlan: 1
      - name: Ethernet1      # 连接 HA-A 管理口
        port_number: 1
        type: access
        vlan: 1
      - name: Ethernet2      # 连接 HA-B 管理口
        port_number: 2
        type: access
        vlan: 1
      - name: Ethernet3      # 预留
        port_number: 3
        type: access
        vlan: 1
      - name: Ethernet4      # 预留
        port_number: 4
        type: access
        vlan: 1
```

### ⚠️ EthernetSwitch 必须设置 console_type

GNS3 API 要求 ethernet_switch 显式设置 `console_type: "none"`，否则报错：
```
"message": "None is not one of ['telnet', 'none']"
```

部署脚本中：
```python
if node_type in ("ethernet_switch", "ethernet_hub"):
    props.setdefault("console_type", "none")
```

---

## 管理网络连接示例（GNS3）

```yaml
links:
  - src: "cloud_mgmt:0/0"
    dst: "sw_mgmt:0/0"
    description: "Cloud 到管理交换机"

  - src: "fw_a:0/0"
    dst: "sw_mgmt:0/1"
    description: "HA-A 管理口"

  - src: "fw_b:0/0"
    dst: "sw_mgmt:0/2"
    description: "HA-B 管理口"
```

注意：Cloud → 管理交换机 → 各设备管理口。管理交换机与原生态交换机连线使用 `port_number`。

---

## GNS3 部署

### 部署步骤

1. **询问 GNS3 信息**：IP 地址、端口（默认 3080）、用户名、密码
2. **生成部署脚本**：参考 `gns-topo参考代码.py` 逻辑
3. **关键注意**：ethernet_switch 的 `console_type: "none"`

### 部署命令

```bash
python deploy_gns3.py topology.yaml \
  --host <GNS3服务器IP> \
  --port <端口，默认3080> \
  --user <用户名> \
  --password <密码> \
  --recreate  # 删除已有项目重新创建
```

示例：
```bash
python deploy_gns3.py nf_ha_topology.yaml --host 10.66.23.119 --port 3080 --user admin --password admin --recreate
```

### GNS3 默认端口
- API 端口: **3080**（非 80）

---

## GNS3 图标

| 节点类型 | 图标路径 |
|---------|---------|
| PC/服务器 | `:/symbols/pc.svg` |
| 交换机 | `:/symbols/ethernet_switch.svg` |
| 防火墙 | `:/symbols/firewall.svg` |
| Cloud | `:/symbols/cloud.svg` |
