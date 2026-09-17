# `.dsh/rules/` 规则目录说明

> 本目录存放 DSH 工作区的**约束规则**。由 `@nsfocus/nf-system-prompt` 插件在
> DSH 启动时扫描注入系统提示词（插件源码见 `packages/nf-system-prompt/src/index.ts`）。

## 自动注入机制

- 目录：`.dsh/rules/*.md`（相对工作区根）。
- **带 YAML frontmatter 的 md 才会被注入系统提示词**；无 frontmatter 的文件
  （如 `process-files.md` 这类"完整版参考文档"）默认跳过，不与插件内硬编码摘要重复。
- 扫描在 `dsh web` 启动时执行一次。**新增 / 修改规则后需重启 `dsh web` 生效**。

## frontmatter 字段约定

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `order` | ✅ | number | section 排序位（同一 order 空间与硬编码 section 并存）。越小越靠前。 |
| `name` | ❌ | string | section 名，仅小写字母/数字/连字符。缺省按文件名派生。 |
| `enabled` | ❌ | boolean | `false` 时跳过本文件。缺省 `true`。 |

- 正文 = frontmatter 之后的所有内容，原样注入（建议以 `## 标题` 开头）。
- 缺 `order`、`enabled: false`、正文为空 → 该文件跳过不注入（各自有日志提示）。

## 模板

````markdown
---
order: -30
name: my-rule
---
## 我的规则

规则正文……
````

## 新增一条规则的操作步骤

1. 新建 `.dsh/rules/<nn>-<slug>.md`，按上表写 frontmatter + 正文。
2. 重启 `dsh web`（`packages/nf-system-prompt` 插件无需重编译——扫描逻辑读的是
   目录文件，不是编译进插件的内容）。
3. 日志出现 `[nf-system-prompt] 已注入规则文件 …`，即注入成功；
   新会话的提示词会带上该规则。

> 注意：若 `packages/nf-system-prompt` 插件**本体逻辑**有改动（非规则文件），
> 才需要 `cd packages/nf-system-prompt && pnpm exec tsc` 重新编译后重启。

## 现有文件

| 文件 | frontmatter | 说明 |
|---|---|---|
| `knowledge-sedimentation.md` | `order: 40` | 知识沉淀去毒门禁（去毒四问 / 四类分区 / frontmatter 规范 / link_check 提交门禁） |
| `review-deliverable-gate.md` | `order: 45` | 文档审阅交付物门禁（引文逐字命中 / 否定性断言前做渲染态核对） |
| `process-files.md` | 无 | 过程文件归属规则**完整版**（提示词注入的是插件内的摘要，本文件不重复注入） |
| `dirs.json` | — | 沙箱可访问目录登记（非提示词规则，由 `nf-hooks` 读取） |

> 排查提示：缺 `order` / `order` 非数值 / 正文为空 / `enabled: false` 的规则文件会被**静默跳过**，
> 只在启动日志里打一行 `[nf-system-prompt] 跳过 …`。新增规则后请确认日志出现
> `已注入规则文件 <文件名> → section … (order …)`。
