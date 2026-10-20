> 第二轮 v1.0.3：见 [优化报告](reports/round2/REPORT.md)。旧集与原始用例均保留；完整来源命中存在回归，默认服务未切换。评测命令现在必须传 `--output`。

# PsyConsult 社区心理健康知识库 v1（试运行包）

本包面向 PsyConsult 从临床决策支持场景转向“社区心理健康服务”的第一版知识库建设。包含公众版 Markdown 文档、来源登记表、Milvus 入库脚本、检索评测集和评测脚本。

## 重要状态说明

- 文档均为**带来源链接的内部测试草稿**，不是经过临床专家最终审核的正式医疗内容。入库脚本默认拒绝导入草稿；只有明确传入 `--allow-draft` 才允许建立试运行集合。
- 建议只在本地开发/演示环境使用试运行内容；正式向公众开放前，应由具备相应资质的临床/精神卫生专业人员审核，核对本地法规、版权许可和各地区资源信息。
- 本包没有复制 WHO 手册的完整正文；对 WHO 资料的引用和改写仍需遵循原始出版物的许可要求。WHO《Doing What Matters in Times of Stress》和 2026 年自助干预手册页面标注 CC BY-NC-SA 3.0 IGO，商业用途需另行确认许可。
- 药物模块只讲一般安全原则，不提供药物剂量、个体化选药、换药或停药方案。具体药品信息必须绑定现行批准说明书。
- 本包不访问或修改你的本地文件系统。你需要把本目录复制/解压到 PsyConsult 项目中，再在自己的 Linux 环境执行脚本。

## 目录

```text
knowledge_base/
  source_registry.csv
  community_mental_health/   # 12 篇公众版主题文档
  eval/retrieval_cases.jsonl # 检索黄金测试集
scripts/
  ingest_knowledge_base.py  # 安全的新集合入库脚本
  evaluate_retrieval.py     # Top-k 来源命中评测
  audit_knowledge_base.py   # 文档与来源元数据静态检查
```

## 在现有项目中使用

1. 将 `PsyConsult-community-kb-v1` 文件夹放到项目根目录：

   `~/Downloads/PsyConsult-codex-hardening-baseline/PsyConsult-community-kb-v1`

2. 激活已有环境并回到项目根目录：

   ```bash
   conda activate psyconsult
   cd ~/Downloads/PsyConsult-codex-hardening-baseline
   unset ALL_PROXY all_proxy
   ```

3. 先做静态检查，不会连接数据库或写入数据：

   ```bash
   python PsyConsult-community-kb-v1/scripts/audit_knowledge_base.py \
     --docs PsyConsult-community-kb-v1/knowledge_base/community_mental_health \
     --registry PsyConsult-community-kb-v1/knowledge_base/source_registry.csv
   ```

4. 检查当前环境是否能读取 `.env` / `agent/.env`，确认 `DASHSCOPE_API_KEY`、`MILVUS_HOST`、`MILVUS_PORT` 或 `MILVUS_URI`。脚本默认目标集合为 `community_mental_health_docs_v1`，不会删除或覆盖已有集合。

5. 首次建立**内部试运行集合**：

   ```bash
   python PsyConsult-community-kb-v1/scripts/ingest_knowledge_base.py \
     --docs PsyConsult-community-kb-v1/knowledge_base/community_mental_health \
     --collection community_mental_health_docs_v1 \
     --allow-draft
   ```

   如果集合已经存在，脚本会停止而不是清空/覆盖。需要重建时，请使用新版本集合名（例如 `community_mental_health_docs_v2`），完成评测后再切换应用配置。

6. 运行检索评测：

   ```bash
   python PsyConsult-community-kb-v1/scripts/evaluate_retrieval.py \
     --collection community_mental_health_docs_v1 \
     --cases PsyConsult-community-kb-v1/knowledge_base/eval/retrieval_cases.jsonl \
     --k 3
   ```

## 接入现有 Agent 的注意事项

- 你现有 `agent/tools/vector_tool.py` 曾使用 `cloud_product_docs`。入库脚本不会自动改写应用代码。先定位该文件中创建 Milvus VectorStore 的 `collection_name` 配置，再将目标集合切换为 `community_mental_health_docs_v1`。
- 新集合必须使用与查询端一致的 DashScope embedding 模型及向量维度。入库脚本默认使用 `text-embedding-v3`，可通过 `DASHSCOPE_EMBEDDING_MODEL` 覆盖；如果当前 `vector_tool.py` 用的是其他模型，必须统一两端配置后再检索。
- 查询结果必须保留 `source_id`、`source_url`、`title`、`publisher`、`topic`、`section_path` 等元数据，供回答端生成可核实的来源列表。
- 检索失败、无相关证据和模型生成失败应区分处理，不能把检索成功但回答生成失败伪装成“知识库没有内容”。
- 自伤/自杀高风险识别和安全支持必须继续走独立安全路由，不得只靠检索本文件。

## 已知限制

- 该包完成了内容与脚本的本地构建，但没有连接你电脑上的 `localhost:19530`；实际入库需要在你的 Linux 项目环境中运行脚本。
- 量表正式上线前仍需确认具体中文版本、使用许可与计分规则。
- 12356 的地方接通情况、当地服务时间和机构地址需要根据具体地区另行核实。
- 药物安全文档尚未纳入逐个药品的批准说明书；不要据此生成具体药物用法或剂量。


## v1.0.2 入库兼容性修复

- 统一所有文档 Chunk 的 `license_note` 元数据；未在单篇文档中单独注明时，写入通用许可提醒，避免 Milvus 因非空字段缺失而拒绝插入。
- 该修复不删除或覆盖任何已有 Milvus 集合。若之前的入库尝试已创建目标集合，请使用新的集合名重试。
