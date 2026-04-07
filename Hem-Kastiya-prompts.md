# Hem-Kastiya Prompts

This list contains the major prompts that aided development. Minor or unnecessary prompts have not been listed.

## 1) Data Cleaning

**Prompt:** I have a `data.jsonl` file. Write a script for analyzing the different fields. Include analysis components such as number of null values, unique values, data type, data distribution, etc., for understanding the importance of each feature.

**Notes:** Generated a script that flattened the JSON field headers and each field header was termed as its own column. However, the `data.jsonl` file had plenty of field headers in the format `secure_media.xxxxx.xxxx`, which created unnecessary extra columns, so regex was utilized to properly analyze the data.

## 2) Data Cleaning

**Prompt:** Here's a list of necessary columns which are to be included and others are to be dropped. Write the Python code for cleaning the `data.jsonl` file.

**Notes:** The file generated had a lot of inconsistencies with column name parsing, hence provided a sample of 10 data rows so as to provide the context of the `data.jsonl` file.

## 3) Deciding Key Functionalities

**Prompt:** (Provided evaluation metrics criteria from `INSTRUCTIONS.md`) Suggest me proper algorithms for implementing clustering, embeddings visualization, semantic search, and network visualization.

**Notes:** I was trying to understand different technologies that exist for the said task, hence I asked which technologies are used for the provided tasks.

## 4) Deciding Key Functionalities

**Proposed Structure**

- `app/core`: config, logging, exception handling, dependency wiring.
- `app/db`: Mongo, Chroma, graph loader clients.
- `app/models`: Pydantic request/response + internal domain models.
- `app/repositories`: all data access only (Mongo/Chroma/graph reads/writes).
- `app/services`: business logic only (search, trends, topics, graph resilience, summaries).
- `app/api/routers`: thin FastAPI routes, no business logic.
- `scripts`: offline pipelines (`embed.py`, `build_topics.py`, `build_graph.py`) with shared utilities from `app/`.
- `tests`: unit tests for services/repositories + API integration tests.

**Design Rules (for future-safe extensibility)**

- Routes call services; services call repositories; repositories call external systems.
- No direct DB calls inside routes.
- All cross-module contracts are typed (Pydantic + Protocol-style service interfaces).
- Shared schemas live in one place; no duplicated payload shapes.
- Feature flags/config centralized in settings, not hardcoded.
- Additive changes happen by creating new service/repo modules, not editing unrelated files.

**Initial API Surface**

- `GET /health`
- `POST /search/semantic`
- `GET /trends/timeseries`
- `GET /topics/distribution`
- `GET /network/subgraph`
- `POST /network/remove-central-node-simulate`
- `POST /summaries/timeseries`

**Build Order**

- Skeleton + config + dependency injection.
- Semantic search vertical slice end-to-end (query embed -> Chroma -> Mongo hydrate).
- Time-series + dynamic AI summary with caching and fallback.
- Network endpoints with centrality/removal simulation.
- Topic endpoints + metadata.
- Tests, docs, and startup checks.

**Prompt:** This is the structure I have thought upon. Analyze possible flaws in the design and report back to me. Even my self studying could lack something that I am not aware of.

## 5) Deciding Key Functionalities

**Prompt:** Provide the full backend file structure from everything we have discussed so far. List all of the usages for each of the module, what each file does, etc. Also provide the implementation plan details for the same.

**Notes:** Reviewed the architecture proposed by it, ensuring it is not adding more files than necessary. Read about what each file does so as to verify that the file is doing what it is intended to do.

## 6) Deciding Key Functionalities

**Prompt:** Alright now let's do the same implementation for frontend. Provide me the details in the same format that you have provided for backend.

**Notes:** Same thing as previous point.

## 7) Building the First Prototype

**Prompt:** Provided the previously generated answers to Codex to start working on building the prototypes.

**Notes:** Fast building the proposed plan.

## 8) Building the First Prototype

**Prompt:** Add `__init__` files in all directories of backend, you haven't done it and will lead to module import errors in the future.

**Notes:** The `__init__` file had been generated but it was empty, this would lead to errors when cross module imports happen.

## 8) Building the First Prototype

**Prompt:** Provide me with the setup steps that I need to perform. Where will I get all the environment variables and all?

**Notes:** Ensuring no API key gets missed so as to not encounter any errors. Moreover, I didn't remember the `uvicorn` server start commands so couldn't start the `uvicorn` server.

## 9) Frontend UI

**Prompt:** The current UI looks very generic. I want to make the UI look similar to a newspaper page, ensure proper tabs for all tasks. Implement proper error handling and loading screens. Moreover, the UI should be responsive, it shouldn't break for edge case or null responses and actively handle it. Layout the file structure, design plan, implementation plan, etc., for it. The usage of styling framework should be done on the basis that is very easy to modify and change when needed.

**Notes:** Provided the prompt as it didn't implement any of the proper error handling, etc., functionalities in the frontend.

## 10) Frontend UI

**Prompt:** Frontend done, it's working. However, the current issue that is being faced is too much load time for embeddings, analysis, network graph, etc. Also searching on network graph doesn't get any results, it's always an empty graph despite all queries, seems it needs to be handled. Clustering takes so much time that it hits the maximum timeout limit set.

**Notes:** After the prompt did I realize that the backend code had a lot of bugs, the issue was not of frontend, hence I started looking and fixing the backend issue.

## 11) Backend Server

**Prompt:** Implement `asyncio` for handling asynchronous requests. The entirety of current architecture is utilizing synchronous functions which is blocking other frontend calls even when the user has switched to another tab.

**Notes:** Upon reading the backend functions, I found that all of them were synchronous, which meant they would be executed in the order called even if their results could wait until end.

## 12) RAG Chatbot Improvement

**Prompt:** The current RAG pipeline is generating very bad responses, filled with hallucinations and noise. Sources are randomly getting cited. Possible improvements that can be done on it.

**Notes:** I knew I hadn't implemented proper embedding chunking and all, but also decided to explore other options to improve the pipeline.

## 13) Networking Graph Improvement

**Prompt:** Currently the network visualization interface is really bad. The search doesn't work, the entire graph renders, and it almost always throws timeout errors. Moreover don't render the whole graph as default, rather just keep heavily connected nodes precomputed for default. When the user searches a keyword, it should create a graph for that. I want the option to view different types of graph connections be made available to the user. Moreover, the parameters that the user changes like removing nodes, manipulating edge weights should be just reflected on the frontend, no need to make unnecessary calls to the backend to slow things down.

**Notes:** The networking graph had serious flaws in its implementation. It constituted rendering the whole graph of all records even if they were isolated nodes, which caused UI breaks and unnecessary latency.

## 14) 2D UMAP Improvement

**Prompt:** Implement the following for improving upon 2D UMAP projections. Stop truncating legend to 8 clusters in `ScatterPlot.tsx`, or make it scrollable. Robustness fixes: guard against `n_clusters=2` instability by raising UI minimum to 3 in `page.tsx` and/or backend fallback handling in `cluster.py` and `clusterer.py`. Quality upgrades: tune UMAP (`n_neighbors`, `min_dist`) with objective metrics (trustworthiness + kNN overlap), not by visual feel. Improve the color contrast of clusters in `scatterplot.tsx`, currently the palette is very hard to differentiate.

**Notes:** Added outliers and everything along with confidence score in each cluster to ensure it conveys proper meaning.

## 15) Cluster Improvement

**Prompt:** The current cluster code calls embeddings every single time when the API gets called, leading to unnecessary delays. I have already stored embeddings in ChromaDB and MongoDB. Use these precomputed edges rather than recomputation. Also add default cluster storing to quickly fetch the default results rather than recomputation on first call. Add percentage of data records falling into that cluster, highlight major keywords, remove stop words, compute clusters only on parameter change, provide highest confidence scoring posts in each cluster.

**Notes** The cluster.py lagged major features that stopped it from performing as intended.

## 16) Semantic Search Improvement

**Prompt:** Search API returns backend `PostDocument` shape (`post_id`, `title_clean`, `created_utc` as float), but frontend search UI expects `id`, `title`, `created_utc` string. Prioritize those posts that have their own self-text rather than the ones that reference other posts. If a post references a post or has no self text, provide the referenced post.

**Notes** The semantic searched results were returned in no particular format often having no selftext posts above the ones that were the original posts.

## 17) Timeseries Improvement

**Prompt:** The frontend has many lagging issues. Currently it only implements time series analytics. I want many other algorithms implemented into it like isolation forest, KMeans, etc. Provide various fields so the user gets to change the analysis showed. Also add key guide so any non tech person understands what each field denotes.

**Notes:** Did the above thing to provide better analytics of the dataset.

## 18) Frontend Caching

**Prompt:** Cache the results into frontend browser to avoid sending API calls if the cached result exists.

**Notes:** Added time expiry of 5 mins from creation to not occupy unnecessary storage. Only cached the latest response to avoid exceeding browser storage limits.

## 19) Embedding Model Migration to Achieve Multi-Lingual Support

**Prompt:** Migrate the current embedding model to another that supports multi-language support.

**Notes:** I realized that the selected model only supported English queries and failed when it encountered other language queries.

## 20) Deployment Guide

**Prompt:** Provide deployment steps for both frontend and backend. Since the backend is quite heavy, provide list of free tier backend server platforms.

**Notes:** I had ChromaDB as a self-hosted service as well as the backend performed quite a few heavy options, which meant it may get problems on many free platforms like Render.

## 21) Migration of ChromaDB to PineconeDB

**Prompt:** Migrate the entire implementation of ChromaDB to PineconeDB.

**Notes:** Did this because I faced a lot of problems deploying the ChromaDB server. However, I knew that it may forget a router or two to change so I kept a deprecated `Chroma.py` file that rerouted any requests to Pinecone if it did encounter. Didn't have time to go and verify as deadline was near. Not clean but a temporary fix.

## 22) Note

This list consists of major prompts that aided in development. Other prompts which were minor or unnecessary have not been listed.
