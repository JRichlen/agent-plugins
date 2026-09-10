import asyncio

async def retry(fn):
    await asyncio.sleep(1)
    return await fn()
