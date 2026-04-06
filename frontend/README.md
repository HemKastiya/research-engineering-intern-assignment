# Frontend README

This directory contains the Next.js frontend for **The Daily Query**, a newspaper-style Reddit research dashboard. It is responsible for the full user experience of the project: the editorial shell, navigation, charts, network visualization, cluster exploration, embedding scatterplot, and streaming RAG chat interface.

## Stack

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS v4
- Recharts for analytics charts
- D3 for the embedding scatterplot
- Sigma.js via `@react-sigma/core` for the network graph
- SWR-compatible fetch patterns through a custom API client

## What This Frontend Does

The app turns backend analytics endpoints into a browsable investigation workflow:

- `/`: overview and corpus health snapshot
- `/timeseries`: trend analysis, anomaly detection, forecasting, and narrative summary
- `/search`: semantic search results
- `/network`: interactive author graph analysis
- `/clusters`: BERTopic topic explorer
- `/embeddings`: 2D UMAP embedding projection
- `/chat`: streaming question answering with retrieved sources

## Project Structure

```text
frontend/
|- src/app/
|  |- layout.tsx
|  |- page.tsx
|  |- chat/page.tsx
|  |- clusters/page.tsx
|  |- embeddings/page.tsx
|  |- network/page.tsx
|  |- search/page.tsx
|  `- timeseries/page.tsx
|- components/
|  |- chat/
|  |- charts/
|  |- clusters/
|  |- layout/
|  |- network/
|  `- ui/
|- lib/
|  |- api.ts
|  |- network.ts
|  |- tokens.ts
|  `- utils.ts
|- types/
|  `- index.ts
|- package.json
|- next.config.ts
`- src/app/globals.css
```

## Design Direction

The UI intentionally avoids a generic dashboard look. The visual system is built around a broadsheet/newsroom metaphor:

- a masthead-style header
- tabbed sections like newspaper columns
- serif-forward typography
- warm paper-toned backgrounds
- ink, rule, and accent color tokens
- border-led layout instead of card-heavy SaaS styling

Core design tokens live in `lib/tokens.ts`, while most of the visual system is implemented in `src/app/globals.css`.

## Key Architectural Pieces

### App Shell

`src/app/layout.tsx` provides the shared frame for the application:

- ingest status banner
- masthead
- sticky section tabs
- page content container

### API Client

`lib/api.ts` is the main integration layer with the backend. It provides:

- typed fetch helpers
- request timeouts
- in-memory and session-storage caching for GET requests
- API error normalization
- SSE chat streaming support

### Network Graph

The network page uses a dynamic import for the Sigma renderer so it only runs on the client. The frontend also recomputes PageRank locally after graph filtering or node removal via `lib/network.ts`.

### Embedding Scatterplot

The embeddings page uses D3 to render a pannable, zoomable scatterplot with:

- cluster-based coloring
- outlier handling
- hover tooltips
- confidence-aware point opacity

### Chat UX

The chat page streams tokens from the backend, updates sources as they arrive, and renders suggested follow-up queries after the answer completes.

## Environment Variables

You can run the frontend in two useful modes.

### Option 1: Explicit API base URL

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In this mode, the browser talks directly to the backend.

### Option 2: Use Next.js dev rewrites

If `NEXT_PUBLIC_API_URL` is omitted, the frontend falls back to same-origin `/api/...` requests. In development, `next.config.ts` rewrites those calls to:

```env
LOCAL_API_ORIGIN=http://localhost:8000
```

This is convenient when you want the browser to stay on one origin during local development.

## Local Development

### Prerequisites

- Node.js 20+
- running backend API

### Install Dependencies

```powershell
npm install
```

### Start Development Server

```powershell
npm run dev
```

The app will usually be available at `http://localhost:3000`.

### Production Build

```powershell
npm run build
npm run start
```

### Lint

```powershell
npm run lint
```

## Available Scripts

Defined in `package.json`:

- `npm run dev`: start local Next.js development server
- `npm run build`: build the production app
- `npm run start`: serve the production build
- `npm run lint`: run ESLint

## Page-by-Page Overview

### `/`

The overview page combines ingest status and a lightweight time-series preview. It is meant to answer a simple first question: is the corpus loaded and ready for deeper analysis?

### `/timeseries`

This is the richest analytics page in the frontend. Users can filter by:

- query
- subreddit
- start date
- end date

The page then presents:

- multiple chart modes
- trend statistics
- anomalies
- daily regime clusters
- 7-day projections
- an AI-generated plain-language summary

### `/search`

This page offers a minimal semantic search experience with:

- example queries
- ranked post cards
- loading and empty states
- graceful error handling

### `/network`

This page provides:

- keyword filtering
- graph-type switching
- edge-weight filtering
- minimum-degree filtering
- node removal experiments
- sidebar inspection of selected authors

### `/clusters`

This page exposes topic count as a tunable parameter and lets users inspect:

- cluster sizes
- top terms
- representative posts

### `/embeddings`

This page visualizes the semantic space and surfaces projection quality signals such as:

- trustworthiness
- k-nearest-neighbor overlap
- outlier ratio
- tuned UMAP parameters

### `/chat`

This page is the highest-level interaction mode. It combines:

- conversational input
- streaming answers
- source previews
- follow-up suggestions

## Components

The component hierarchy is split by feature area:

- `components/layout`: masthead, nav tabs, ingest banner
- `components/ui`: reusable cards, badges, skeletons, and shared UI primitives
- `components/charts`: chart renderers for time series and analytics views
- `components/network`: graph controls, renderer, and node sidebar
- `components/clusters`: cluster list, cards, and topic slider
- `components/chat`: chat window, input, message rendering, sources, and suggestions

This keeps feature-specific logic near the UI that uses it while preserving a small shared primitives layer.

## Type Safety

Shared API response shapes live in `types/index.ts`. The frontend depends on these types for:

- search results
- time-series analytics
- cluster payloads
- graph payloads
- ingest status
- chat messages

This makes page logic and component props more predictable when backend payloads evolve.

## UX and Resilience Notes

The frontend already includes several user-facing safeguards:

- loading skeletons on async views
- explicit empty states for no-result conditions
- retry affordances on failures
- debounced search/filter inputs where appropriate
- client-only loading for graph-heavy visualizations
- polling-based ingest banner when embeddings are still being built

Some heavier pages also warn implicitly through the UI that first load may take longer because backend ML jobs are more expensive.

## Backend Contract

This frontend expects the backend routes below to be available:

- `GET /api/ingest/status`
- `GET /api/timeseries/`
- `GET /api/timeseries/analytics`
- `GET /api/timeseries/summary`
- `POST /api/search/`
- `GET /api/clusters/`
- `GET /api/clusters/embeddings`
- `GET /api/network`
- `POST /api/chat/`

If these routes change, update `lib/api.ts` first.

## Notable Implementation Details

### Development Proxy Behavior

The development rewrite in `next.config.ts` only applies outside production. That means production deployments should set `NEXT_PUBLIC_API_URL` explicitly unless the frontend and backend are served from the same origin.

### Client Components

Most page modules are client components because they depend on:

- interactive controls
- browser APIs
- chart libraries
- incremental fetch behavior
- streaming updates

### Dynamic Imports

The network graph and scatterplot-heavy visualizations are loaded client-side to avoid SSR issues with browser-only graphing libraries.

## If You Need To Extend It

Good places to add new work:

- new API integrations: `lib/api.ts`
- new routes/pages: `src/app/...`
- reusable visual patterns: `components/ui`
- shared chart patterns: `components/charts`
- new design tokens: `lib/tokens.ts` and `src/app/globals.css`

## Notes

- This directory does not run meaningfully by itself unless the backend API is reachable.
- The UI is optimized around the existing FastAPI contract rather than mocked local data.
- The editorial styling is deliberate and central to the project identity, so future changes should preserve that visual language unless there is a strong product reason to change it.
