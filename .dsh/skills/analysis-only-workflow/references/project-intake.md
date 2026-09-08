# 快速熟悉代码库（lite 版）

> bug-fix-workflow `references/project-intake.md` 的精简版。本 skill 默认任务是"无 bug 单的轻量分析"，熟悉时间应控制在单轮内，不展开完整项目画像。

## 1. 5 分钟熟悉路径

1. **确认代码边界**：仓库根、分支、HEAD commit、最后修改时间。
2. **定位目标模块**：grep 关键符号 / 函数名 / 文件名 / 报错关键字。
3. **建立模块目录结构印象**：`ls` + `tree -L 2`（如已安装）。
4. **找入口 / 配置文件**：`README`、`Makefile`、`CMakeLists.txt`、主入口文件。
5. **如仓库根有 `.codegraph/`**：优先 `codegraph explore <符号>` 替代 grep/读文件。

## 2. 立项检查

- [ ] 仓库根确定
- [ ] 目标模块定位完成
- [ ] 调用入口 / 配置文件识别完成
- [ ] 不熟悉依赖（Makefile / CMake / 包管理）已扫描
- [ ] 不展开到无关模块

## 3. 不做的事

- 不读完整个项目 README
- 不通读所有源码文件
- 不展开历史 commit
- 不下载附件、开浏览器
- 不创建 worktree（除非用户明确需要隔离编码环境）