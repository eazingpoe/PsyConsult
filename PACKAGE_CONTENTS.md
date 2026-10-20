# 打包内容说明

- 生成时间：20261020_203631
- 项目根目录：`/home/user/Downloads/PsyConsult-codex-hardening-baseline`
- 纳入文件：249
- 排除项目：35

## 排除项目

- `.git/` — runtime/cache/build directory
- `.pytest_cache/` — runtime/cache/build directory
- `data/` — runtime/cache/build directory
- `logs/` — runtime/cache/build directory
- `mock_data/` — mock_data excluded by default; use --include-mock-data only if verified synthetic
- `json` — unexpected root artifact named 'json'; review manually
- `PsyConsult-community-kb-v1/scripts/__pycache__/` — runtime/cache/build directory
- `agent/__pycache__/` — runtime/cache/build directory
- `agent/.env` — environment file may contain secrets
- `agent/.env.bak.20261020_131717` — environment file may contain secrets
- `agent/.env.bak.20261020_132012` — environment file may contain secrets
- `agent/.env.save` — environment file may contain secrets
- `agent/agents/__pycache__/` — runtime/cache/build directory
- `agent/config/__pycache__/` — runtime/cache/build directory
- `agent/core/__pycache__/` — runtime/cache/build directory
- `agent/core/graph/__pycache__/` — runtime/cache/build directory
- `agent/core/mcp/__pycache__/` — runtime/cache/build directory
- `agent/core/memory/__pycache__/` — runtime/cache/build directory
- `agent/core/workflow/__pycache__/` — runtime/cache/build directory
- `agent/core/workflow/safety.py.bak.20261020_144827` — backup file
- `agent/mcp_servers/__pycache__/` — runtime/cache/build directory
- `agent/test/__pycache__/` — runtime/cache/build directory
- `agent/tools/__pycache__/` — runtime/cache/build directory
- `app/__pycache__/` — runtime/cache/build directory
- `app/app_config/__pycache__/` — runtime/cache/build directory
- `app/infra/__pycache__/` — runtime/cache/build directory
- `app/router/__pycache__/` — runtime/cache/build directory
- `app/schemas/__pycache__/` — runtime/cache/build directory
- `app/service/__pycache__/` — runtime/cache/build directory
- `app/service/chat_service.py.bak.20261020_152147` — backup file
- `app/test/__pycache__/` — runtime/cache/build directory
- `front/clinical_cds/dist/` — runtime/cache/build directory
- `front/clinical_cds/node_modules/` — runtime/cache/build directory
- `front/clinical_cds/.env.local` — environment file may contain secrets
- `learn/part02-quickstart/environment.md` — high-confidence secret pattern: (?i)\bDASHSCOPE_API_KEY\s*[:=]\s*['\"]?[A-Za-z0-9_-]{24,}
