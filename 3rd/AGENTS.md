# 目录的作用

当前目录是给AGENT动态增加的扩展能力，用于实现特定场景的特定功能。

## 扩展清单

- [nf_simple](nf_simple/index.md) — 绿盟NF防火墙REST API客户端。低上下文设计：模块/函数按需读取（`nf_index` 找模块 → `nf_read_file` 确认签名 → `nf_check_object` 检查依赖 → `nf_exec` 执行），调用前必须看签名，禁止凭记忆调用。




