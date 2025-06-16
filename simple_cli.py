#!/usr/bin/env python3
import asyncio
import sys
import os
from fast_rag import FastRAG, load_env

async def main():
    load_env()

    if len(sys.argv) < 2:
        print("Usage: python simple_cli.py 'your query here'")
        return

    query = sys.argv[1]
    serper_key = os.getenv('SERPER_API_KEY')
    firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
    jina_key = os.getenv('JINA_API_KEY')
    cohere_key = os.getenv('COHERE_API_KEY')

    if not serper_key or not firecrawl_key:
        print("Set SERPER_API_KEY and FIRECRAWL_API_KEY")
        return

    # Use 30 minute cache for faster results (1800000 ms)
    rag = FastRAG(serper_key, firecrawl_key, jina_key, cohere_key, max_age=1800000)
    result = await rag.process(query)

    # Show timing breakdown
    timing = result['timing']
    print("\n⚡ Fast Results with 30min Cache (maxAge: 1800000ms)")
    print("\n⏱️  Timing Breakdown:")
    print(f"  Search:  {timing['search']:.1f}s")
    print(f"  Scrape:  {timing['scrape']:.1f}s (using Firecrawl cache)")
    print(f"  Chunk:   {timing['chunk']:.1f}s")
    print(f"  Format:  {timing['format']:.1f}s")
    print(f"  Total:   {timing['total']:.1f}s")
    print("\n" + "="*50)
    print(result['context'])

if __name__ == "__main__":
    asyncio.run(main())
