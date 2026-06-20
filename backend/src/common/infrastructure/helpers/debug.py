import asyncio

import nest_asyncio

try:
    nest_asyncio.apply()
except ImportError:
    pass


def run_async(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return asyncio.ensure_future(coro)  # Returns a Task, may need `await` somewhere else
    return loop.run_until_complete(coro)
