"""``mint``/``consume`` ephemeral stream token over real Redis (10 §5.2).

GETDEL → single-use; TTL-bounded; scan-bound. Requires the docker redis.
"""

from uuid import uuid4

import pytest
from expects import be_false, be_true, expect
from redis.asyncio import Redis

from src.common.settings import settings
from src.scans.infrastructure.sse.stream_token import (
    consume_stream_token,
    mint_stream_token,
)


@pytest.fixture
async def redis():
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    yield client
    await client.aclose()


async def test_mint_then_consume_is_valid_once(redis):
    scan_id = uuid4()
    token = await mint_stream_token(redis, scan_id, uuid4())

    expect(await consume_stream_token(redis, token, scan_id)).to(be_true)


async def test_second_consume_of_same_token_fails(redis):
    scan_id = uuid4()
    token = await mint_stream_token(redis, scan_id, uuid4())

    await consume_stream_token(redis, token, scan_id)
    # Single-use: GETDEL removed the key on first consume.
    expect(await consume_stream_token(redis, token, scan_id)).to(be_false)


async def test_token_for_other_scan_is_rejected(redis):
    token = await mint_stream_token(redis, uuid4(), uuid4())

    expect(await consume_stream_token(redis, token, uuid4())).to(be_false)


async def test_unknown_token_is_rejected(redis):
    expect(await consume_stream_token(redis, "never-minted", uuid4())).to(be_false)


async def test_token_expires_after_ttl(redis):
    scan_id = uuid4()
    token = await mint_stream_token(redis, scan_id, uuid4(), ttl_s=1)

    import asyncio

    await asyncio.sleep(1.2)
    expect(await consume_stream_token(redis, token, scan_id)).to(be_false)
