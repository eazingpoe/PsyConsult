import json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[2]
KB=ROOT/'PsyConsult-community-kb-v1'
sys.path.insert(0,str(KB/'scripts'))
from audit_knowledge_base import audit
from evaluate_retrieval import score_case,summarize
from ingest_knowledge_base import section_chunks
from kb_common import provenance,section_metadata
from agent.tools.community_kb_config import embedding_model

def test_all_chunks_have_consistent_sources():
    chunks=audit(KB/'knowledge_base/community_mental_health')
    assert len(chunks)>50
    for c in chunks:
        m=c['metadata']; urls=json.loads(m['source_urls'])
        assert set(m['source_ids'].split(','))==set(urls)
        assert m['source_url'] in urls.values()
        assert m['section_path'] and m['doc_id']

def test_original_cases_unchanged():
    assert (KB/'knowledge_base/eval/retrieval_cases.jsonl').read_bytes()==(KB/'reports/round2/before/retrieval_cases.jsonl').read_bytes()

def test_complete_hit_is_not_any_hit_and_errors_stay_in_denominator():
    case={'case_id':'X','query':'q','expected_source_ids':['A','B']}
    doc=SimpleNamespace(metadata={'source_ids':'A'},page_content='a')
    partial=score_case(case,[(doc,0.2)]); missing=score_case(case,[])
    assert partial['any_hit'] and not partial['complete_hit']
    assert partial['missing']==['B']
    assert summarize([partial,missing])['macro_source_coverage']==0.25

def test_bibliography_not_embedded():
    result=section_chunks('# Doc\n## Body\nReal content\n## 来源与边界\nURL only',700,100,'Doc')
    assert len(result)==1 and 'URL only' not in result[0][1]

def test_unknown_section_fails_closed():
    registry,mapping=provenance()
    with pytest.raises(KeyError): section_metadata({'doc_id':'screening_scales_001'},'unknown',registry,mapping)

def test_embedding_model_cannot_silently_drift(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_EMBEDDING_MODEL','text-embedding-v2')
    with pytest.raises(ValueError): embedding_model()

def test_phq9_chunk_not_attributed_to_gad7():
    chunks=audit(KB/'knowledge_base/community_mental_health')
    c=next(c for c in chunks if '第九题非零' in c['metadata']['section_path'])
    assert 'GAD7_SPITZER_2006' not in c['metadata']['source_ids']
    assert '不等于已经确定高危' in c['content']
    assert 'NHC_12356_2024' in c['metadata']['source_ids']


def test_agent_import_preserves_explicit_collection_and_model():
    import subprocess,os
    env=dict(os.environ,MILVUS_COLLECTION_NAME='community_mental_health_docs_v1_0_3',DASHSCOPE_EMBEDDING_MODEL='text-embedding-v3')
    code="import sys,os; sys.path.insert(0,'agent'); from agents.treatment_agent import TreatmentAgentNode; assert os.environ['MILVUS_COLLECTION_NAME']=='community_mental_health_docs_v1_0_3'; assert os.environ['DASHSCOPE_EMBEDDING_MODEL']=='text-embedding-v3'"
    subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,check=True,capture_output=True)
