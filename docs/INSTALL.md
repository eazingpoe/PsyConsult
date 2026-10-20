# 安装与运行说明

本文档面向本地开发与演示环境。不同提交的依赖和配置可能有差异；以当前工作区中的配置文件和实际启动日志为准。

## 1. 系统要求

- Linux（本文命令以 Ubuntu 为例）
- Python 3.12（项目当前开发环境使用 Python 3.12）
- Conda（可选，但项目开发环境使用 `psyconsult`）
- Node.js 与 npm
- Docker Compose（如果要使用仓库提供的 Redis/其他基础服务）
- 模型服务/API 凭据
- 如需扫描版 PDF 或图片 OCR：Tesseract OCR 与中文语言包

## 2. 获取代码

```bash
git clone https://github.com/<OWNER>/PsyConsult.git
cd PsyConsult
```

将 `<OWNER>` 替换为你实际的 GitHub 用户名。请确认 clone 的分支包含患者档案、录音转写和报告分析功能。

## 3. Python 环境与依赖

若已有开发环境：

```bash
conda activate psyconsult
cd /path/to/PsyConsult
python --version
python -m pip install -r agent/requirements.txt
```

若尚未创建环境：

```bash
conda create -n psyconsult python=3.12 -y
conda activate psyconsult
cd /path/to/PsyConsult
python -m pip install --upgrade pip
python -m pip install -r agent/requirements.txt
```

如果依赖被拆分在其他 requirements 文件中，请根据当前分支中的文件补装。不要在未检查项目依赖的情况下盲目安装同名但不同用途的包。

## 4. 配置模型服务与环境变量

1. 检查 `app/app_config/settings.py`、`agent/config/`、`agent/requirements.txt` 和现有 `.env.example`（如果存在）。
2. 确认当前版本所需的模型服务、API Key、认证 Token、Redis 和向量检索配置。
3. 将真实凭据保存在本机环境变量或本地 `.env` 文件中，文件位置应与当前代码的配置读取逻辑一致。
4. `.env` 不得提交到 Git；公开示例只保留变量名和无效占位值。

检查仓库中可能存在的示例配置：

```bash
find . -maxdepth 4 \
  \( -name ".env.example" -o -name "*.env.example" -o -name "docker-compose.yml" -o -name "compose.yaml" \) \
  -print
```

如果使用本地代理，确保 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 的 URL scheme 与客户端支持的协议一致。若启动时报 `Unknown scheme for proxy URL`，先检查代理变量配置；不要把代理密码或 Token 粘贴到日志或公开文档。

## 5. 启动基础服务（如需要）

先检查仓库是否包含 Compose 文件：

```bash
find docker -maxdepth 2 \
  \( -name "docker-compose.yml" -o -name "compose.yaml" \) \
  -print 2>/dev/null
```

如果存在 `docker/docker-compose.yml`：

```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml ps
```

若 Compose 文件位置不同，请替换成实际路径。后端启动日志显示 Redis 或向量数据库不可用时，先检查相应服务、端口和连接配置。不要因为某个服务未启动就直接删除数据库卷。

## 6. 启动后端 API

在项目根目录执行：

```bash
conda activate psyconsult
cd /path/to/PsyConsult

python -m uvicorn app.app_main:app \
  --app-dir "$PWD" \
  --host 127.0.0.1 \
  --port 5000
```

启动成功后检查：

- `http://127.0.0.1:5000/openapi.json`
- `http://127.0.0.1:5000/docs`

若出现 `Address already in use`，先查看端口占用：

```bash
sudo lsof -i :5000
```

确认占用进程属于本项目后，再决定是否停止旧进程；不要直接终止不认识的进程。

## 7. 启动前端

打开另一个终端：

```bash
cd /path/to/PsyConsult/front/clinical_cds
npm install
npm run dev
```

使用 Vite 输出的实际地址打开浏览器，通常为 `http://127.0.0.1:5173`。如果前端无法请求后端，检查 `front/clinical_cds/vite.config.ts` 的 API 代理和后端监听地址。

## 8. OCR 依赖（可选）

如果系统需要处理扫描版 PDF 或图片，请检查：

```bash
which tesseract
tesseract --list-langs
```

Ubuntu 上可按需安装中文语言包：

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-chi-sim
```

Python 端通常使用 `pytesseract`、Pillow、PyMuPDF（`fitz` 模块）和 PDF 文本提取依赖。具体依赖请以 `agent/requirements.txt` 与报告分析服务代码为准。

## 9. 运行自动化测试

在项目根目录：

```bash
conda activate psyconsult
python -m pytest -q app/test agent/test
```

前端类型检查与生产构建：

```bash
cd front/clinical_cds
npm run build
```

记录当前提交实际测试结果；不要把旧提交的测试通过记录写成当前版本的保证。

## 10. 生成系统截图（可选）

截图应使用虚构测试数据。安装 Playwright：

```bash
python -m pip install playwright
python -m playwright install chromium
```

在项目根目录执行：

```bash
python tools/capture_screenshots.py --url http://127.0.0.1:5173
```

截图脚本会打开一个受控浏览器。按终端提示依次切换到聊天、自评、患者档案、报告分析和录音页面，再按回车截图。可输入 `skip` 跳过某一页。图片保存在 `docs/screenshots/`。

## 11. 公开发布前检查

```bash
python tools/audit_public_release.py
```

此外建议运行 Gitleaks 扫描当前文件和 Git 历史。该工具的扫描结果不能证明绝对安全；任何真实凭据一旦提交，都应先撤销或轮换。详细步骤见 `docs/SECURITY_REVIEW.md`。
