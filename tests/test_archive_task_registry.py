import asyncio

import pytest

from services.archive_task_registry import register, wait_for_all


@pytest.mark.asyncio
async def test_wait_for_all_returns_after_task_done():
    async def work():
        await asyncio.sleep(0)

    task = asyncio.create_task(work())
    register(task)
    await wait_for_all(timeout_s=1.0)
    assert task.done()


@pytest.mark.asyncio
async def test_wait_for_all_times_out_with_pending_task():
    gate = asyncio.Event()

    async def work():
        await gate.wait()

    task = asyncio.create_task(work())
    register(task)
    await wait_for_all(timeout_s=0.0)
    assert not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

