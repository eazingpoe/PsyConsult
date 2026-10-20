# GitHub 发布前检查清单

## 重要

这个包包含当前项目中符合打包规则的源码、配置、测试和文档，包括 Git 尚未跟踪的源文件。它不包含 `.git` 历史；这有助于避免误上传历史提交中曾经出现的密钥，但不能替代密钥审计。

## 发布前请检查

1. 检查 `PsyConsult_功能报告.md`，确认描述与当前代码一致。
2. 检查 `.env.example` 中只有占位符，不包含真实密钥。
3. 检查知识库和 `PsyConsult-community-kb-v1` 下的文档/报告是否允许再分发。
4. 检查是否有真实患者资料、上传文件、录音、日志或本地数据库。
5. 在打包目录中重新执行测试；本打包脚本不会执行测试。
6. 第一次建议创建 Private 仓库，完成审查后再决定是否公开。

## GitHub 上传命令

将 ZIP 解压后进入解压目录：

```bash
git init
git branch -M main
git add .
git status --short
git diff --cached --check
```

仔细检查 `git status --short`，确认没有密钥、真实患者信息或未授权资料，再执行：

```bash
git commit -m "Initial commit: PsyConsult"
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPOSITORY>.git
git push -u origin main
```

将 `<YOUR_USERNAME>` 和 `<YOUR_REPOSITORY>` 替换为实际 GitHub 用户名和仓库名。若已创建仓库并配置远程地址，不要重复执行 `git remote add origin`。
