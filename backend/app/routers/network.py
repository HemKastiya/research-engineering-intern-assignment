import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.schemas import GraphResult
from ml.network_builder import (
    DEFAULT_BACKBONE_TOP_N,
    DEFAULT_MAX_RESPONSE_NODES,
    get_network_payload,
)

router = APIRouter()

@router.get("", response_model=GraphResult)
async def get_network(
    request: Request,
    query: Optional[str] = None,
    graph_type: str = "co_subreddit",
    top_n: int = DEFAULT_BACKBONE_TOP_N,
    max_nodes: int = DEFAULT_MAX_RESPONSE_NODES,
):
    try:
        return await asyncio.to_thread(
            get_network_payload,
            request.app.state,
            query,
            graph_type,
            top_n,
            max_nodes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build network graph: {exc}")
