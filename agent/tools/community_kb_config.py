"""Shared configuration for community KB ingestion, evaluation and application."""
import os
from pathlib import Path

MODEL = "text-embedding-v3"
OLD_COLLECTION = "community_mental_health_docs_v1_0_2"
NEW_COLLECTION = "community_mental_health_docs_v1_0_3"


def load_environment():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def embedding_model():
    model = os.getenv("DASHSCOPE_EMBEDDING_MODEL", MODEL)
    if model != MODEL:
        raise ValueError(f"Community KB requires {MODEL}, received {model}")
    return model


def embedding_key():
    return next((os.environ[k].strip() for k in (
        "EMBEDDING_API_KEY", "DASHSCOPE_EMBEDDING_API_KEY", "DASHSCOPE_API_KEY"
    ) if os.getenv(k, "").strip()), None)


def connection_args():
    args = {"uri": os.getenv("MILVUS_URI") or
            f"http://{os.getenv('MILVUS_HOST', 'localhost')}:{os.getenv('MILVUS_PORT', '19530')}"}
    if os.getenv("MILVUS_TOKEN"):
        args["token"] = os.environ["MILVUS_TOKEN"]
    return args
