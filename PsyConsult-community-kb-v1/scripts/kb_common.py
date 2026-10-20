"""Shared configuration and fail-closed chapter provenance."""
import csv
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.tools.community_kb_config import load_environment, embedding_key, embedding_model, connection_args
KB = Path(__file__).resolve().parents[1] / "knowledge_base"
def provenance():
    with (KB / "source_registry.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    registry = {r["source_id"]: r for r in rows}
    if len(registry) != len(rows): raise ValueError("Duplicate source_id")
    return registry, json.loads((KB / "section_sources.json").read_text())
def section_metadata(meta, section_path, registry, mapping):
    entry = mapping[meta["doc_id"]][section_path.split(" > ")[-1]]
    ids = entry["source_ids"]
    if not ids: raise ValueError("Missing section source")
    if not set(ids) <= set(meta["source_ids"].split(",")):
        raise ValueError("Section source absent from document")
    sources = [registry[sid] for sid in ids]
    urls = {s["source_id"]: s["source_url"] for s in sources}
    if not all(u.startswith("https://") for u in urls.values()): raise ValueError("Non-HTTPS source")
    return dict(source_ids=",".join(ids), source_url=sources[0]["source_url"],
        source_urls=json.dumps(urls, ensure_ascii=False),
        source_title="; ".join(s["source_title"] for s in sources),
        publisher="; ".join(dict.fromkeys(s["publisher"] for s in sources)), source_scope=entry["scope"])
