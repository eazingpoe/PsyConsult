#!/usr/bin/env python3
"""Validate every actual chunk against an explicit chapter source mapping."""
import argparse,json
from pathlib import Path
from ingest_knowledge_base import parse_frontmatter,section_chunks
from kb_common import provenance,section_metadata

def audit(docs):
    registry,mapping=provenance(); seen=set(); chunks=[]
    for p in sorted(Path(docs).glob('*.md')):
        meta,body=parse_frontmatter(p.read_text())
        for k in ['doc_id','title','topic','audience','source_ids','source_url','publisher','source_title','last_verified','review_status']:
            if not meta.get(k): raise ValueError(f'{p.name}: missing {k}')
        if meta['doc_id'] in seen: raise ValueError('Duplicate doc_id')
        seen.add(meta['doc_id'])
        ids=meta['source_ids'].split(',')
        if meta['source_url'] not in [registry[x]['source_url'] for x in ids]: raise ValueError('Document URL mismatch')
        sections=section_chunks(body,700,100,meta['title'])
        if set(mapping[meta['doc_id']]) != {h.split(' > ')[-1] for h,_ in sections}: raise ValueError('Stale section mapping')
        for heading,content in sections:
            md=dict(meta,**{})
            md.update(section_metadata(meta,heading,registry,mapping))
            md['section_path']=heading
            chunks.append(dict(metadata=md,content=content))
    if seen != set(mapping): raise ValueError('Stale document mapping')
    return chunks

def main():
    p=argparse.ArgumentParser(); p.add_argument('--docs',required=True)
    p.add_argument('--registry',required=True); p.add_argument('--output')
    a=p.parse_args()
    from kb_common import KB
    if Path(a.registry).resolve() != (KB/'source_registry.csv').resolve():
        raise ValueError('Audit uses the canonical registry; unexpected --registry')
    chunks=audit(a.docs)
    if a.output: Path(a.output).write_text(json.dumps(chunks,ensure_ascii=False,indent=2)+'\n')
    print(f'Validated {len(chunks)} chunks; exact chapter/source ID/URL mappings; duplicate IDs rejected.')
    print('Internal drafts remain drafts; static validation is not medical expert approval.')
if __name__=='__main__': main()
