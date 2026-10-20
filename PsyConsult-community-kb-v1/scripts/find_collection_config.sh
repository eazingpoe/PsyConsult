#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"
TARGET="${1:-community_mental_health_docs_v1}"
echo "项目根目录：$ROOT"
echo "查找旧集合名和新集合名配置；本脚本只读，不会修改文件。"
grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude='*.pyc' \
  -E 'cloud_product_docs|community_mental_health_docs_v1|collection_name' \
  "$ROOT/agent" "$ROOT/app" 2>/dev/null || true
echo
echo "目标集合建议：$TARGET"
echo "请确认查询端 embedding 模型与入库脚本完全一致，再修改运行配置。"
