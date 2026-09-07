---
name: nf-config-procedures
description: "绿盟NF防火墙配置流程库 - 接口、路由、安全策略等操作手册及避坑指南"
user-invocable: true
origin: manual-curated
---

# 绿盟NF防火墙配置流程库

**维护方式：** 每次通过 LightRAG 查询 + 浏览器自动化完成新配置后，
将流程追加到对应章节。

**知识来源：** LightRAG (http://lightrag.boombox.local)
**设备地址：** 10.66.23.115:1443

---

## 通用登录流程

```bash
# 方案 A：fill 优先
playwright-cli attach --extension=chrome
playwright-cli --s=chrome --timeout=10000 fill <用户名ref> "webpolicy"
playwright-cli --s=chrome --timeout=10000 fill <密码ref> "密码"
playwright-cli --s=chrome --timeout=10000 click <登录按钮ref>

# 方案 B：fill 失败时回落到 click+type
playwright-cli attach --extension=chrome
playwright-cli --s=chrome --timeout=10000 click <用户名ref>
playwright-cli --s=chrome --timeout=10000 type "webpolicy"
playwright-cli --s=chrome --timeout=10000 click <密码ref>
playwright-cli --s=chrome --timeout=10000 type "密码"
playwright-cli --s=chrome --timeout=10000 click <登录按钮ref>
```

确认 URL 跳转到 `#/layout/...` 表示登录成功。

> **通用 playwright-cli 技巧**（输入框填写、下拉框、脚本文件等）参见
> `playwright-cli-patterns` skill。

---

## NF Web UI 操作注意事项

### A. 配置前必须查询 LightRAG

使用 playwright-cli 配置 NF 防火墙前，**必须先用 lightrag skill 查询配置步骤**：

```bash
# 查询配置步骤
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://lightrag.boombox.local query -q "绿盟防火墙[功能名称]配置步骤"

# 查询 REST API 接口（如需 API 配置）
npx tsx "$SKILL_DIR/lightrag-cli.ts" --url http://lightrag.boombox.local query -q "绿盟防火墙REST API[功能名称]接口"
```

**原因：** 知识库已收录《绿盟NF防火墙V6.0R06F02操作手册》，直接查询比重新研究更高效

**流程：** `lightrag 查询配置步骤` → `playwright-cli 执行配置`

### B. 按钮状态逻辑（重要）

按钮显示的是**点击后将执行的操作**，不是当前状态：

| 按钮显示 | 当前状态 | 点击后状态 |
|---------|---------|-----------|
| **启用** | 禁用 | 启用 |
| **禁用** | 启用 | 禁用 |

**正确理解：** 按钮文本 = 即将执行的动作，不是当前状态

### C. 对象选择逻辑（服务/应用）

默认状态：服务和应用都选中 `any`

| 场景 | 服务选择 | 应用选择 |
|------|---------|---------|
| 需要特定服务 | 反选 any → 正选目标服务 | 保持 any |
| 需要特定应用 | 保持 any | 反选 any → 正选目标应用 |
| 需要特定服务+应用 | 反选 any → 正选目标服务 | 反选 any → 正选目标应用 |

**操作步骤：**
1. 点击【选择对象】打开选择对话框
2. 搜索目标对象（如 ICMP）
3. **反选 any** - 取消勾选 `any` 的复选框
4. **正选目标对象** - 勾选需要的对象
5. 点击【确定】确认

**关键点：** 不能直接选择目标对象而不取消 any，否则可能冲突

```bash
# 1. 点击选择对象按钮
playwright-cli --s=chrome click <选择对象按钮ref>

# 2. 搜索目标服务
playwright-cli --s=chrome fill <搜索框ref> "icmp"
playwright-cli --s=chrome click <搜索按钮ref>

# 3. 反选 any（必须！）
playwright-cli --s=chrome click <any复选框ref>

# 4. 正选目标服务
playwright-cli --s=chrome click <icmp复选框ref>

# 5. 确认选择
playwright-cli --s=chrome click <确定按钮ref>
```

### D. 菜单导航（禁止 goto）

NF Web UI 是 Angular SPA，`goto` 直接跳转会丢失登录会话。

❌ **错误**：`await page.goto('https://.../#/layout/network-manage/static-routing')` → 跳转到登录页

✅ **正确**：通过菜单导航，子菜单用 `force: true`：
```bash
playwright-cli --s=chrome run-code "async page => {
  await page.locator('li.ant-menu-submenu:has-text(\"路由\")').click({ force: true });
  await page.waitForTimeout(1000);
  await page.locator('li.ant-menu-item:has-text(\"静态路由\")').click({ force: true });
  await page.waitForTimeout(2000);
}"
```

### E. 多选下拉框焦点陷阱

Ant Design 多选下拉框（接口选择、对象选择等）选择后焦点不释放，
后续操作会被 overlay 拦截。**选完后必须点击其他元素移开焦点**：

```bash
# 选完源接口后，点击单出口单选按钮移开焦点
playwright-cli --s=chrome run-code "async page => {
  await page.locator('label').filter({ hasText: '单出口' }).click({ force: true });
  await page.waitForTimeout(1000);
}"
# 之后才能安全操作目的接口下拉框
```

移开焦点的替代方法：点击附近单选按钮、点击文本输入框、按 Escape 键。

---

## 流程：配置三层接口

**触发：** 需要为物理接口分配 IP 地址、加入安全区

**LightRAG 查询：**
  query -q "绿盟NF防火墙如何配置三层接口IP地址 G1/3" --mode mix

**Web UI 步骤：**
  1. 导航：网络管理 > 接口
  2. 找到目标接口行 → 点击 "编辑"（文本链接，非按钮）
  3. 接口类型下拉框 → 点击箭头 img → snapshot → 选 "三层"
  4. 安全区下拉框 → 默认 TRUST（可改）
  5. 管理属性 → 默认 default
  6. IPv4 配置方式 → 静态配置（默认选中）
  7. IPv4 地址 → 清空默认值 "0.0.0.0/0" → 输入 "X.X.X.X/掩码"
  8. 点击 "确定"

**本次配置结果：**
  G1/3 | TRUST | 三层 | 30.0.0.1/24 | 静态配置

---

## 流程：配置三层接口（含MTU）

**触发：** 需要为物理接口分配 IP 地址、设置 MTU

**Web UI 步骤：**
  1. 导航：网络管理 > 接口
  2. 找到目标接口行 → 点击 "编辑"（文本链接，非按钮）
  3. 接口类型下拉框 → 点击箭头 img → snapshot → 选 "三层"
  4. 安全区下拉框 → 默认 TRUST（可改）
  5. 管理属性 → 默认 default
  6. IPv4 配置方式 → 静态配置（默认选中）
  7. IPv4 地址 → 清空默认值 "0.0.0.0/0" → 输入 "X.X.X.X/掩码"
  8. 高级参数 → 展开
  9. IPv4 MTU → 清空默认值 "1500" → 输入新值
  10. IPv6 MTU → 清空默认值 "1500" → 输入新值
  11. 点击 "确定"

**本次配置结果：**
  G1/4 | TRUST | 三层 | 40.0.0.1/24 | 静态配置 | IPv4 MTU: 1000 | IPv6 MTU: 1280

---

## 流程：配置接口 IP 地址

**触发：** 需要为单个物理接口分配 IP 地址（playwright-cli 操作版）

**Web UI 步骤：**
  1. 导航：网络管理 > 接口
  2. 找到目标接口行 → 使用行选择器点击"编辑"
  3. 接口类型下拉框 → 点击箭头 img → snapshot → 选"三层"
  4. IPv4 地址 → fill 或 click+type 输入 "X.X.X.X/掩码"
  5. 点击"确定"

**playwright-cli 操作：**
```bash
# 1. 点击目标接口的编辑按钮（使用行选择器）
playwright-cli --s=chrome --timeout=10000 run-code "async page => { await page.locator('tr:has-text(\"G1/5\")').getByText('编辑').click(); }"

# 2. 获取快照，找到接口类型下拉框
playwright-cli --s=chrome --timeout=10000 snapshot

# 3. 如果接口未配置，先选择接口类型
playwright-cli --s=chrome --timeout=10000 click <下拉框ref>
playwright-cli --s=chrome --timeout=10000 snapshot  # 二次快照获取选项
playwright-cli --s=chrome --timeout=10000 click <三层-option-ref>

# 4. 设置 IP 地址（格式：IP/CIDR）
playwright-cli --s=chrome --timeout=10000 fill <IPv4地址ref> "50.0.0.1/24"
# 若 fill 不生效，回落到 click+type：
# playwright-cli --s=chrome --timeout=10000 click <IPv4地址ref>
# playwright-cli --s=chrome --timeout=10000 type "50.0.0.1/24"

# 5. 确认保存
playwright-cli --s=chrome --timeout=10000 click <确定按钮ref>
```

**配置结果示例：**
  G1/5 | TRUST | 三层 | 50.0.0.1/24 | 静态配置

---

## 流程：批量配置多个接口

**触发：** 需要连续配置多个接口的 IP 地址

**playwright-cli 操作：**
```bash
# 配置 G1/5
playwright-cli --s=chrome --timeout=10000 run-code "async page => { await page.locator('tr:has-text(\"G1/5\")').getByText('编辑').click(); }"
playwright-cli --s=chrome --timeout=10000 snapshot
playwright-cli --s=chrome --timeout=10000 click <下拉框ref>
playwright-cli --s=chrome --timeout=10000 snapshot
playwright-cli --s=chrome --timeout=10000 click <三层-option-ref>
playwright-cli --s=chrome --timeout=10000 fill <IPv4地址ref> "50.0.0.1/24"
playwright-cli --s=chrome --timeout=10000 click <确定按钮ref>

# 配置 G1/6（重复相同流程）
playwright-cli --s=chrome --timeout=10000 run-code "async page => { await page.locator('tr:has-text(\"G1/6\")').getByText('编辑').click(); }"
# ... 后续步骤相同
```

**提示：** 大量重复操作建议写成 script.js 批量执行（参见 playwright-cli-patterns skill）。

---

## 流程：配置策略路由

**触发：** 需要基于源/目的 IP、接口等条件进行策略路由转发

**Web UI 步骤：**
  1. 导航：网络管理 > 策略路由
  2. 点击"新建"
  3. 填写路由名称、源/目的 IP
  4. 选择源接口（多选）→ 移开焦点
  5. 选择目的接口
  6. 填写网关地址
  7. 点击"确定"→"应用配置"

**playwright-cli 操作：**
```bash
# 1. 导航到策略路由（子菜单需要 force: true）
playwright-cli --s=chrome click <网络管理-ref>
playwright-cli --s=chrome run-code "async page => {
  await page.locator('li.ant-menu-item:has-text(\"策略路由\")').click({ force: true });
  await page.waitForTimeout(2000);
}"

# 2. 点击新建按钮
playwright-cli --s=chrome click <新建按钮ref>

# 3. 填写路由名称
playwright-cli --s=chrome fill <路由名称ref> "PBR-G1G4"

# 4. 填写源IP地址（0.0.0.0/0表示所有流量）
playwright-cli --s=chrome fill <源IP地址ref> "0.0.0.0/0"

# 5. 填写目的IP地址
playwright-cli --s=chrome fill <目的IP地址ref> "0.0.0.0/0"

# 6. 选择源接口（多选）— 参见"多选下拉框焦点陷阱"
playwright-cli --s=chrome run-code "async page => {
  await page.locator('nz-form-item').filter({ hasText: '源接口' }).locator('.ant-select').click();
  await page.waitForTimeout(1000);
}"
playwright-cli --s=chrome click <G1/1-ref>
playwright-cli --s=chrome click <G1/2-ref>
playwright-cli --s=chrome click <G1/3-ref>

# 7. 关键：移开焦点（点击单出口单选按钮）
playwright-cli --s=chrome run-code "async page => {
  await page.locator('label').filter({ hasText: '单出口' }).click({ force: true });
  await page.waitForTimeout(1000);
}"

# 8. 选择目的接口
playwright-cli --s=chrome run-code "async page => {
  await page.locator('nz-form-item').filter({ hasText: '目的接口' }).locator('.ant-select').click({ force: true });
  await page.waitForTimeout(1000);
}"
playwright-cli --s=chrome click <G1/4-ref>

# 9. 填写网关地址
playwright-cli --s=chrome fill <网关地址ref> "40.0.0.2"

# 10. 点击确定保存
playwright-cli --s=chrome click <确定按钮ref>

# 11. 应用配置
playwright-cli --s=chrome click <应用配置按钮ref>
```

**策略路由配置参数说明：**

| 参数 | 说明 | 示例值 |
|------|------|--------|
| 路由名称 | 策略路由的唯一标识 | PBR-G1G4 |
| 状态 | 启用/禁用 | 启用 |
| 源IP地址 | 匹配的源IP网段 | 0.0.0.0/0（所有） |
| 目的IP地址 | 匹配的目的IP网段 | 0.0.0.0/0（所有） |
| 源接口 | 流量进入的接口（多选） | G1/1, G1/2, G1/3 |
| 目的接口 | 流量转发出去的接口 | G1/4 |
| 网关地址 | 下一跳网关IP | 40.0.0.2 |
| 管理距离 | 路由优先级（越小越优先） | 1 |
| 权值 | 负载均衡权重 | 1 |

---

## 流程：配置静态路由
（待补充）

## 流程：配置安全策略
（待补充）

## 流程：配置NAT
（待补充）

---

## 问题排查：playwright-cli 命令卡死

**现象：** `click`、`fill`、`run-code` 等命令挂起不返回

**根本原因：**
  playwright-cli 会话中存在卡住的后台命令，阻塞了后续所有命令的执行队列。
  一旦某个命令因页面 Angular Zone.js 稳定性检查（持续轮询/定时器）而超时，
  后续命令都会排队等待，表现为"卡死"。

**解决方案：**
  1. `playwright-cli detach` — 断开当前会话（会清除所有排队命令）
  2. `playwright-cli attach --extension=chrome` — 重新附加到浏览器
  3. 之后的命令即可正常执行

**注意事项：**
  - 避免在主页面（有实时时钟/轮询的 Angular 应用）上使用 `click` 命令
  - 优先使用 `run-code` + `page.evaluate()` 来点击元素（绕过 actionability 检查）
  - 使用 `type` / `press` 命令代替 `fill` 命令输入文本

---

## 问题排查：多选下拉框焦点残留

**现象：** 选择多选下拉框（如源接口）后，后续操作其他下拉框或表单元素时
实际操作的仍是之前的下拉框，或出现 `intercepts pointer events` 错误。

**根本原因：**
  Ant Design 的 `nz-select` 多选模式在选择选项后，overlay 仍然打开，
  焦点停留在下拉框上。cdk-overlay-backdrop 会拦截所有点击事件。

**解决方案：** 选择完多选下拉框后，**必须点击其他表单元素移开焦点**。

| 方法 | 适用场景 |
|------|----------|
| 点击附近单选按钮 | 如"单出口"/"多出口" |
| 点击文本输入框 | 如路由名称、IP 地址输入框 |
| 按 Escape 键 | 通用方法，关闭 overlay |
| 点击页面空白处 | `await page.mouse.click(0, 0)` |

**关键：** 不能跳过移开焦点这一步直接操作下一个下拉框。

---

## 问题排查：菜单导航被拦截

**现象：** 点击左侧菜单子项时报 `intercepts pointer events` 错误

**根本原因：** 父菜单的展开区域遮挡了子菜单项

**解决方案：** 使用 `force: true` 强制点击：
```bash
playwright-cli --s=chrome run-code "async page => {
  await page.locator('li.ant-menu-item:has-text(\"子菜单名\")').click({ force: true });
  await page.waitForTimeout(2000);
}"
```

---

## 问题排查：goto 跳转丢失登录

**现象：** 使用 `page.goto()` 直接导航到功能页面后，页面跳转到登录页

**根本原因：** NF Web UI 是 Angular SPA，路由状态存在内存中，
`goto` 会重新加载页面，导致 SPA 状态丢失，触发登录重定向。

**解决方案：** 禁止使用 `goto`，必须通过左侧菜单导航（参见"D. 菜单导航"）。
