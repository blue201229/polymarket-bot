import pytest

from backend.src.core.events import EventBus


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    async def handler(**data):
        received.append(data)

    bus.subscribe("test.event", handler)
    await bus.publish("test.event", value=42)

    assert len(received) == 1
    assert received[0]["value"] == 42


@pytest.mark.asyncio
async def test_multiple_handlers():
    bus = EventBus()
    results = []

    async def handler1(**data):
        results.append("h1")

    async def handler2(**data):
        results.append("h2")

    bus.subscribe("test.event", handler1)
    bus.subscribe("test.event", handler2)
    await bus.publish("test.event")

    assert "h1" in results
    assert "h2" in results


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(**data):
        received.append(True)

    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)
    await bus.publish("test.event")

    assert len(received) == 0


@pytest.mark.asyncio
async def test_publish_no_handlers():
    bus = EventBus()
    await bus.publish("nonexistent.event")  # should not raise
