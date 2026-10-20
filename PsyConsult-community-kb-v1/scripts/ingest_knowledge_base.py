#!/usr/bin/env python3
"""Safe first-time ingestion into a NEW Milvus collection. Never drops collections."""
import argparse, hashlib, os, re, sys
from pathlib import Path
from kb_common import load_environment, embedding_key, embedding_model, connection_args, provenance, section_metadata


def parse_frontmatter(text):
    if not text.startswith('---\n'):
        raise ValueError('Markdown 文件缺少 YAML frontmatter')
    end=text.find('\n---',4)
    if end < 0: raise ValueError('frontmatter 缺少结束分隔符')
    meta={}
    for line in text[4:end].splitlines():
        if ':' not in line: continue
        k,v=line.split(':',1); meta[k.strip()]=v.strip().strip('"\'')
    return meta, text[end+4:].lstrip()


def split_text(text, chunk_size, chunk_overlap):
    """Small dependency-free splitter with paragraph/sentence boundary preference."""
    text=text.strip()
    if not text: return []
    if len(text) <= chunk_size: return [text]
    chunks=[]; start=0
    preferred=['\n\n','\n','。','！','？','；','，',' ']
    while start < len(text):
        end=min(start+chunk_size,len(text))
        if end < len(text):
            floor=min(end, start+int(chunk_size*0.60))
            cut=-1
            for sep in preferred:
                pos=text.rfind(sep,floor,end)
                if pos > cut: cut=pos+len(sep)
            if cut > start: end=cut
        piece=text[start:end].strip()
        if piece: chunks.append(piece)
        if end >= len(text): break
        start=max(start+1,end-chunk_overlap)
    return chunks

def section_chunks(body, chunk_size, chunk_overlap, doc_title):
    """Keep heading path in every chunk; do not create title-only chunks."""
    lines=body.splitlines()
    sections=[]; path=[]; buf=[]
    def flush():
        nonlocal buf
        content='\n'.join(buf).strip()
        if content:
            sections.append((" > ".join(path) if path else doc_title, content))
        buf=[]
    for line in lines:
        m=re.match(r'^(#{1,6})\s+(.+?)\s*#*\s*$',line.strip())
        if m:
            flush(); level=len(m.group(1)); title=m.group(2).strip()
            path=path[:level-1]; path.append(title)
        else:
            buf.append(line)
    flush()
    result=[]
    for section_path, content in sections:
        # Source URLs are retained in metadata/source_registry; do not embed bibliography-only sections.
        if section_path.split(" > ")[-1].strip().startswith("来源"):
            continue
        for chunk in split_text(content, chunk_size, chunk_overlap):
            chunk=chunk.strip()
            if not chunk: continue
            if all((not x.strip()) or x.strip().startswith('#') for x in chunk.splitlines()):
                continue
            result.append((section_path, f'文档主题：{doc_title}\n章节：{section_path}\n\n{chunk}'))
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--docs',required=True,help='包含 Markdown 文件的目录')
    ap.add_argument('--collection',default='community_mental_health_docs_v1')
    ap.add_argument('--allow-draft',action='store_true',help='仅用于内部试运行，允许导入未审核草稿')
    ap.add_argument('--dry-run',action='store_true',help='只统计分块，不连接数据库')
    ap.add_argument('--chunk-size',type=int,default=700)
    ap.add_argument('--chunk-overlap',type=int,default=100)
    args=ap.parse_args()
    if args.chunk_size <= 0 or not 0 <= args.chunk_overlap < args.chunk_size:
        ap.error("Require 0 <= chunk_overlap < chunk_size")
    docs_dir=Path(args.docs)
    if not docs_dir.is_dir(): print(f'ERROR: 文档目录不存在: {docs_dir}'); return 2
    load_environment()
    registry, mapping = provenance()
    model = embedding_model()
    files=sorted(docs_dir.glob('*.md'))
    if not files: print('ERROR: 没有找到 Markdown 文档'); return 2

    all_docs=[]; ids=[]; skipped=[]; doc_ids=set()
    for path in files:
        try: meta, body=parse_frontmatter(path.read_text(encoding='utf-8'))
        except Exception as e: print(f'ERROR: {path.name}: {e}'); return 2
        required=['doc_id','title','topic','source_ids','source_url','publisher','source_title','review_status']
        missing=[x for x in required if not meta.get(x)]
        if missing: print(f'ERROR: {path.name} 缺少元数据: {missing}'); return 2
        if not meta['source_url'].startswith('https://'):
            print(f'ERROR: {path.name} 的 source_url 不是 HTTPS'); return 2
        if meta['review_status'] != 'approved_for_public_release' and not args.allow_draft:
            skipped.append((path.name,meta['review_status']))
            continue
        if not args.allow_draft and meta['review_status'] != 'approved_for_public_release':
            continue
        if meta['doc_id'] in doc_ids: raise ValueError('Duplicate doc_id')
        doc_ids.add(meta['doc_id'])
        chunks=section_chunks(body,args.chunk_size,args.chunk_overlap,meta['title'])
        if not chunks: print(f'ERROR: {path.name} 没有生成有效正文 Chunk'); return 2
        for n,(section_path, content) in enumerate(chunks,1):
            md={k:v for k,v in meta.items()}
            md.update(section_metadata(meta, section_path, registry, mapping))
            md["embedding_model"] = model
            # Milvus requires every row to provide every non-nullable metadata field.
            # Only some source documents carry an explicit license_note, so normalize it.
            md.setdefault('license_note', '未单独注明；请遵循 source_url 对应来源的许可和引用要求。')
            md.update({'source':path.name,'filename':path.name,'section_path':section_path,'chunk_index':str(n),'chunk_count':str(len(chunks))})
            # stable IDs are useful for evaluation and later versioned rebuilds
            chunk_id=hashlib.sha256((meta['doc_id']+'|'+section_path+'|'+str(n)+'|'+content).encode('utf-8')).hexdigest()[:32]
            md['chunk_id']=chunk_id
            all_docs.append({'page_content':content,'metadata':md,'id':chunk_id}); ids.append(chunk_id)
    if skipped:
        print('以下文档因未通过正式审核而跳过：')
        for name,status in skipped: print(f' - {name}: {status}')
    print(f'文档文件数: {len(files)}; 待入库文档数: {len(set(d["metadata"].get("doc_id") for d in all_docs))}; Chunk 数: {len(all_docs)}')
    title_only=sum(1 for d in all_docs if all((not x.strip()) or x.strip().startswith('#') for x in d['page_content'].splitlines()))
    print(f'纯标题 Chunk 数: {title_only}')
    if not all_docs:
        print('没有可入库文档。草稿仅能在内部测试时显式使用 --allow-draft。'); return 2
    if args.dry_run:
        for d in all_docs[:8]: print(f'\n[{d["metadata"]["doc_id"]} | {d["metadata"]["section_path"]}]\n{d["page_content"][:240]}')
        print('DRY RUN: 未连接 Milvus，未写入数据。'); return 0

    conn = connection_args()
    uri = conn['uri']
    token = conn.get('token')
    api_key=embedding_key()
    if not api_key: print('ERROR: 未找到 DASHSCOPE_API_KEY，请检查项目 .env / agent/.env'); return 2
    model=embedding_model()

    # Non-destructive guard: refuse if target collection already exists.
    try:
        from pymilvus import connections, utility
        alias='psyconsult_kb_ingest_guard'
        kwargs={'alias':alias,'uri':uri}
        if token: kwargs['token']=token
        connections.connect(**kwargs)
        existing=utility.list_collections(using=alias)
        if args.collection in existing:
            print(f'ERROR: 集合 {args.collection!r} 已存在。为避免重复数据或破坏旧数据，脚本不会覆盖/清空它。请换新版本集合名。')
            return 3
    except Exception as e:
        print(f'ERROR: 无法检查 Milvus 连接/集合状态: {type(e).__name__}: {e}')
        return 2
    finally:
        try: connections.disconnect('psyconsult_kb_ingest_guard')
        except Exception: pass

    try:
        from langchain_core.documents import Document
        from langchain_community.embeddings import DashScopeEmbeddings
        from langchain_milvus import Milvus
        docs_for_ingest=[Document(page_content=d['page_content'],metadata=d['metadata']) for d in all_docs]
        emb=DashScopeEmbeddings(model=model, dashscope_api_key=api_key)
        conn={'uri':uri}
        if token: conn['token']=token
        print(f'准备入库：collection={args.collection}, uri={uri}, embedding={model}, chunks={len(all_docs)}')
        Milvus.from_documents(
            documents=docs_for_ingest,
            embedding=emb,
            collection_name=args.collection,
            connection_args=conn,
            ids=ids,
            drop_old=False,
        )
        print('入库完成。集合未被覆盖；请运行 evaluate_retrieval.py 验证检索质量。')
        return 0
    except Exception as e:
        print(f'ERROR: 入库失败: {type(e).__name__}: {e}')
        print('注意：脚本没有调用 drop_collection。若集合创建后中途失败，请先检查 Milvus 中目标集合，再决定是否使用新的版本名重试。')
        return 1

if __name__=='__main__': sys.exit(main())
