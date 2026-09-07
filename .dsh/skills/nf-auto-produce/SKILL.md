---
name: nf-auto-produce
description: NF防火墙设备自动化生产工具，支持恢复(recover)、配置(config)、组合(recover_config)、提取HASH(hash)四种模式
触发条件：重生产，恢复生产，生产电子盘，刷写电子盘，刷盘，设备生产，刷写，自动化生产，produce device，recover device
---

# NF防火墙自动化生产

基于 `device_automation.py`，通过 Telnet 连接设备执行恢复生产、配置管理口IP、提取HASH。

## 参数

| 参数 | 必填 | 说明 | 默认值 |
|------|------|------|--------|
| tel_ip | 是 | Telnet串口服务器IP | |
| tel_port | 是 | Telnet端口 | |
| mgt_ip | 是 | 设备管理口IP | |
| mgt_mask | 是 | 子网掩码 | |
| mgt_gw | 是 | 默认网关 | |
| server | 否 | 文件服务器IP | 10.44.11.237 |
| image | 是 | 电子盘镜像名 | |
| mode | 是 | 操作模式 | recover |

> hash模式仅需 tel_ip、tel_port，其他参数不需填。

## 模式

| 模式 | 说明 |
|------|------|
| recover | 刷写电子盘镜像，重启设备 |
| config | 配置管理口静态IP |
| recover_config | 先刷盘再配置IP（默认） |
| hash | 提取设备Product ID |

## 执行

```bash
python device_automation.py \
  --tel-ip 10.66.23.118 --tel-port 32769 \
  --mgt-ip 10.66.23.120 --mgt-mask 255.255.255.0 --mgt-gw 10.66.23.254 \
  --server 10.44.11.237 --image "NF606F03_fixpass_x86_7f29aa22_20260518223341" \
  --mode recover_config

# hash模式
python device_automation.py --tel-ip 10.66.23.118 --tel-port 32769 --mode hash
```

触发后检查必填参数，缺失时通过 AskUserQuestion 询问。
