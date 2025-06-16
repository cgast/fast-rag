# Fast RAG - Ultra Minimal

Get web context for your LLM in 3 seconds using only external APIs.

## Install
```bash
pip install aiohttp requests
```

## Setup
```bash
# Copy the template and add your keys
cp .env.example .env

# Edit .env with your API keys:
# SERPER_API_KEY=your_key_from_serper.dev
# FIRECRAWL_API_KEY=your_key_from_firecrawl.dev  
# JINA_API_KEY=your_key_from_jina.ai
# COHERE_API_KEY=your_key_from_cohere.ai
```

## Use
```bash
python simple_cli.py "What is quantum computing?"
```

## Python
```python
from fast_rag import FastRAG
import asyncio

async def main():
    rag = FastRAG(serper_key, firecrawl_key, jina_key)
    result = await rag.process("your query")
    print(result['context'])

asyncio.run(main())
```

That's it. 150 lines of code, 2 dependencies, 3 second results.