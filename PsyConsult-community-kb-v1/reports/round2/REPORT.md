# 社区心理健康知识库第二轮优化报告

日期：2026-10-20。新集合 `community_mental_health_docs_v1_0_3` 已创建，12 篇内部测试草稿、56 个分块。旧集合 `community_mental_health_docs_v1_0_2` 的 52 个分块及向量完整性指纹未变。未修改 `mock_data`；原始 40 题 JSONL 字节保持一致，未修改任何原始预期来源。

## 定位结果（先实测旧库，再修改）

- KB014：相关双相段落存在，旧排名第 4（L2 约 0.703766），通用知识第 3（约 0.702564）。症状识别与专业求助分散，标题泛化，查询被睡眠内容占据。新增独立症状识别与专业求助段落，不修改查询或预期来源。
- KB021：旧报告 HIT 实际只是 PHQ-9 来源命中，缺少服务导航来源。原文已经说非零不能判定危险等级，问题是衔接与来源归属不足。新增清楚的安全确认、专业评估与紧急求助衔接；NIMH 资料仅支持 ASQ 阳性成人的专业评估一般原则，不冒充 PHQ-9 风险分级算法。
- KB034：这是无证据时的回答行为，不是 WHO 医学来源检索问题。原题、原预期均保留，旧检索结果单列诊断；独立运行无结果、错误、无关证据三种回答测试，不用检索命中替代行为合规。
- KB038：旧 Top 3 全为压力自助，服务导航第 6、抑郁文档第 8。分别在抑郁文档和服务导航中建立持续低落、工作受影响与专业评估的联系，并明确 WHO 支持症状求助、卫健委支持门诊建设。
- KB040：通用文档缺少治疗、康复、社会支持专节，旧排名第 9。按 WHO 精神障碍事实清单补充概述，不增加个体化处方或疗效保证。
- 来源元数据：旧入库将整篇来源赋给所有章节，PHQ-9 段落被错误附加 GAD-7，工程规则被算作医学来源命中。睡眠文档 ID 指向压力指南、URL 却指向压力问答。现采用逐章节显式映射和多来源 URL 字典；来源与编辑规则的作用在 `source_scope` 中区分。
- 应用配置：图谱工具导入时 `load_dotenv(..., override=True)` 会把显式指定的 v1_0_3 覆盖回 `.env` 的旧库。图谱和向量工具均改为环境变量优先，并增加子进程导入回归测试。
- 回答引用：实测曾把本地整理标题列为官方文献，现提示词要求使用 `source_title/source_urls`，不可把 `title/section_path` 冒充官方标题，并遵守 `source_scope`。

## 评测口径与结果

历史 Recall@3 指“至少命中一个预期来源”，并非所有预期来源都命中。新增完整命中率（全部预期来源进入 Top 3）、逐题 matched/missing、平均来源覆盖率、Top 10 诊断内容、配置及测试集 SHA256。查询错误计为失败，不能从分母移除。

正式来源检索为原集 39 题；KB034 单列行为测试。为保持可追溯性，JSON 同时保留原 40 题旧口径诊断结果。以下前后两列使用完全相同口径：

|范围与指标|旧集合|新集合|
|---|---:|---:|
|39题 Recall@3（任一预期来源）|92.3%|92.3%|
|39题完整来源命中率|89.7%|82.1%|
|39题平均来源覆盖率|91.0%|87.2%|
|8题改写 Recall@3|87.5%|100.0%|
|8题改写完整来源命中率|50.0%|100.0%|

四道重点检索题 KB014/021/038/040 均完整命中。全套完整命中率没有提升：来源纠错消除了部分虚假命中，同时存在检索回归，不能将针对性成功表述为全套通过。

### 全部原题逐题来源命中

下表“命中/预期”以来源数量计，详细 Top 3 正文、标题、URL、分数见 `baseline.json` / `after.json`。

|题号|旧命中/预期|新命中/预期|新库缺失的预期来源|
|---|---:|---:|---|
|KB001|1/1|1/1|无|
|KB002|1/1|1/1|无|
|KB003|2/2|2/2|无|
|KB004|1/1|1/1|无|
|KB005|1/1|1/1|无|
|KB006|2/2|0/2|WHO_MENTAL_DISORDERS_ZH_2026, WHO_STRESS_GUIDE_2020|
|KB007|1/1|1/1|无|
|KB008|1/1|1/1|无|
|KB009|1/1|1/1|无|
|KB010|1/1|1/1|无|
|KB011|1/1|1/1|无|
|KB012|1/1|1/1|无|
|KB013|1/1|1/1|无|
|KB014|0/1|1/1|无|
|KB015|1/1|1/1|无|
|KB016|1/1|1/1|无|
|KB017|1/1|1/1|无|
|KB018|1/1|1/1|无|
|KB019|1/1|1/1|无|
|KB020|1/1|1/1|无|
|KB021|1/2|2/2|无|
|KB022|2/2|1/2|NMPA_OFFICIAL_PORTAL|
|KB023|1/1|1/1|无|
|KB024|2/2|1/2|NMPA_OFFICIAL_PORTAL|
|KB025|1/1|0/1|NMPA_OFFICIAL_PORTAL|
|KB026|1/1|1/1|无|
|KB027|1/1|1/1|无|
|KB028|1/1|1/1|无|
|KB029|2/2|2/2|无|
|KB030|1/1|1/1|无|
|KB031|2/2|1/2|NHC_12356_2024|
|KB032|2/2|1/2|NHC_12356_2024|
|KB033|1/1|1/1|无|
|KB034（独立行为题，仅诊断）|0/1|0/1|WHO_MENTAL_DISORDERS_ZH_2026|
|KB035|1/1|1/1|无|
|KB036|1/1|0/1|NMPA_OFFICIAL_PORTAL|
|KB037|1/1|1/1|无|
|KB038|0/2|2/2|无|
|KB039|2/2|2/2|无|
|KB040|0/1|1/1|无|

### 剩余问题及发布决定

- KB006：新 Top 3 没有原预期的精神障碍/压力指南来源；睡眠来源修正为真实的 WHO 压力问答后，原来依靠整篇来源继承的命中消失。后续应补充确有指南支持的睡前压力应对与求助内容；本轮没有改预期来抬分。
- KB022/024/025/036：药监门户仅能支持官方查询入口，不足以支持用药事实；新库用 NIMH 用药资料支撑一般安全原则。原预期门户仍保留，按缺失报告。后续需要具体产品的现行批准说明书，不应重新给所有药物段落贴门户来源。
- KB031/032：新 Top 3 缺少热线通知，已有 WHO/NIMH 危机求助内容；安全回答与热线导航仍有检索覆盖缺口。危机独立路由不应依赖检索命中。
- 文档仍为 `draft_for_internal_testing`，未伪装为医学专家审核完成。
- 独立模型行为测试属于有限样本检查，不证明所有提示下都不会产生幻觉。
- 现有在线服务未重启，`agent/.env` 的默认集合仍为 v1_0_2。新库通过显式配置在独立真实应用进程中验证；由于全套完整来源命中率下降，本轮不自动将现有服务切换到新库。
- HTTP 测试启动了真实应用工作流并使用合成测试身份；正常 Redis checkpoint 可能存留至 TTL。未清空 Redis 或其他集合。测试退出发现既有 checkpointer 关闭警告，不影响四题 SSE 完成，尚未处理该无关生命周期问题。

## 修改文件及目的

- `knowledge_base/community_mental_health/01、04、06、09、11`：补充本轮场景；全部 12 篇同步章节真实来源的文档汇总元数据/来源列表，版本记为 1.0.3。
- `02`：独立权威自助资料导航段落；`03`：纠正压力问答来源并收敛睡眠建议到已核查来源；`10`：区分药品查询入口与一般用药安全依据；`12`：区分安全原则、热线导航和平台工程规则。`05、07、08` 主要为来源元数据统一。
- `source_registry.csv`：新增真实 WHO 压力问答、NIMH 安全评估和用药资料。历史来源 ID 不因官网更新年份而重命名，年份后缀仅视为稳定 ID。
- `section_sources.json`、`scripts/kb_common.py`：章节级来源、URL、标题、发布者与使用边界；未知映射拒绝入库。
- `scripts/ingest_knowledge_base.py`：共享 embedding 配置，逐块写来源元数据及模型名，拒绝重复 doc_id/非法分块参数，跳过来源目录段落，继续拒绝覆盖现有集合。
- `scripts/audit_knowledge_base.py`：检查每个实际分块，拒绝来源/章节/URL/ID 不一致，导出审计正文。
- `scripts/evaluate_retrieval.py`：完整率、覆盖率、逐题 JSON、Top 10 诊断，行为题独立计量。
- `knowledge_base/eval/targeted_retrieval_cases.jsonl`：8 道改写回归题；`behavior_cases.jsonl`：独立 KB034 场景，原 `retrieval_cases.jsonl` 未改。
- `agent/tools/community_kb_config.py`：入库、评测与应用知识查询共用模型、连接和 key 优先级；非 v3 配置立即报错，不静默混用。缓存/长期记忆使用其他集合的 v2 配置未被迁移。
- `agent/tools/vector_tool.py`：返回真实 doc_id、source_ids、多 URL、章节和来源作用范围。
- `agent/tools/graph_tool.py`：不覆盖显式部署环境变量。
- `agent/agents/treatment_agent.py`：区分本地标题与官方来源、NIMH 适用边界。
- `agent/test/test_community_kb_round2.py`、`test_vector_tool_evidence.py`、`test_treatment_agent_prompt.py`、`app/test/test_assessment_api.py`：来源一致性、配置导入、完整指标、PHQ-9 非零不判定高危与引用边界回归。
- `scripts/evaluate_behavior.py`、`check_application_queries.py`、`check_http_queries.py`：真实模型行为、生产查询工具、真实 ASGI/API/工作流/SSE 验证，独立记录结果。
- `scripts/collection_snapshot.py`、`verify_collection.py`：旧集合指纹及新库全部实际分块校验、模型抽样比对。
- `reports/round2/`：原始数据快照、前后全量结果、分块审计、应用回答、测试与完整性报告；`MANIFEST.json` 重新计算文件哈希。

## 运行与回滚

在项目根目录使用 `/home/user/miniconda3/envs/psyconsult/bin/python`。新集合已存在，不能再次对其执行入库；脚本会拒绝覆盖。若继续修改正文，需再选一个新版本集合并重新评测。

复测示例：

```bash
/home/user/miniconda3/envs/psyconsult/bin/python PsyConsult-community-kb-v1/scripts/evaluate_retrieval.py --collection community_mental_health_docs_v1_0_3 --cases PsyConsult-community-kb-v1/knowledge_base/eval/retrieval_cases.jsonl --output /tmp/psyconsult-v3-recheck.json
```

评测退出码 1 表示存在未完整命中的用例，不是连接必然失败；检查 JSON 的 errors 字段。脚本依赖实际已配置的 DashScope key，不写入报告。

若后续决定启用新库，将部署环境或 `agent/.env` 中 `MILVUS_COLLECTION_NAME` 设为 `community_mental_health_docs_v1_0_3`，`DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3`。重启对应后端进程使向量单例重建，并禁用旧回答缓存（`ENABLE_SEMANTIC_CACHE=false`）或另行实施版本隔离；不要清空任何既有集合。

回滚时只需把 `MILVUS_COLLECTION_NAME` 改回 `community_mental_health_docs_v1_0_2` 并重启该后端进程；embedding 保持 v3。若环境变量与 `.env` 同时设置，环境变量优先。旧集合无需重新导入，新集合也无需删除。当前默认服务本就仍指向旧集合。

## 权威来源核对

本轮补充核对了 [WHO 双相情感障碍](https://www.who.int/zh/news-room/fact-sheets/detail/bipolar-disorder)、[WHO 精神障碍](https://www.who.int/zh/news-room/fact-sheets/detail/mental-disorders)、[WHO 抑郁障碍](https://www.who.int/zh/news-room/fact-sheets/detail/depression)、[WHO 压力问答](https://www.who.int/news-room/questions-and-answers/item/stress)、[WHO 自助实施手册](https://www.who.int/publications/i/item/9789240120785)、[NIMH 成人安全评估](https://www.nimh.nih.gov/research/research-conducted-at-nimh/asq-toolkit-materials/adult-outpatient/adult-outpatient-brief-suicide-safety-assessment-guide)、[NIMH 用药资料](https://www.nimh.nih.gov/health/topics/mental-health-medications)。卫健委服务通知直连返回 412，使用官方域名搜索索引核对心理/睡眠门诊建设段落，未把该索引核对说成医院当前服务确认。PHQ/GAD 原始文献登记不变；不声称本轮重新完整审核了量表授权或中文版本。

## 最终验证记录

- `pytest.txt`：72 passed；已有 LangChain 弃用提示 1 条。
- `database_verification.json`：新库 56 条正文与来源元数据全部一致；旧库包含向量的 SHA256 前后一致。两库抽样向量均为 1024 维，与当前 v3 文档编码余弦相似度约 0.99999928；最大元素差约 0.000156，因此不声称服务端编码按位确定。
- `behavior.json`：KB034 三种证据条件的真实模型回答均拒绝编造并说明证据不足；不与检索指标合并。此记录来自增加更严格来源标题规则前的提示词。
- `application_queries_final.json`：生产向量查询工具四题全部预期来源命中，真实回答来源可追溯。
- `http_queries_final.json`：真实 ASGI lifespan、认证、完整工作流、SSE 四题均 HTTP 200 且 done=true、无错误事件；明确使用新集合、关闭该测试进程的语义缓存。没有把真实模型测试描述为 mocked 单元测试。
- 生成回答尚有用语优化空间：HTTP KB038 附加提醒将一般自伤想法/绝望与紧急求助并列，可进一步按当前危险程度细化。不能把有限场景测试通过等同于医学安全性已全面验证。
- `git diff --check` 通过；`git status --short mock_data` 无变更。现有项目中用户原先的其他未提交修改保持原状。
