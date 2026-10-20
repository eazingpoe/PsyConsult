import json
from types import SimpleNamespace

from agent.tools import vector_tool


class FakeVectorStore:
    def __init__(self, results):
        self.results = results

    def similarity_search_with_score(self, query, k):
        assert k == 3
        return self.results


def make_document(content, metadata):
    return SimpleNamespace(page_content=content, metadata=metadata)


def test_vector_search_preserves_evidence_and_metadata(monkeypatch):
    document = make_document(
        "心理健康指南中的原始段落。",
        {
            "source": "/data/guidelines/mental_health.pdf",
            "page": 12,
            "section": "2.1",
            "title": "心理健康指南",
            "internal_secret": "must_not_be_exposed",
        },
    )
    monkeypatch.setattr(
        vector_tool,
        "_get_milvus_store",
        lambda: FakeVectorStore([(document, 0.27)]),
    )

    raw = vector_tool.query_vector_db.invoke({"query": "心理健康"})
    result = json.loads(raw)

    assert result["status"] == "success"
    assert len(result["evidence"]) == 1

    evidence = result["evidence"][0]
    assert evidence["source"] == "mental_health.pdf"
    assert evidence["content"] == "心理健康指南中的原始段落。"
    assert evidence["metadata"]["page"] == 12
    assert evidence["metadata"]["section"] == "2.1"
    assert evidence["metadata"]["title"] == "心理健康指南"
    assert "internal_secret" not in evidence["metadata"]
    assert evidence["raw_score"] == 0.27
    assert "置信度" in result["retrieval"]["score_note"]


def test_vector_search_reports_no_results(monkeypatch):
    monkeypatch.setattr(
        vector_tool,
        "_get_milvus_store",
        lambda: FakeVectorStore([]),
    )

    result = json.loads(
        vector_tool.query_vector_db.invoke({"query": "无匹配结果"})
    )

    assert result["status"] == "no_results"
    assert result["evidence"] == []


def test_vector_search_reports_failure_without_fake_evidence(monkeypatch):
    def fail():
        raise ConnectionError("simulated database failure")

    monkeypatch.setattr(vector_tool, "_get_milvus_store", fail)

    result = json.loads(
        vector_tool.query_vector_db.invoke({"query": "测试检索失败"})
    )

    assert result["status"] == "error"
    assert result["evidence"] == []
    assert result["error_type"] == "ConnectionError"


def test_community_source_ids_and_urls_reach_application(monkeypatch):
    metadata = {'source': 'knowledge.md', 'doc_id': 'doc1', 'source_ids': 'A,B',
                'source_url': 'https://example.org/a',
                'source_urls': json.dumps({'A': 'https://example.org/a', 'B': 'https://example.org/b'}),
                'section_path': 'Topic > Safety', 'source_scope': 'screening only',
                'review_status': 'draft_for_internal_testing'}
    monkeypatch.setattr(vector_tool, '_get_milvus_store', lambda: FakeVectorStore([(make_document('content',metadata),0.2)]))
    result=json.loads(vector_tool.query_vector_db.invoke({'query':'screening'}))
    for key in ('doc_id','source_ids','source_url','source_urls','section_path','source_scope','review_status'):
        assert result['evidence'][0]['metadata'][key]==metadata[key]
