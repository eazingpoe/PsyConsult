#!/usr/bin/env python3
"""Source retrieval metrics, explicitly separate from behavioral evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
from kb_common import load_environment, embedding_key, embedding_model, connection_args

BEHAVIOR_TOPICS = {'general_no_hallucination'}

def score_case(case, results):
    found=set(); details=[]
    for doc,score in results:
        md=doc.metadata
        found.update(x.strip() for x in md.get('source_ids','').split(',') if x.strip())
        details.append({'metadata': md, 'score':float(score), 'content':doc.page_content})
    expected=set(case['expected_source_ids']); matched=expected & found
    return dict(case_id=case['case_id'],query=case['query'],expected=sorted(expected),
                found=sorted(found),matched=sorted(matched),missing=sorted(expected-found),
                any_hit=bool(matched),complete_hit=bool(expected) and expected <= found,
                coverage=len(matched)/len(expected) if expected else 0,results=details)

def summarize(rows):
    n=len(rows)
    return dict(cases=n,any_source_recall=sum(r['any_hit'] for r in rows)/n if n else 0,
        complete_source_hit_rate=sum(r['complete_hit'] for r in rows)/n if n else 0,
        macro_source_coverage=sum(r['coverage'] for r in rows)/n if n else 0,
        errors=sum('error' in r for r in rows))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--collection',required=True); p.add_argument('--cases',required=True)
    p.add_argument('--k',type=int,default=3); p.add_argument('--limit',type=int,default=0)
    p.add_argument('--output',required=True); p.add_argument('--diagnostic-k',type=int,default=10)
    a=p.parse_args()
    if a.k<1 or a.diagnostic_k<a.k: p.error('Require diagnostic-k >= k >= 1')
    load_environment(); model=embedding_model()
    from langchain_community.embeddings import DashScopeEmbeddings
    from langchain_milvus import Milvus
    from pymilvus import MilvusClient
    client=MilvusClient(**connection_args())
    if not client.has_collection(a.collection): raise ValueError('Collection does not exist')
    client.close()
    store=Milvus(embedding_function=DashScopeEmbeddings(model=model,dashscope_api_key=embedding_key()),
                 collection_name=a.collection,connection_args=connection_args())
    content=Path(a.cases).read_bytes()
    cases=[json.loads(line) for line in content.decode().splitlines() if line.strip()]
    if a.limit: cases=cases[:a.limit]
    rows=[]; behavior=[]
    for c in cases:
        try:
            results=store.similarity_search_with_score(c['query'],k=a.diagnostic_k)
            row=score_case(c,results[:a.k])
            row['diagnostic_results']=score_case(c,results)['results']
        except Exception as exc:
            row=score_case(c,[]); row['error']=type(exc).__name__
        if c.get('expected_topic') in BEHAVIOR_TOPICS:
            row['metric_scope']='legacy diagnostic only; independent behavior test required'
            behavior.append(row)
        else: rows.append(row)
        print(c['case_id'], 'COMPLETE' if row['complete_hit'] else 'PARTIAL' if row['any_hit'] else 'MISS',
              'matched=',row['matched'],'missing=',row['missing'],flush=True)
    report=dict(collection=a.collection,embedding_model=model,k=a.k,cases_sha256=hashlib.sha256(content).hexdigest(),
        retrieval=summarize(rows),legacy_all_cases_diagnostic=summarize(rows+behavior),
        cases=rows,behavior_diagnostics=behavior,
        metric_note='any_source_recall is historical Recall@k; complete requires ALL expected sources. Errors count as misses. Source IDs do not establish clinical correctness.')
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['retrieval'],ensure_ascii=False))
    return 0 if rows and all(r['complete_hit'] for r in rows) else 1
if __name__=='__main__': raise SystemExit(main())
