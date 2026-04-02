from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.chroma import ensure_collection
from core.mongo import client as mongo_client
from app.routers import ingest, timeseries, search, cluster, network, chat
from ml.tasks import embed_all

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup Chroma and Embeddings dynamically on startup over empty setups
    collection = ensure_collection()
    # Simple count check
    if hasattr(collection, 'count'):
        c = collection.count()
    else:
        # chroma < v0.4
        c = len(collection.get()['ids'])
        
    if c == 0:
         embed_all.delay()
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
