import asyncio
from ml.semantic_search import search
results = asyncio.run(search("economic hardship", top_k=5, filters={}))
print(results)