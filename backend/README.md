# Backend README

This directory contains the FastAPI backend for **The Daily Query**. It powers the project's data access, semantic retrieval, time-series analytics, topic clustering, network analysis, embedding projection, and retrieval-augmented chat workflows.

The backend sits between the Reddit corpus and the Next.js frontend. MongoDB stores the cleaned posts, Pinecone stores dense vector embeddings, and Gemini is used for generated summaries and chat responses.

## Stack

- FastAPI
- MongoDB via Motor and PyMongo
- Pinecone for vector search
- Sentence Transformers for embeddings
- BERTopic, UMAP, and HDBSCAN for topic analysis
- NetworkX and python-louvain for graph analysis
- scikit-learn for regression, anomaly detection, and clustering
- Gemini 2.5 Flash for natural-language summaries and RAG answers

## What This Backend Does

The service provides the full analysis layer for the project:

- corpus ingest status and indexing health
- semantic search over embedded Reddit content
- time-series aggregations and statistical overlays
- BERTopic topic clustering
- 2D embedding projection with quality metrics
- author network generation with influence and community scores
- streaming chat answers grounded in retrieved evidence

## Project Structure

```text
backend/
|- app/
|  |- main.py
|  `- routers/
|     |- chat.py
|     |- cluster.py
|     |- ingest.py
|     |- network.py
|     |- search.py
|     `- timeseries.py
|- core/
|  |- config.py
|  |- embedding_store.py
|  |- mongo.py
|  |- pinecone.py
|  |- schemas.py
|  `- chroma.py
|- ml/
|  |- clusterer.py
|  |- embedder.py
|  |- network_builder.py
|  |- semantic_search.py
|  |- summarizer.py
|  `- tasks.py
|- scripts/
|  |- build_embeddings.py
|  |- migrate_chroma_to_pinecone.py
|  |- seed_mongo.py
|  `- verify_setup.py
|- requirements.txt
|- Dockerfile
|- docker-compose.yml
`- test.py
```

## Architecture Overview

### Primary Data Stores

- MongoDB: source of truth for Reddit posts and lexical filtering
- Pinecone: dense vector index for semantic retrieval
- Mongo embedding backup collection: backup and restore layer for vector data

### Request Flow

1. Requests arrive through FastAPI routers under `/api/...`.
2. MongoDB provides raw post documents, aggregations, and text-search filtering.
3. Pinecone provides dense nearest-neighbor retrieval over title/body embeddings.
4. ML modules in `ml/` compute topics, projections, graph structure, and summaries.
5. Responses are returned to the frontend as typed JSON or SSE streams.

## Startup Behavior

The application lifecycle is managed in `app/main.py`. On startup it:

- warms the sentence-transformer model
- ensures MongoDB indexes exist
- ensures the Pinecone index exists
- checks whether Pinecone already contains vectors
- restores Pinecone from Mongo embedding backups if Pinecone is empty
- otherwise schedules a background embedding build when needed
- seeds Mongo embedding backups from Pinecone if Pinecone already has vectors and Mongo backup is empty
- precomputes the default author-network backbone

This keeps first-use latency lower and makes cold-start environments more recoverable.

## Environment Variables

Create `backend/.env` with the following values:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=reddit_investigator
MONGO_EMBEDDINGS_COLLECTION=post_embeddings

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_pinecone_index_name
PINECONE_INDEX_HOST=your_pinecone_index_host
PINECONE_NAMESPACE=reddit_posts
PINECONE_CLOUD=
PINECONE_REGION=
PINECONE_AUTO_CREATE=false

GEMINI_API_KEY=your_gemini_api_key
CORS_ORIGINS=http://localhost:3000

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384
```

### Notes

- `PINECONE_INDEX_HOST` is required unless you allow auto-creation and host discovery.
- `PINECONE_CLOUD` and `PINECONE_REGION` are only needed when `PINECONE_AUTO_CREATE=true`.
- `CORS_ORIGINS` accepts either a comma-separated string or a JSON array.

## Local Development

### Prerequisites

- Python 3.10+
- MongoDB instance
- Pinecone index credentials
- Gemini API key
- cleaned dataset file downloaded separately

### Install Dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Seed MongoDB

The seeding script expects the dataset at:

`../data/processed/data_cleaned.jsonl`

Run:

```powershell
python scripts/seed_mongo.py
```

This script:

- validates each line against the `PostDocument` schema
- inserts documents into `posts`
- creates indexes for `post_id`, `subreddit`, and multilingual text search

### Verify Setup

```powershell
python scripts/verify_setup.py
```

This checks:

- MongoDB connectivity
- Mongo embedding backup collection
- multilingual text-index configuration
- Pinecone connectivity
- Gemini API access

### Run The API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will then be available at `http://localhost:8000`.

## Docker

### Build

```powershell
docker build -t reddit-investigator-backend .
```

### Run

```powershell
docker run -p 7860:7860 --env-file .env reddit-investigator-backend
```

### Docker Compose

```powershell
docker compose up --build
```

`docker-compose.yml` maps the backend to port `8000` and forwards environment variables into the container.

## Hugging Face Spaces Deployment

This backend is also configured to run on Hugging Face Spaces using the Docker SDK.

### Steps

1. Create a new Space using the **Docker** SDK.
2. Upload the contents of the `backend/` directory to the Space repository root.
3. Add the required secret environment variables in the Space settings.

### Required Secrets

- `MONGO_URI`
- `MONGO_DB`
- `PINECONE_API_KEY`
- `PINECONE_INDEX_NAME`
- `PINECONE_INDEX_HOST`
- `GEMINI_API_KEY`
- optional Pinecone namespace/cloud/region settings

### Container Notes

- The Docker image listens on port `7860`, which matches Hugging Face Spaces expectations.
- The image pre-downloads a sentence-transformer at build time to reduce cold-start latency.
- The Dockerfile currently preloads `sentence-transformers/all-MiniLM-L12-v2`, while runtime config defaults to `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. If you want build-time caching to match runtime exactly, update the Dockerfile accordingly.

## API Routes

### `GET /api/ingest/status`

Returns:

- Mongo document count
- Mongo embedding backup count
- Pinecone vector count
- current embedding task status

### `GET /api/timeseries/`

Returns daily aggregates with optional filters:

- `query`
- `subreddit`
- `from_date`
- `to_date`

### `GET /api/timeseries/analytics`

Returns enriched analytics including:

- daily time series
- subreddit distribution
- weekday distribution
- score buckets
- linear trend model
- anomaly detection output
- daily regime clustering output

### `GET /api/timeseries/summary`

Uses Gemini to generate a plain-language summary over the returned time-series data.

### `POST /api/search/`

Runs semantic search over the vector index. Requires a query string with at least 3 characters.

### `GET /api/clusters/`

Runs BERTopic clustering and returns topic summaries, counts, representations, and representative posts.

### `GET /api/clusters/embeddings`

Returns:

- UMAP 2D coordinates
- cluster labels
- post IDs
- point labels
- point confidences
- projection quality diagnostics

### `GET /api/network`

Builds an author graph with optional parameters:

- `query`
- `graph_type`
- `top_n`
- `max_nodes`

Supported graph types:

- `co_subreddit`
- `crosspost`
- `shared_domain`

### `POST /api/chat/`

Streams a retrieval-augmented answer using Server-Sent Events. The response emits:

- retrieved sources
- streamed answer chunks
- suggested follow-up queries
- error events when generation fails

## ML / Analytics Modules

### `ml/embedder.py`

Loads the configured sentence-transformer model and exposes embedding helpers. The model is cached in-process with `lru_cache`.

### `ml/semantic_search.py`

Implements the main search-page retrieval path:

- embed query
- query Pinecone
- deduplicate chunk hits back to post IDs
- fetch full post documents from Mongo
- resolve some crosspost/reference cases
- return ranked search results

### `ml/summarizer.py`

Handles:

- Gemini-backed time-series summaries
- query expansion for chat
- hybrid dense + lexical retrieval for chat
- BM25 scoring
- reciprocal rank fusion
- final reranking
- prompt construction
- suggested follow-up queries

### `ml/clusterer.py`

Handles:

- BERTopic topic modeling
- UMAP parameter tuning
- 2D embedding projection
- representative-post selection
- projection quality scoring
- in-memory caching
- persisted cache storage in Mongo for default cluster requests

### `ml/network_builder.py`

Builds and caches backbone graphs for:

- co-subreddit author relations
- crosspost author relations
- shared-domain author relations

It also computes:

- PageRank
- Louvain communities
- author profile summaries
- truncated graph responses for large filtered results

### `ml/tasks.py`

Coordinates background embedding tasks and backup/restore flows between Mongo and Pinecone.

## Data Model

The main post schema is defined in `core/schemas.py` as `PostDocument`. Important fields include:

- identifiers: `post_id`, `post_fullname`, `author`, `subreddit`
- timestamps: `created_utc`, `created_datetime`, `created_date`
- text fields: `title_clean`, `selftext_clean`, `combined_text`
- engagement fields: `score`, `num_comments`, `engagement`
- crosspost metadata
- URL and permalink fields

The same module also defines request and response schemas for:

- semantic search
- clusters
- network graphs
- chat
- time-series points

## Embedding and Recovery Pipeline

The backend intentionally stores embedding state in two places:

- Pinecone for active semantic retrieval
- Mongo backup collection for recovery and portability

This enables a few useful flows:

- full rebuild from Mongo posts into Pinecone
- restore Pinecone from Mongo backup if Pinecone is empty
- seed Mongo backup from Pinecone if Mongo backup is empty

That logic is implemented across:

- `core/embedding_store.py`
- `ml/tasks.py`
- `scripts/build_embeddings.py`

## Caching Strategy

The backend uses several cache layers to keep expensive operations responsive:

- embedder model cache
- in-memory BERTopic result cache
- in-memory UMAP config/projection cache
- in-memory network backbone cache
- persisted default cluster results in Mongo
- in-flight task deduplication for clustering and embeddings

This is important because topic modeling and projection generation are relatively expensive compared to ordinary CRUD-style APIs.

## Robustness Notes

The backend includes several practical fallback paths:

- PageRank falls back to weighted degree heuristics if NetworkX PageRank fails
- Louvain falls back to connected components if partitioning fails or the package is unavailable
- BERTopic topic reduction falls back to natural topics if reduction fails
- UMAP parameter tuning falls back to conservative defaults when tuning fails
- vector-store recovery falls back from restore to full rebuild when needed
- time-series anomaly detection and clustering only run when there is enough data
- multilingual Mongo text indexing uses `default_language="none"` to avoid English-only stemming assumptions

## Known Gaps / Notes

- `core/chroma.py` and some function names still mention Chroma for backward compatibility, but the active vector store is Pinecone.
- `app/routers/timeseries.py` includes a placeholder `/topics` route that currently returns an empty list.
- There is no full automated test suite yet; verification is currently script-based and manual.
- The backend assumes the cleaned dataset has already been prepared before ingest.

## Recommended Order Of Operations

For a fresh setup:

1. Create `backend/.env`.
2. Install dependencies.
3. Download the cleaned dataset into `../data/processed/data_cleaned.jsonl`.
4. Run `python scripts/seed_mongo.py`.
5. Run `python scripts/verify_setup.py`.
6. Start the API with Uvicorn.
7. Start the frontend and confirm `/api/ingest/status` reports healthy counts.
