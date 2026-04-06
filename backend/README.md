---
title: Reddit Investigator API
emoji: 🕵️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Reddit Investigator Backend

This is the FastAPI backend for the Reddit Investigator research project. It handles semantic search, topic clustering, network analysis, and AI-powered chat using Gemini.

## Deployment on Hugging Face Spaces

This project is configured to run on Hugging Face Spaces using the Docker SDK.

1.  **Create a New Space**: Select the **Docker** SDK.
2.  **Environment Variables**: Go to Settings and add the following **Secret** variables:
    -   `MONGO_URI`: Your MongoDB Atlas connection string.
    -   `MONGO_DB`: Name of your database (e.g., `reddit_investigator`).
    -   `GEMINI_API_KEY`: Your Google AI Studio API key.
    -   `CHROMA_HOST**: Leave as `localhost` if running Chroma in the same container, or set to an external URL.
3.  **Upload Files**: Upload the contents of this directory to the root of your Space's repository.

## Local Development (Optional)

If you have Docker installed:
```powershell
docker build -t reddit-investigator-backend .
docker run -p 7860:7860 --env-file .env reddit-investigator-backend
```
