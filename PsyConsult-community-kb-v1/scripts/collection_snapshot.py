"""Read-only integrity snapshot including vectors. No mutation operations."""
import argparse,hashlib,json
from pathlib import Path
from kb_common import load_environment,connection_args

def snapshot(name):
    from pymilvus import MilvusClient
    load_environment(); client=MilvusClient(**connection_args())
    rows=client.query(collection_name=name,filter='',output_fields=['*'],limit=16384)
    rows=sorted(rows,key=lambda r:str(r.get('pk',r.get('chunk_id',''))))
    payload=json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str)
    result={'collection':name,'rows':len(rows),'sha256_including_vectors':hashlib.sha256(payload.encode()).hexdigest(),
            'schema':client.describe_collection(name)}
    client.close(); return result
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--collection',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    result=snapshot(a.collection); Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n')
    print(result['collection'],result['rows'],result['sha256_including_vectors'])
