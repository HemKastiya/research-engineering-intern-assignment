# The Daily Query

An investigative Reddit intelligence dashboard for semantic search, time-series analysis, topic clustering, embedding exploration, network analysis, and retrieval-augmented chat.

This repository is a full-stack submission for the SimPPL Research Engineering Intern assignment. It turns a cleaned Reddit corpus into an interactive research surface designed for exploratory analysis rather than static reporting. The product theme is a digital newspaper: each section focuses on a different way to understand how narratives travel through the dataset.

## Submission Links

- Live dashboard: `https://the-daily-query.vercel.app/`
- Demo video: `https://drive.google.com/file/d/1An0UQmuWUH6t1_Ykbd6LjLSdNSeQMbED/view?usp=drive_link`
- Prompt log: `Hem-Kastiya-prompts.md`
- Dataset source: `Same as the one provided in INSTRUCTIONS.md`

## Screenshots

```md

```

## Project Summary

The system supports six main research workflows:

1. Track posting volume and engagement over time, with statistical overlays and an LLM-written plain-language summary.
2. Search posts semantically, so relevant results can still surface even when the query does not share exact keywords with the post.
3. Cluster posts into topics and expose the number of clusters as a user-controlled parameter.
4. Visualize the embedding space as an interactive UMAP projection with projection-quality diagnostics.
5. Build author interaction graphs and rank influential actors with PageRank and community detection.
6. Ask natural-language questions against the corpus using a streaming RAG interface with cited source posts and suggested follow-up questions.

## What Is In This Repo

```text
research-engineering-intern-assignment/
|- README.md
|- INSTRUCTIONS.md
|- PRO-TIPS.md
|- backend/
|  |- app/
|  |  |- main.py
|  |  |- routers/
|  |- core/
|  |- ml/
|  |- scripts/
|  |- requirements.txt
|  |- Dockerfile
|  |- docker-compose.yml
|  |- README.md
|  `- test.py
`- frontend/
   |- src/app/
   |- components/
   |- lib/
   |- types/
   |- package.json
   `- next.config.ts
```

## System Architecture

### Frontend

- Framework: Next.js 16 + React 19 + TypeScript
- Styling: custom editorial design system in Tailwind CSS
- Charts: Recharts + D3
- Network graph rendering: Sigma.js via `@react-sigma/core`
- Data fetching: custom fetch wrapper with timeout handling and session/memory caching

### Backend

- Framework: FastAPI
- Database: MongoDB for post storage and lexical filtering
- Vector store: Pinecone for semantic retrieval
- LLM provider: Gemini 2.5 Flash for time-series summaries and RAG answers
- Embedding model: multilingual MiniLM sentence-transformer

### Storage and Processing Flow

1. Cleaned Reddit posts are loaded into MongoDB.
2. Title and body chunks are embedded and upserted into Pinecone.
3. The same embeddings are also backed up to MongoDB for restore/bootstrap flows.
4. FastAPI serves analytics, search, clustering, network, and chat endpoints.
5. The Next.js frontend renders a newspaper-style dashboard on top of those APIs.

## Key Features

### 1. Overview Dashboard

The landing page gives a quick operational snapshot of the corpus:

- Mongo document count
- vector count / indexing state
- first-look time-series chart
- navigation into deeper analysis modules

### 2. Time-Series Analytics

The `/timeseries` page supports:

- keyword filtering
- subreddit filtering
- date-range filtering
- daily post volume
- average score and engagement over time
- subreddit share and weekday activity
- score bucket distributions
- anomaly detection
- regime clustering of days
- 7-day projection
- an LLM-generated plain-language summary for non-technical readers

### 3. Semantic Search

The `/search` page is built for meaning-based retrieval rather than plain keyword lookup. It returns ranked results, handles empty results gracefully, and exposes a simple search-first workflow for exploratory investigation.

### 4. Network Analysis

The `/network` page builds interactive author graphs with:

- multiple graph types
- server-side backbone pruning
- PageRank-based influence scoring
- community labels
- client-side node removal to test graph robustness
- edge-weight and degree filtering

Supported graph modes:

- `co_subreddit`: authors connected when they post in the same subreddits
- `crosspost`: directed edges from original authors to reposters
- `shared_domain`: authors connected when they share the same external domains

### 5. Topic Clustering

The `/clusters` page exposes BERTopic-based topic modeling with a tunable topic-count slider, cluster summaries, top terms, and representative posts per topic.

### 6. Embedding Visualization

The `/embeddings` page projects post embeddings to 2D with UMAP and allows interactive exploration of:

- cluster assignments
- outliers
- point labels
- projection trustworthiness and neighborhood-overlap diagnostics

### 7. Retrieval-Augmented Chat

The `/chat` page provides a streaming question-answering interface over the dataset with:

- hybrid retrieval
- source post panel
- streaming Gemini responses
- suggested follow-up questions
- multilingual query support

## Dashboard Walkthrough

### Overview

Use this page to confirm that the corpus has been seeded and embedded correctly before opening the heavier ML workflows.

### Time Series

This section is the best starting point for narrative discovery. It helps answer questions like:

- When did a topic spike?
- Was engagement rising faster than volume?
- Were certain days statistically unusual?
- Do the daily patterns break into distinct behavioral regimes?

### Search

This module is useful when the user already has a concept, event, or narrative in mind and wants semantically related posts without manually crafting Boolean keyword queries.

### Network

This module focuses on actor relationships rather than post content. It helps identify influential users, graph structure, community partitions, and what happens when central nodes are removed.

### Clusters + Embeddings

These two pages work together:

- `/clusters` explains what the topics are
- `/embeddings` shows how those topics are arranged in semantic space

### Chat

This page is the fastest way to ask broad investigative questions and receive a synthesized answer backed by retrieved evidence.

## Data Expectations

The backend seeding script expects a cleaned JSONL dataset at:

`data/processed/data_cleaned.jsonl`

Each document is validated against the `PostDocument` schema and includes fields such as:

- `post_id`, `author`, `subreddit`
- `created_utc`, `created_date`, `created_datetime`
- `title_clean`, `selftext_clean`, `combined_text`
- `score`, `num_comments`, `engagement`
- crosspost metadata
- permalink / full permalink

Note: the data directory is not committed in this repo, so you need to download the dataset separately from the assignment link above.

## Local Setup

### Prerequisites

- Python 3.10+
- Node.js 20+
- MongoDB
- Pinecone account and index credentials
- Gemini API key

### Backend Environment Variables

Create `backend/.env` with values like:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=reddit_investigator
MONGO_EMBEDDINGS_COLLECTION=post_embeddings

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name
PINECONE_INDEX_HOST=your_index_host
PINECONE_NAMESPACE=reddit_posts
PINECONE_CLOUD=
PINECONE_REGION=
PINECONE_AUTO_CREATE=false

GEMINI_API_KEY=your_gemini_api_key
CORS_ORIGINS=http://localhost:3000

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384
```

### Frontend Environment Variables

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running The Project Locally

### 1. Install Backend Dependencies

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Seed MongoDB

Place the cleaned JSONL file at `data/processed/data_cleaned.jsonl`, then run:

```powershell
cd backend
python scripts/seed_mongo.py
```

### 3. Verify External Services

```powershell
cd backend
python scripts/verify_setup.py
```

This script checks:

- MongoDB connectivity
- Mongo embedding backup collection
- Pinecone connectivity
- Gemini API access
- multilingual Mongo text index setup

### 4. Start The Backend

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On startup, the API will:

- warm the embedding model
- ensure Mongo indexes exist
- ensure the Pinecone index exists
- restore Pinecone from Mongo embedding backup if possible
- otherwise schedule a full embedding rebuild
- precompute the default network backbone

### 5. Start The Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## API Surface

### Ingest

- `GET /api/ingest/status`: document counts, vector counts, and embedding status

### Time Series

- `GET /api/timeseries/`: daily aggregates
- `GET /api/timeseries/analytics`: enriched analytics payload
- `GET /api/timeseries/summary`: Gemini-written plain-language summary

### Search

- `POST /api/search/`: semantic retrieval over the vector index

### Clusters

- `GET /api/clusters/`: BERTopic topics
- `GET /api/clusters/embeddings`: 2D embedding projection and cluster labels

### Network

- `GET /api/network`: author graph payload

### Chat

- `POST /api/chat/`: streaming RAG response with sources and suggested queries

## AI / ML Components

Below is a concise implementation summary, aligned with the assignment instructions.

| Component | Model / Algorithm | Key Parameters | Library / API |
| --- | --- | --- | --- |
| Multilingual embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 dimensions; title/body chunking; cosine retrieval | `SentenceTransformer(...)` via `sentence-transformers` |
| Semantic retrieval | Dense vector search in Pinecone | `top_k` over chunk embeddings; namespace-based querying | Pinecone Python SDK |
| Hybrid lexical retrieval for chat | Mongo text search + custom BM25 scoring | `BM25_K1=1.5`, `BM25_B=0.75` | MongoDB text index + custom scorer |
| Rank fusion for chat | Reciprocal Rank Fusion | `RRF_K=60`, `HYBRID_TOP_K=30` | custom Python |
| Final reranking for chat | Weighted heuristic reranker | `RERANK_TOP_K=8`; dense, BM25, hybrid, overlap, phrase, title boosts | custom Python |
| Chat generation | Gemini 2.5 Flash | source-grounded prompt; streaming output | `google.generativeai.GenerativeModel("gemini-2.5-flash")` |
| Time-series summary | Gemini 2.5 Flash | summary over returned daily aggregates | `generate_content(...)` |
| Trend detection | Linear Regression | slope threshold: `> 0.05` upward, `< -0.05` downward | `sklearn.linear_model.LinearRegression` |
| Anomaly detection | Isolation Forest | contamination bounded between `0.05` and `0.18` | `sklearn.ensemble.IsolationForest` |
| Daily regime clustering | KMeans | `n_clusters = min(4, max(2, len(time_series)//25 + 2))` | `sklearn.cluster.KMeans` |
| Topic modeling | BERTopic | UMAP 5D + HDBSCAN + c-TF-IDF; topic reduction to requested count when possible | `BERTopic` |
| BERTopic UMAP config | UMAP | cosine metric; `n_components=5`; auto-tuned `n_neighbors` / `min_dist` | `umap-learn` |
| BERTopic density model | HDBSCAN | `min_cluster_size=max(15, min(25, n_posts//400))`; `cluster_selection_method="eom"` | `hdbscan` |
| Topic term extraction | CountVectorizer + c-TF-IDF | `ngram_range=(1,2)`, `min_df=2`, `max_df=0.9` | scikit-learn + BERTopic |
| Embedding projection | UMAP 2D | candidate grid: `(10,0.0)`, `(15,0.0)`, `(30,0.05)`, `(45,0.1)` | `umap-learn` |
| Projection quality scoring | Trustworthiness + kNN overlap | `k=15` sample-based tuning | scikit-learn + custom metric |
| Influence scoring | PageRank | damping `alpha=0.85` | NetworkX |
| Community detection | Louvain | weighted partitioning with connected-component fallback | `python-louvain` |

## How Semantic Search Works

The repository uses two slightly different retrieval paths:

### Search Page

- embeds the user query with MiniLM
- queries Pinecone for similar title/body chunks
- deduplicates chunk hits back to post IDs
- resolves some crosspost/reference cases to the underlying post
- returns ranked posts with relevance scores

### Chat Page

- expands the query
- runs dense retrieval and lexical retrieval in parallel
- scores lexical candidates with BM25
- fuses rankings with reciprocal rank fusion
- reranks the top candidates
- builds a structured context block
- prompts Gemini to answer only from retrieved evidence
- streams the answer plus suggested follow-up questions

## Network Analysis Design

The network subsystem is intentionally designed to stay responsive on larger corpora:

- a backbone graph is precomputed at startup
- authors are ranked by PageRank and posting activity
- the response graph is induced from backbone nodes
- keyword filtering is applied through Mongo text search
- large keyword-matched subgraphs can be truncated to the top PageRank nodes
- the frontend recomputes PageRank client-side after node removal or edge filtering

This makes it possible to test graph resilience, including the edge case called out in the assignment: removing a highly connected node without crashing the visualization.

## Robustness / Edge-Case Handling

The codebase includes several practical safeguards:

- empty semantic search returns an empty array instead of failing
- empty chat queries produce an empty-context response path
- multilingual lexical matching is supported by a Mongo text index with `default_language="none"`
- the backend restores Pinecone from Mongo embedding backups when possible
- if Pinecone is empty on startup, background embedding generation is scheduled automatically
- BERTopic topic reduction falls back to natural topics if reduction fails
- PageRank falls back to a degree-based approximation if NetworkX PageRank errors
- Louvain falls back to connected components if partitioning is unavailable
- UMAP falls back to conservative defaults if tuned parameters fail
- time-series anomaly detection and clustering disable themselves on too-small datasets instead of forcing unstable models

## Known Gaps And Practical Notes

- `backend/app/routers/timeseries.py` includes a placeholder `/topics` endpoint that is not yet implemented.
- The data file itself is not checked into the repository.
- There is no full automated test suite yet; current verification is primarily via `verify_setup.py`, `test.py`, and manual UI testing.
- Some older names still reference Chroma for backward compatibility, but the active vector store implementation is Pinecone.

## Semantic Search Evaluation Examples

The assignment asks for three README examples showing semantic search behavior with zero keyword overlap. 

| Query | Returned result | Why it is correct |
| --- | --- | --- |
| `Books` | `Book recs :By u/maiinmay: 12 Nov 2024` | `The post talks about how the user came across a book title, hence the underlying meaning of books was captured.` |
| `Songs on trend` | `What kind of music you been into lately?: By u/Lil_Peachy_Fox: 18 Dec 2024` | `The post inquires about the current taste of music in the subreddit.` |
| `वर्तमान अर्थव्यवस्था की स्थिति` | `A quick recap of the New Economy: By u/AgentR-gov: 12 Feb 2025` | `It may not directly related to present, but the meaning of new has been associated with present.` |

## License
This project is assigned as part of the SimPPL research engineering assignment.
