from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from core.chroma import ensure_collection
from core.mongo import client as mongo_client
from app.routers import ingest, timeseries, search, cluster, network, chat
from ml.embedder import warmup_embedder
from ml.tasks import schedule_embed_all
from ml.network_builder import DEFAULT_BACKBONE_TOP_N, warm_network_backbone_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly load embedding model to avoid first-query timeout spikes.
    try:
        await asyncio.to_thread(warmup_embedder)
    except Exception as exc:
        print(f"[WARN] Failed to warm up embedding model: {exc}")

    # Setup Chroma and Embeddings dynamically on startup over empty setups
    collection = ensure_collection()
    # Simple count check
    if hasattr(collection, 'count'):
        c = collection.count()
    else:
        # chroma < v0.4
        c = len(collection.get()['ids'])
        
    if c == 0:
         schedule_embed_all()

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
    allow_origins=["http://localhost:3000"],
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
