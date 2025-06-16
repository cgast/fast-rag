#!/usr/bin/env python3
import asyncio
import os
import time
from fast_rag import FastRAG, load_env

async def test_cache_strategies():
    load_env()
    
    serper_key = os.getenv('SERPER_API_KEY')
    firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
    jina_key = os.getenv('JINA_API_KEY')
    cohere_key = os.getenv('COHERE_API_KEY')
    
    if not serper_key or not firecrawl_key:
        print("Set SERPER_API_KEY and FIRECRAWL_API_KEY")
        return
    
    query = "What is machine learning?"
    print(f"Testing cache strategies for: {query}\n")
    
    # Test different cache ages
    strategies = [
        ("No Cache", 0),
        ("5 minutes", 300000),
        ("30 minutes", 1800000), 
        ("1 hour", 3600000),
        ("1 day", 86400000)
    ]
    
    results = []
    
    for name, max_age in strategies:
        print(f"🧪 Testing {name} (maxAge: {max_age}ms)")
        
        rag = FastRAG(serper_key, firecrawl_key, jina_key, cohere_key, max_age=max_age)
        
        start_time = time.time()
        result = await rag.process(query)
        total_time = time.time() - start_time
        
        results.append({
            'strategy': name,
            'max_age': max_age,
            'total_time': total_time,
            'scrape_time': result['timing']['scrape'],
            'sources': result['sources'],
            'chunks': result['chunks']
        })
        
        print(f"  ✅ Total: {total_time:.1f}s | Scrape: {result['timing']['scrape']:.1f}s")
        print(f"  📊 {result['sources']} sources, {result['chunks']} chunks\n")
    
    # Summary
    print("=" * 60)
    print("📈 CACHE STRATEGY COMPARISON")
    print("=" * 60)
    print(f"{'Strategy':<12} {'MaxAge':<8} {'Total':<8} {'Scrape':<8} {'Sources':<8}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['strategy']:<12} {r['max_age']:<8} {r['total_time']:<7.1f}s {r['scrape_time']:<7.1f}s {r['sources']:<8}")
    
    # Find fastest
    fastest = min(results, key=lambda x: x['total_time'])
    print(f"\n🏆 Fastest: {fastest['strategy']} ({fastest['total_time']:.1f}s)")
    
    # Cache hit analysis
    no_cache_time = results[0]['scrape_time']
    print(f"\n⚡ Speed Improvements vs No Cache:")
    for r in results[1:]:
        if r['scrape_time'] < no_cache_time:
            improvement = ((no_cache_time - r['scrape_time']) / no_cache_time) * 100
            print(f"  {r['strategy']}: {improvement:.0f}% faster")
        else:
            print(f"  {r['strategy']}: No cache benefit")

if __name__ == "__main__":
    asyncio.run(test_cache_strategies())