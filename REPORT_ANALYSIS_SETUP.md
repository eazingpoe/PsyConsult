# PsyConsult 心理测评报告分析增量补丁

## 功能
- 沿用患者档案报告管理，增加 PNG/JPG/JPEG，保留 PDF/DOCX。
- 提取 PDF/DOCX 文本；扫描版 PDF 和图片尝试中文 OCR。
- 使用现有 `agent.config.settings.get_settings().get_model_config()` 调用模型。
- 将每次分析和提取文本保存到 SQLite 独立的 `report_analyses` 表。
- 在报告列表增加“分析”“历史”，并增加分析结果查看。
- 不替换现有问答、自评、SSE、录音、安全支持或患者档案数据表。

## 应用补丁
```bash
conda activate psyconsult
cd ~/Downloads/PsyConsult-codex-hardening-baseline
python ~/Downloads/psyconsult_report_analysis_patch.py --project-root "$PWD" --dry-run
python ~/Downloads/psyconsult_report_analysis_patch.py --project-root "$PWD"
```

## 安装依赖
```bash
conda activate psyconsult
cd ~/Downloads/PsyConsult-codex-hardening-baseline
python -m pip install "pypdf>=5.0" "PyMuPDF>=1.24" "Pillow>=10.0" "pytesseract>=0.3.13" "python-docx>=1.1"
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
```

若未安装 OCR，文本型 PDF 和 DOCX 仍可尝试分析；扫描件和图片会返回明确错误，不会假装已提取成功。

## 验证
```bash
python -m pytest -q app/test agent/test
cd front/clinical_cds && npm run build
```

## 新增接口
- `POST /api/patients/{patient_id}/reports/{report_id}/analyze`
- `GET /api/patients/{patient_id}/reports/{report_id}/analyses`
- `GET /api/patients/{patient_id}/reports/{report_id}/analyses/{analysis_id}`

## 安全边界
这是研究/演示原型，不应直接用于真实患者临床决策。模型输出不是临床诊断，OCR 结果必须人工核对。正式部署前还需落实可靠身份认证、授权、加密、访问审计、备份及数据保留策略。
