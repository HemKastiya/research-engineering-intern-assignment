from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from core.pinecone import ensure_index
from core.config import settings
from core.embedding_store import count_pinecone_vectors
from core.mongo import client as mongo_client, ensure_posts_indexes
from app.routers import ingest, timeseries, search, cluster, network, chat
from ml.embedder import warmup_embedder
from ml.tasks import (
    restore_pinecone_from_mongo,
    schedule_embed_all,
    seed_mongo_from_pinecone_if_empty,
)
from ml.network_builder import DEFAULT_BACKBONE_TOP_N, warm_network_backbone_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly load embedding model to avoid first-query timeout spikes.
    try:
        await asyncio.to_thread(warmup_embedder)
    except Exception as exc:
        print(f"[WARN] Failed to warm up embedding model: {exc}")

    try:
        await ensure_posts_indexes()
    except Exception as exc:
        print(f"[WARN] Failed to ensure Mongo posts indexes: {exc}")

    # Setup Pinecone and Embeddings dynamically on startup over empty setups
    collection = ensure_index()
    c = count_pinecone_vectors(collection)
        
    if c == 0:
         try:
             restored = await asyncio.to_thread(restore_pinecone_from_mongo)
             if restored > 0:
                 c = restored
                 print(f"[INFO] Restored {restored} vectors from MongoDB backup into Pinecone.")
             else:
                 schedule_embed_all()
         except Exception as exc:
             print(f"[WARN] Failed to restore Pinecone from MongoDB backup: {exc}")
             schedule_embed_all()
    else:
        async def _bootstrap_mongo_backup() -> None:
            try:
                copied = await asyncio.to_thread(seed_mongo_from_pinecone_if_empty)
                if copied > 0:
                    print(f"[INFO] Seeded MongoDB embedding backup from Pinecone ({copied} vectors).")
            except Exception as exc:
                print(f"[WARN] Failed to seed MongoDB embedding backup from Pinecone: {exc}")

        asyncio.create_task(
            _bootstrap_mongo_backup(),
            name="bootstrap_mongo_embedding_backup",
        )

    # Precompute default network backbone once, then serve from memory.
    try:
        await asyncio.to_thread(
            warm_network_backbone_cache,
            app.state,
            DEFAULT_BACKBONE_TOP_N,
        )
    except Exception as exc:
        print(f"[WARN] Failed to precompute network backbone: {exc}")
    yield
    # Teardown logic
    mongo_client.close()

app = FastAPI(title="Reddit Investigator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])
app.include_router(timeseries.router, prefix="/api/timeseries", tags=["Timeseries"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(cluster.router, prefix="/api/clusters", tags=["Clusters"])
app.include_router(network.router, prefix="/api/network", tags=["Network"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
