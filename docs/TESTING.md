# 测试与 GitHub 发布检查

## 1. 后端回归测试

在项目根目录执行：

```bash
conda activate psyconsult
python -m pytest -q app/test agent/test
```

## 2. 前端构建

```bash
cd front/clinical_cds
npm install
npm run build
```

## 3. API 检查

启动后端后：

```bash
curl -fsS http://127.0.0.1:5000/openapi.json -o /tmp/psyconsult-openapi.json
python - <<'PY'
import json
with open("/tmp/psyconsult-openapi.json", encoding="utf-8") as f:
    data = json.load(f)
print("API paths:", len(data.get("paths", {})))
for path in sorted(data.get("paths", {})):
    if "patients" in path or "report-analysis" in path or "transcribe" in path:
        print(path, sorted(data["paths"][path]))
PY
```

## 4. 手工回归清单

- [ ] 普通问答能返回完整正文。
- [ ] SSE 分块时正文顺序正确，结束事件正常。
- [ ] 高风险表达触发安全分流。
- [ ] PHQ-9 / GAD-7 正常计分，错误答案数量被拒绝。
- [ ] PHQ-9 第九题非零时显示安全提示。
- [ ] 创建、更新、查看和删除测试患者档案。
- [ ] 测评结果可保存并在档案中查看。
- [ ] 录音转写可用。
- [ ] PDF 文本报告上传、提取和分析成功。
- [ ] 扫描 PDF / 图片 OCR 结果经人工核对。
- [ ] 报告可归档至测试患者，报告和分析历史可查询。
- [ ] 错误请求有可理解的错误提示。
- [ ] 测试数据、上传文件和日志中不含真实个人信息。

## 5. 开发期间记录的历史结果

下列结果来自开发过程中曾提供的终端输出，不是 GitHub Actions 的自动化结果，也不能保证当前提交仍然完全一致：

- 后端回归：82 passed，1 条弃用警告。
- 端到端 API 冒烟测试：12/12 项通过。
- 安全边界测试：8/8 项通过。
- 报告分析相关的 `app/test`：曾显示 29 passed。
- 前端 `npm run build`：曾成功，但出现第三方注释和 bundle 大小警告。

建议在当前仓库重新执行以上测试后，再将测试状态写入发布说明。

## 6. GitHub 发布前安全检查

- [ ] `git status --short` 确认没有意外文件。
- [ ] 不提交 `.env`、Token、API Key、私钥或密码。
- [ ] 检查 Git 历史；如果密钥曾提交，删除文件不够，需要撤销或轮换密钥。
- [ ] 不提交真实患者资料、录音、报告、数据库、日志和上传目录。
- [ ] 确认知识库、第三方文档及数据集允许再分发。
- [ ] 增加 `.env.example`，仅填写变量名和无效占位符。
- [ ] 明确选择开源许可证；未确认授权前不要默认添加许可证。
- [ ] 使用私有仓库完成安全审查后，再决定是否公开。
