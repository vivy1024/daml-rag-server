import asyncio, time, httpx, json

async def test_agent(query):
    url = 'http://localhost:8001/api/v1/chat/stream'
    payload = {
        'user_id': '2',
        'query': query,
        'domain': 'fitness',
        'strategy': 'agent'
    }
    start = time.monotonic()
    first_chunk = None
    total_chars = 0
    content_buf = ''
    error_msg = None

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream('POST', url, json=payload) as resp:
            if resp.status_code != 200:
                error_msg = f'HTTP {resp.status_code}'
                return first_chunk, time.monotonic() - start, 0, error_msg, ''
            async for line in resp.aiter_lines():
                if line.startswith('data: '):
                    d = line[6:]
                    if d == '[DONE]': break
                    try:
                        data = json.loads(d)
                        if data.get('type') == 'error':
                            error_msg = data.get('message', 'unknown error')
                        c = data.get('content', '')
                        if c:
                            if not first_chunk: first_chunk = time.monotonic() - start
                            total_chars += len(c)
                            content_buf += c
                    except:
                        pass
    elapsed = time.monotonic() - start
    preview = content_buf[:150].replace('\n', ' ')
    return first_chunk, elapsed, total_chars, error_msg, preview

async def main():
    q = '帮我算一下TDEE'
    print(f'"{q}" (agent模式)')
    ttfb, total, chars, err, preview = await test_agent(q)
    if err:
        print(f'  ERROR: {err} | 总耗时={total:.1f}s')
    else:
        ttfb_s = f'{ttfb:.1f}s' if ttfb else 'N/A'
        print(f'  TTFB={ttfb_s} | 总耗时={total:.1f}s | 字符={chars}')
        print(f'  预览: {preview}...')

asyncio.run(main())
