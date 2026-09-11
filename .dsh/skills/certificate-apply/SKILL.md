---
name: certificate-apply
description: '绿盟科技内部支持系统的证书申请全流程自动化。包括设备查询、证书申请、证书下载。当用户提到"申请证书"、"制作证书"、"获取证书"、"证书下载"、"NF证书"、"设备证书"、"license申请"等涉及绿盟科技证书系统操作时，必须使用此技能。适用于10.42.42.76内网证书系统。'
scene: develop
user-invocable: true
---

   # 绿盟科技证书申请流程

   证书申请全流程已封装为自动化脚本 `certificate-apply.py`，优先使用脚本。

   ## 前提

   - 需要用户提供：**用户名**、**PIN码**（固定部分）、**HASH**、**UIP**（一次性口令）
   - 内网可达 10.42.42.76
   - 默认参数：NF产品、vNF 6.0.5、2核、功能模块 fw qos ddos ipsecvpn appid sdwan

   ## 用户需提供的信息

   向用户确认以下参数：

   | 参数          | 必填 | 说明                   |
   | ------------- | ---- | ---------------------- |
   | 用户名        | 是   | 登录账户名             |
   | PIN码         | 是   | 固定密码部分           |
   | HASH / 序列号 | 是   | 设备唯一标识           |
   | UIP           | 是   | 一次性口令             |
   | 版本          | 否   | 默认 6.0.6，可选 6.0.5 |
   | 显示产品      | 否   | 默认 vnf，可选 nf / sg |

   ## 自动化脚本（首选）

   ```bash
   # 默认配置（vNF 6.0.6）
   python certificate-apply.py <用户名> <PIN码> <HASH> <UIP>
   
   # 指定版本和显示产品
   python certificate-apply.py <用户名> <PIN码> <HASH> <UIP> --version 6.0.6 --dev nf
   ```

   脚本自动完成：登录 → 查询设备 → 阶段A(apply) → 阶段B(insertNf) → 下载证书到 `<workspace_root>/.dsh/env_config/certificate-apply/` 目录（`workspace_root` 由 `certificate-apply.py` 顶部的 `_resolve_workspace_root()` 解析：`AGENT_ASSETS_DIR` 环境变量 → git 根 → cwd 兜底）。

   ## 手动流程（脚本异常时回退）

   当脚本因编码异常或系统变更无法工作时，按以下步骤手动执行。

   ### 日期计算
   ```bash
   START_DATE=$(date +%Y-%m-%d)
   END_DATE=$(date -d "@$(($(date +%s) + 365*86400))" +%Y-%m-%d)
   ```

   ### 登录
   ```bash
   curl -s -c cookies.txt -b cookies.txt http://10.42.42.76/user/requireLogin -o /dev/null
   curl -s -c cookies.txt -b cookies.txt -X POST http://10.42.42.76/user/login \
     --data-urlencode "user[account]=<用户名>" \
     --data-urlencode "user[password]=<PIN码+UIP>" \
     -L | grep "window.top.location"
   ```

   ### 查询设备
   ```bash
   # AJAX 查询
   curl -s -b cookies.txt \
     'http://10.42.42.76/device/indexContent?search%5BcustomerId%5D=-1&search%5Bhash%5D=<HASH>&search%5Bserial%5D=<HASH>'
   ```
   提取客户短名称（格式 `全称(-短名称)`）用于阶段A。

   ### 阶段A：apply
   ```bash
   # AJAX 设置 session
   curl -s -b cookies.txt -c cookies.txt \
     "http://10.42.42.76/licenseApply/response?field=all&show=true&serial=<HASH>&applyer=<用户名>&itemName=<用户名>&pactName=<用户名>&customer=<短名称>&agentName=&projectNumber="
   
   # 提交申请
   curl -s -b cookies.txt -c cookies.txt -X POST http://10.42.42.76/licenseApply/apply \
     --data-urlencode "license[holidayTime]=1" --data-urlencode "license[extend]=1" \
     --data-urlencode "license[applyer]=<用户名>" --data-urlencode "license[applyDate]=${START_DATE}" \
     --data-urlencode "license[agentName]=" --data-urlencode "license[itemName]=<用户名>" \
     --data-urlencode "license[pactName]=<用户名>" --data-urlencode "license[folio]=<用户名>" \
     --data-urlencode "license[projectNumber]=" -d "license[productLineId]=1" -d "license[product]=51" \
     --data-urlencode "license[customer]=<短名称>" --data-urlencode "license[serial]=<HASH>" \
     --data-urlencode "license[mail]=" --data-urlencode "license[mark]="
   ```

   ### 阶段B：insertNf（预编码body）
   ```python
   # 用 Python 预编码中文全称
   python -c "import urllib.parse; print(urllib.parse.quote('<客户中文全称>'))"
   ```
   构造包含 `version`（6=6.0.5, 7=6.0.6）和 `display_model`（vnf/nf/sg）的预编码 body 提交。

   ### 下载证书
   ```bash
   curl -s -b cookies.txt "http://10.42.42.76/licenseViewer/downloads/id/<证书编号>" \
     -o "<workspace_root>/.dsh/env_config/certificate-apply/<证书文件名>"
   ```

   ## 关键注意事项

   1. **编码**：阶段A用短名称(`--data-urlencode`)，阶段B用中文全称预编码(`-d`)—数据库 utf8mb3/utf8mb4 collation 冲突
   2. **两阶段顺序**：先 AJAX 设置 session → apply → insertNf，缺一不可
   3. **Cookie 管理**：始终 `-c cookies.txt -b cookies.txt` 成对使用
   4. **日期不硬编码**：所有截止日期用 `$END_DATE`
   5. **设备存在性**：先查是否已存在，避免重复添加
   6. **版本**：6.0.5=6, 6.0.6=7（表单中 version 字段的值）
   7. **显示产品**：vnf/nf/sg（表单中 display_model radio 的值）
