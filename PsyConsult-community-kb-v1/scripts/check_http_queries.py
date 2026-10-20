#!/usr/bin/env python3
"""Real ASGI lifespan, authentication, workflow and SSE; synthetic test identities."""
import argparse,json,os,uuid
from pathlib import Path
from kb_common import load_environment

def main():
    p=argparse.ArgumentParser(); p.add_argument('--collection',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    load_environment(); os.environ['MILVUS_COLLECTION_NAME']=a.collection
    os.environ['ENABLE_SEMANTIC_CACHE']='false'
    from fastapi.testclient import TestClient
    from app.app_main import app
    from app.app_config.settings import settings
    from tools.vector_tool import _get_milvus_store
    path=Path(__file__).resolve().parents[1]/'knowledge_base/eval/retrieval_cases.jsonl'
    rows=[]
    with TestClient(app) as client:
        for c in map(json.loads,path.read_text().splitlines()):
            if c['case_id'] not in ['KB014','KB021','KB038','KB040']: continue
            uid='kb-round2-'+uuid.uuid4().hex[:12]
            headers={'X-User-Id':uid}
            if settings.api_auth_token: headers['Authorization']='Bearer '+settings.api_auth_token
            response=client.post('/api/chat',headers=headers,json={'query':c['query'],'session_id':uid})
            events=[json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
            assert response.status_code==200
            assert any(e.get('done') for e in events)
            assert not any(e.get('error') or e.get('status')=='error' for e in events)
            answer=''.join(e.get('content','') for e in events if e.get('agent')=='treatment_recommend' and 'status' not in e)
            rows.append({'case_id':c['case_id'],'http_status':response.status_code,'answer':answer,'sse':response.text})
            Path(a.output).write_text(json.dumps({'collection':a.collection,'scope':'Real ASGI lifespan + API + workflow + SSE. Dedicated process, semantic cache disabled; existing server untouched. Synthetic IDs; Redis checkpoints may persist until normal TTL.','cases':rows},ensure_ascii=False,indent=2)+'\n')
            print(c['case_id'],response.status_code,flush=True)
        assert _get_milvus_store().collection_name==a.collection
if __name__=='__main__': main()
