from __future__ import annotations

from typing import Any

try:
    from pinecone.grpc import PineconeGRPC as Pinecone
except Exception:  # pragma: no cover - fallback when gRPC deps are unavailable
    from pinecone import Pinecone
from pinecone import ServerlessSpec

from core.config import settings

_pinecone_client: Pinecone | None = None
_pinecone_index = None
_pinecone_index_host: str | None = None


def get_pinecone() -> Pinecone:
    global _pinecone_client
    if _pinecone_client is None:
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _pinecone_client


def get_pinecone_namespace() -> str:
    namespace = str(settings.PINECONE_NAMESPACE or "").strip()
    return namespace if namespace else "__default__"


def _extract_index_host(description: Any) -> str | None:
    if isinstance(description, dict):
        return str(description.get("host") or "").strip() or None
    host = getattr(description, "host", None)
    if host:
        return str(host).strip()
    return None


def _resolve_index_host(pc: Pinecone) -> str:
    configured_host = str(settings.PINECONE_INDEX_HOST or "").strip()
    if configured_host:
        return configured_host

    description = pc.describe_index(name=settings.PINECONE_INDEX_NAME)
    host = _extract_index_host(description)
    if not host:
        raise ValueError("Pinecone index host not found. Set PINECONE_INDEX_HOST.")
    return host


def get_pinecone_index():
    global _pinecone_index, _pinecone_index_host
    pc = get_pinecone()
    host = _resolve_index_host(pc)
    if _pinecone_index is None or host != _pinecone_index_host:
        _pinecone_index = pc.Index(host=host)
        _pinecone_index_host = host
    return _pinecone_index


def ensure_index():
    pc = get_pinecone()
    try:
        pc.describe_index(name=settings.PINECONE_INDEX_NAME)
    except Exception:
        if not settings.PINECONE_AUTO_CREATE:
            raise

        cloud = str(settings.PINECONE_CLOUD or "").strip()
        region = str(settings.PINECONE_REGION or "").strip()
        if not cloud or not region:
            raise ValueError("PINECONE_CLOUD and PINECONE_REGION are required for auto-create.")

        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=int(settings.EMBEDDING_DIM),
            metric="cosine",
            spec=ServerlessSpec(cloud=cloud, region=region),
        )

    return get_pinecone_index()


def get_namespace_vector_count(index, namespace: str | None = None) -> int:
    stats = index.describe_index_stats()
    namespaces = {}
    if isinstance(stats, dict):
        namespaces = stats.get("namespaces") or {}
    else:
        namespaces = getattr(stats, "namespaces", {}) or {}

    target = namespace or get_pinecone_namespace()
    info = namespaces.get(target) or {}
    if isinstance(info, dict):
        value = info.get("vector_count")
        if value is None:
            value = info.get("vectorCount")
    else:
        value = getattr(info, "vector_count", None)
        if value is None:
            value = getattr(info, "vectorCount", None)
    try:
        return int(value or 0)
    except Exception:
        return 0
