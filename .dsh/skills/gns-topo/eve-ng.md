# EVE-NG 平台特定规则

> 此文件仅在用户选择 EVE-NG 平台后加载。通用规则见 `skill.md`。

---

## 核心原则

**YAML 统一使用 GNS3 模板名**，部署脚本通过 `TEMPLATE_MAP` 自动转换。

**⚠️ 部署必须使用 `evengsdk` 库，禁止用 `requests` 直接调 EVE-NG API！**

原因：
- evengsdk 封装了认证、session 管理、接口名解析等逻辑，直接用 requests 需自行处理 token/cookie，容易出错
- evengsdk 的 `EvengClient` 提供了 `add_node`、`connect_node_to_node`、`connect_node_to_cloud` 等语义化方法，代码更清晰
- 踩坑笔记中的问题（create_lab 500、session 不兼容等）已在 evengsdk 层面处理

部署前必须验证 evengsdk 可用：
```bash
python -c "import evengsdk; print(evengsdk.__version__)"
```
若不可用，终止部署并提示：
```
[ERROR] evengsdk 未安装，EVE-NG 部署必须使用 evengsdk。
安装命令：pip install evengsdk
```

---

## 模板名映射

| YAML template (统一用 GNS3 名) | EVE-NG template key |
|-------------------------------|---------------------|
| `NF605` | `nsfocusnf` |
| `huawei-ce6800` | `huaweice6800` |
| `linux-ubuntu22.04` | `linux` |

管理交换机在 EVE-NG 中也用 `huawei-ce6800`（QEMU 交换机），**不使用 IOL**。

```python
TEMPLATE_MAP = {
    "NF605":              "nsfocusnf",
    "huawei-ce6800":      "huaweice6800",
    "linux-ubuntu22.04":  "linux",
}
```

---

## 接口名称映射（关键！）

**EVE-NG 使用真实接口名，不是 `eth0/0` 格式。部署脚本必须用 `IFACE_MAP` 转换。**

| 模板 key | adapter 0 | adapter 1 | adapter 2 | adapter 3 | adapter 4 | adapter 5 |
|---------|-----------|----------|----------|----------|----------|----------|
| `nsfocusnf` | `MEth0/0/0` (管理口) | `Gi1/0` | `Gi2/0` | `Gi3/0` | `Gi4/0` | `Gi5/0` |
| `huaweice6800` | `MEth0/0/0` (管理口) | `GE1/0/0` | `GE1/0/1` | `GE1/0/2` | - | - |
| `linux` | `e0` | `e1` | `e2` | ... | - | - |

```python
IFACE_MAP = {
    "nsfocusnf": {
        0: "MEth0/0/0", 1: "Gi1/0", 2: "Gi2/0", 3: "Gi3/0", 4: "Gi4/0", 5: "Gi5/0",
    },
    "huaweice6800": {
        0: "MEth0/0/0", 1: "GE1/0/0", 2: "GE1/0/1", 3: "GE1/0/2",
    },
    "linux": {},  # Dynamic: e{adapter}
}
```

Linux 接口名动态生成：
```python
def get_iface(template_key, adapter):
    if template_key == "linux":
        return f"e{adapter}"
    return IFACE_MAP.get(template_key, {}).get(adapter)
```

---

## Cloud / 管理网络（EVE-NG）

EVE-NG 的 Cloud（pnet）是 host 上的桥接网络，**多台设备可以直接接入同一个 Cloud，不需要管理交换机做端口扩容**。

这与 GNS3 不同：GNS3 Cloud 每个 eth 接口只能连接一台设备，需要交换机扩容。EVE-NG 的 pnet 本身就是一个二层桥，所有接入的设备在同一网段内直接互通。

用 `node_type: nat` + `network_type` 表达：

```yaml
- id: cloud_mgmt
  name: cloud1
  node_type: nat
  network_type: pnet1
  icon: ":/symbols/cloud.svg"
  left: 100
  top: 50
```

### network_type 对照表

| network_type | 对应 | 说明 |
|-------------|------|------|
| `pnet0` | host eth0 | 默认管理网 |
| `pnet1` | host eth1 | 扩展网段 |
| `bridge` | 内部桥接 | 仅 lab 内部通信 |

**cloud1 必须用 `pnet1`**，否则防火墙无法通过 host eth1 通信。

---

## EVE-NG 节点 YAML 示例

### 防火墙
```yaml
- id: fw_a
  name: FW-A
  node_type: qemu
  template: NF605     # ← 统一用 GNS3 模板名，脚本自动转
  ram: 4096
  cpu: 2
  adapters: 6
  icon: ":/symbols/firewall.svg"
  left: 400
  top: 200
```

### 交换机
```yaml
- id: sw_downlink
  name: CE6800-Downlink
  node_type: qemu
  template: huawei-ce6800
  ram: 4096
  cpu: 2
  adapters: 4
  icon: ":/symbols/Switch.png"
  left: 200
  top: 300
```

### PC
```yaml
- id: pc_client
  name: PC-Client
  node_type: qemu
  template: linux-ubuntu22.04
  image: ubuntu-22-04.qcow2
  ram: 1024
  cpu: 1
  icon: ":/symbols/Server.png"
  left: 50
  top: 300
```

---

## EVE-NG 图标

**⚠️ EVE-NG 只接受 `.png` 文件名作为 icon，不接受 GNS3 格式（`:/symbols/firewall.svg`）。**
YAML 中仍写 GNS3 格式，部署脚本通过 `ICON_MAP` 自动转换。

| 节点类型 | YAML icon（GNS3 格式） | EVE-NG 实际 icon |
|---------|----------------------|-----------------|
| 防火墙 | `:/symbols/firewall.svg` | `Firewall.png` |
| 交换机 | `:/symbols/Switch.png` 或 `:/symbols/ethernet_switch.svg` | `Switch.png` |
| PC/服务器 | `:/symbols/Server.png` 或 `:/symbols/pc.svg` | `Desktop.png` |
| Cloud | `:/symbols/cloud.svg` | `Cloud.png` |
| 路由器 | `:/symbols/router.svg` | `Router.png` |

若 YAML icon 不在 `ICON_MAP` 中，脚本按模板回退：`nsfocusnf→Firewall.png`、`huaweice6800→Switch.png`、`linux→Desktop.png`

---

## EVE-NG 部署

### 部署步骤

1. **询问 EVE-NG 信息**：IP 地址、端口（默认 80）、用户名、密码
2. **生成部署脚本**：参考 `eve-ng.py` 逻辑
3. **关键注意**：EVE-NG 必须认证，cloud 不能 add_node

### 部署命令

```bash
# 旧式用法（向后兼容）
python eve-ng.py topology.yaml \
  --host <EVE-NG服务器IP> \
  --port <端口，默认80> \
  --user <用户名> \
  --password <密码> \
  --recreate  # 删除已有实验室重新创建

# 新式用法（推荐）
python eve-ng.py deploy topology.yaml \
  --host <EVE-NG服务器IP> --port 80 --user admin --password eve --recreate
```

示例：
```bash
python eve-ng.py deploy nf_ha_topology.yaml --host 10.66.23.119 --port 80 --user admin --password eve --recreate
```

### 启动/停止/查看节点

```bash
# 启动所有节点
python eve-ng.py start topology.yaml --host <IP> --user admin --password eve

# 启动单个节点
python eve-ng.py start topology.yaml --host <IP> --user admin --password eve --node FW-A

# 停止所有节点
python eve-ng.py stop topology.yaml --host <IP> --user admin --password eve

# 停止单个节点
python eve-ng.py stop topology.yaml --host <IP> --user admin --password eve --node FW-A

# 查看节点状态和 console 地址
python eve-ng.py list topology.yaml --host <IP> --user admin --password eve

# 指定 lab 名称（覆盖 YAML 中的 lab name）
python eve-ng.py start topology.yaml --host <IP> --lab HA_Test --node FW-A
```

### EVE-NG 默认端口
- API 端口: **80**（HTTP），非 443

---

## 部署脚本核心逻辑

脚本位置：`eve-ng.py`（与 skill.md 同目录）

关键处理流程：
1. **登录**: 用 evengsdk `EvengClient` 或 requests 都可以，evengsdk 优先
2. **创建 lab**: `create_lab(name, path="/", ...)`，捕获 "already exists" 异常
3. **Cloud 节点跳过 add_node**：`node_type == "nat"` 的跳过
4. **创建节点**: `add_node(path, name, template=eve_template, ethernet=adapters, ...)`
5. **创建 Cloud 网络**: `add_lab_network(lab_path, network_type='pnet1', name='cloud1')`  
6. **连接 Cloud**: `connect_node_to_cloud(lab_path, src=节点名, src_label=接口名, dst=网络名)`
7. **连接节点**: `connect_node_to_node(lab_path, src, src_label, dst, dst_label)`
8. **接口名解析**: 用 `IFACE_MAP[template_key][adapter]` 查真实接口名
9. **adapter 数量**: `count_adapter_usage()` 自动统计链路所需 adapter 数

---

## 已知问题（踩坑笔记）

### 1. create_lab 报 500 错误
**现象**：`EvengClient` 登录后 `create_lab` 报 500，PHP `__lab.php Line:64`。
**原因**：evengsdk 的 session 处理与部分 API 不兼容。
**解决**：异常捕获后继续。

### 2. YAML 名称不能用非 ASCII 字符
**现象**：lab 名称含中文所有节点被 SKIP（options error）。
**原因**：EVE-NG 后端 PHP 不接受非 ASCII 字符。
**解决**：所有名称必须英文/ASCII。

### 3. CE6800 模板默认只有 2 口
**现象**：连接 `GE1/0/1` 报 `invalid or missing`。
**原因**：`huaweice6800` 模板默认 2 口。
**解决**：创建时指定 `adapters=4`。

### 4. Cloud 节点不能 add_node
**现象**：`node_type: nat` 节点报错。
**原因**：cloud 是虚拟网络。
**解决**：跳过 add_node，改用 `add_lab_network` + `connect_node_to_cloud`。

### 5. connect_node_to_cloud 方向判断
**现象**：报 `network FW-A not found`。
**原因**：`src_is_cloud` 时错误用了 `dst_conf` 获取网络名。
**解决**：
- `src_is_cloud` → `src_conf.get("name")`
- `dst_is_cloud` → `dst_conf.get("name")`
