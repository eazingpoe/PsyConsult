"""Read-only post-ingestion verification of all rows and sampled embeddings."""
import json
from pathlib import Path
from kb_common import *
from collection_snapshot import snapshot
from audit_knowledge_base import audit

def main():
    load_environment()
    from pymilvus import MilvusClient
    from langchain_community.embeddings import DashScopeEmbeddings
    import numpy as np
    c=MilvusClient(**connection_args()); report={}; out=KB.parent/'reports/round2'
    expected={(x['metadata']['doc_id'],x['metadata']['section_path']):x for x in audit(KB/'community_mental_health')}
    rows=c.query('community_mental_health_docs_v1_0_3',filter='',output_fields=['*'],limit=16384)
    assert len(rows)==len(expected)==56
    for row in rows:
        e=expected[(row['doc_id'],row['section_path'])]
        assert row['text']==e['content']
        for key in ['source_ids','source_url','source_urls','source_title','publisher','source_scope']:
            assert row[key]==e['metadata'][key],key
        assert row['embedding_model']==embedding_model()
    emb=DashScopeEmbeddings(model=embedding_model(),dashscope_api_key=embedding_key())
    for name in ['community_mental_health_docs_v1_0_2','community_mental_health_docs_v1_0_3']:
        row=c.query(name,filter='',output_fields=['text','vector'],limit=1)[0]
        fresh=emb.embed_documents([row['text']])[0]; delta=float(np.max(np.abs(np.array(fresh)-np.array(row['vector']))))
        assert len(fresh)==len(row['vector'])==1024
        left,right=np.array(fresh),np.array(row['vector'])
        cosine=float(left@right/np.linalg.norm(left)/np.linalg.norm(right))
        # Provider encoding is not bitwise deterministic; verify directional agreement.
        assert cosine > 0.99999
        report[name]={'sample_vector_dimension':len(fresh),'sample_max_abs_difference_v3':delta,'sample_cosine_v3':cosine}
    old=snapshot('community_mental_health_docs_v1_0_2')
    before=json.loads((out/'old_collection_before.json').read_text())
    assert before['sha256_including_vectors']==old['sha256_including_vectors']
    (out/'old_collection_after.json').write_text(json.dumps(old,ensure_ascii=False,indent=2,default=str)+'\n')
    report.update(all_new_rows_verified=len(rows),old_collection_unchanged=True,embedding_model=embedding_model())
    (out/'database_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
