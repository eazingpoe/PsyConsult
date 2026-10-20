#!/usr/bin/env python3
"""Exercise production retrieval tool and answer prompt with actual new KB evidence."""
import argparse,json,os,sys
from pathlib import Path
from kb_common import ROOT,load_environment,embedding_model
sys.path.insert(0,str(ROOT/'agent'))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--collection',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    load_environment(); os.environ['MILVUS_COLLECTION_NAME']=a.collection
    from tools.vector_tool import query_vector_db,_get_milvus_store
    from agents.treatment_agent import TreatmentAgentNode
    from config import get_settings
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage,HumanMessage,AIMessage,ToolMessage
    llm=ChatOpenAI(**get_settings().get_model_config(),temperature=0.1,timeout=60,max_retries=1)
    node=TreatmentAgentNode.__new__(TreatmentAgentNode)
    path=Path(__file__).resolve().parents[1]/'knowledge_base/eval/retrieval_cases.jsonl'
    cases=[json.loads(x) for x in path.read_text().splitlines()]
    rows=[]
    for case in cases:
        if case['case_id'] not in ['KB014','KB021','KB038','KB040']: continue
        evidence=json.loads(query_vector_db.invoke({'query':case['query']}))
        assert evidence['status']=='success'
        ids=set()
        for e in evidence['evidence']:
            m=e['metadata']; ids.update(m['source_ids'].split(','))
            assert m['doc_id'] and m['section_path'] and m['source_url']
            assert set(json.loads(m['source_urls']))==set(m['source_ids'].split(','))
        messages=[SystemMessage(content=node._build_system_prompt('')),HumanMessage(content=case['query']),
            AIMessage(content='',tool_calls=[{'id':'actual-evidence','name':'query_vector_db','args':{'query':case['query']}}]),
            ToolMessage(content=json.dumps(evidence,ensure_ascii=False),tool_call_id='actual-evidence')]
        answer=llm.invoke(messages).content
        rows.append({'case_id':case['case_id'],'query':case['query'],'complete_hit':set(case['expected_source_ids'])<=ids,'evidence':evidence,'answer':answer,'manual_review':'pending'})
        print(case['case_id'],rows[-1]['complete_hit'],flush=True)
    store=_get_milvus_store()
    assert store.collection_name==a.collection
    Path(a.output).write_text(json.dumps({'collection':store.collection_name,'embedding_model':embedding_model(),'scope':'Production query_vector_db + actual application prompt and LLM. Not HTTP/SSE, routing, or semantic-cache validation.','cases':rows},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__': main()
