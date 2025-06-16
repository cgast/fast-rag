import asyncio
import aiohttp
import os
import time

def load_env():
    """Load .env file if it exists"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

class FastRAG:
    def __init__(self, serper_key, firecrawl_key, jina_key=None, cohere_key=None, max_age=3600000):
        self.serper_key = serper_key
        self.firecrawl_key = firecrawl_key
        self.jina_key = jina_key
        self.cohere_key = cohere_key
        self.max_age = max_age  # Default 1 hour cache

    async def search(self, query, num_results=5):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': self.serper_key, 'Content-Type': 'application/json'},
                json={'q': query, 'num': num_results}
            ) as response:
                data = await response.json()
                return [{'title': item.get('title', ''), 'url': item.get('link', ''), 'snippet': item.get('snippet', '')}
                       for item in data.get('organic', [])]

    async def scrape(self, urls):
        results = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.post(
                        'https://api.firecrawl.dev/v0/scrape',
                        headers={'Authorization': f'Bearer {self.firecrawl_key}', 'Content-Type': 'application/json'},
                        json={'url': url, 'formats': ['markdown'], 'onlyMainContent': True, 'maxAge': self.max_age}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data.get('data', {}).get('markdown', '')
                            if content:
                                results.append({'url': url, 'content': content})
                except Exception as e:
                    print(f"Error scraping {url}: {e}")
        return results

    def chunk(self, content, size=1000):
        text = content.strip()
        if len(text) <= size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + size
            if end < len(text):
                # Find sentence boundary
                for punct in ['. ', '! ', '? ']:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct > start + size//2:
                        end = last_punct + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - 50  # Small overlap

        return chunks

    async def rerank(self, query, chunks, top_k=5):
        if not chunks:
            return []

        rerank_start = time.time()

        # Try Cohere first (it's working better)
        if self.cohere_key:
            cohere_start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        'https://api.cohere.ai/v1/rerank',
                        headers={'Authorization': f'Bearer {self.cohere_key}', 'Content-Type': 'application/json'},
                        json={
                            'model': 'rerank-english-v3.0',
                            'query': query,
                            'documents': chunks,
                            'top_k': min(top_k, len(chunks))
                        }
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            ranked = []
                            for result in data.get('results', []):
                                ranked.append({
                                    'content': chunks[result['index']],
                                    'score': result['relevance_score']
                                })
                            if ranked:
                                cohere_time = time.time() - cohere_start
                                print(f"✅ Cohere reranking successful ({cohere_time:.1f}s)")
                                return ranked
                        else:
                            print(f"Cohere API error: {response.status}, trying Jina...")
            except Exception as e:
                print(f"Cohere error: {e}, trying Jina...")

        # Fallback to Jina
        if self.jina_key:
            jina_start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        'https://api.jina.ai/v1/rerank',
                        headers={'Authorization': f'Bearer {self.jina_key}', 'Content-Type': 'application/json'},
                        json={'query': query, 'documents': chunks, 'top_k': min(top_k, len(chunks))}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            ranked = []
                            for result in data.get('results', []):
                                ranked.append({
                                    'content': chunks[result['index']],
                                    'score': result['relevance_score']
                                })
                            if ranked:
                                jina_time = time.time() - jina_start
                                print(f"✅ Jina reranking successful ({jina_time:.1f}s)")
                                return ranked
                        else:
                            print(f"Jina API error: {response.status}")
            except Exception as e:
                print(f"Jina error: {e}")

        # Final fallback - no reranking
        fallback_time = time.time() - rerank_start
        print(f"Using simple ranking fallback ({fallback_time:.1f}s)")
        return [{'content': chunk, 'score': 0} for chunk in chunks[:top_k]]

    async def process(self, query):
        start_time = time.time()

        # Search
        search_start = time.time()
        print("🔍 Searching...")
        sources = await self.search(query)
        urls = [s['url'] for s in sources]
        search_time = time.time() - search_start
        print(f"Found {len(sources)} sources ({search_time:.1f}s)")

        # Scrape
        scrape_start = time.time()
        print(f"📄 Scraping {len(urls)} URLs...")
        scraped = await self.scrape(urls)
        scrape_time = time.time() - scrape_start
        print(f"Successfully scraped {len(scraped)} pages ({scrape_time:.1f}s)")

        # Chunk
        chunk_start = time.time()
        all_chunks = []
        for item in scraped:
            chunks = self.chunk(item['content'])
            all_chunks.extend(chunks[:3])  # Max 3 chunks per source
        chunk_time = time.time() - chunk_start
        print(f"Created {len(all_chunks)} chunks ({chunk_time:.1f}s)")

        # Rerank
        ranked = await self.rerank(query, all_chunks)
        print(f"Reranked to {len(ranked)} top chunks")

        # Format context
        format_start = time.time()
        context = f"Query: {query}\n\n"
        for i, chunk in enumerate(ranked, 1):
            context += f"Source {i} (Score: {chunk.get('score', 0):.3f}):\n{chunk['content'][:500]}...\n\n"
        format_time = time.time() - format_start

        total_time = time.time() - start_time
        print(f"Context formatted ({format_time:.1f}s) | Total: {total_time:.1f}s")

        return {
            'query': query,
            'sources': len(sources),
            'chunks': len(all_chunks),
            'context': context,
            'time': total_time,
            'timing': {
                'search': search_time,
                'scrape': scrape_time,
                'chunk': chunk_time,
                'format': format_time,
                'total': total_time
            }
        }

# Simple usage
async def main():
    load_env()
    serper_key = os.getenv('SERPER_API_KEY')
    firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
    jina_key = os.getenv('JINA_API_KEY')
    cohere_key = os.getenv('COHERE_API_KEY')

    if not serper_key or not firecrawl_key:
        print("Set SERPER_API_KEY and FIRECRAWL_API_KEY environment variables")
        return

    rag = FastRAG(serper_key, firecrawl_key, jina_key, cohere_key, max_age=1800000)  # 30 min for demo

    query = "What is artificial intelligence?"
    print(f"Query: {query}")
    result = await rag.process(query)

    print(f"\nTime: {result['time']:.1f}s | Sources: {result['sources']} | Chunks: {result['chunks']}")
    print("\nCONTEXT:")
    print("=" * 50)
    print(result['context'])

if __name__ == "__main__":
    asyncio.run(main())
