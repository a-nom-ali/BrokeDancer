"""
Tests for State Store implementations

Tests both in-memory and Redis backends to ensure interface compliance.
"""

import pytest
from datetime import timedelta
from src.infrastructure.state import create_state_store, StateStore


class StateStoreTestSuite:
    """
    Base test suite for state store implementations.

    Subclasses should implement the fixture to provide specific backend.
    """

    @pytest.mark.asyncio
    async def test_set_and_get(self, store: StateStore):
        """Test basic set and get operations"""
        await store.set("test_key", "test_value")
        value = await store.get("test_key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store: StateStore):
        """Test getting non-existent key returns None"""
        value = await store.get("nonexistent_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self, store: StateStore):
        """Test delete operation"""
        await store.set("delete_me", "value")
        assert await store.exists("delete_me")

        result = await store.delete("delete_me")
        assert result is True
        assert not await store.exists("delete_me")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store: StateStore):
        """Test deleting non-existent key returns False"""
        result = await store.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, store: StateStore):
        """Test exists check"""
        assert not await store.exists("check_me")
        await store.set("check_me", "value")
        assert await store.exists("check_me")

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, store: StateStore):
        """Test TTL (time-to-live) functionality"""
        import asyncio

        # Set with 1 second TTL
        await store.set("ttl_key", "value", ttl=timedelta(seconds=1))
        assert await store.get("ttl_key") == "value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        value = await store.get("ttl_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_complex_values(self, store: StateStore):
        """Test storing complex data structures"""
        complex_data = {
            "user_id": 123,
            "name": "Alice",
            "scores": [95, 87, 92],
            "metadata": {
                "created_at": "2024-01-01",
                "active": True
            }
        }

        await store.set("complex", complex_data)
        retrieved = await store.get("complex")

        assert retrieved == complex_data
        assert retrieved["user_id"] == 123
        assert retrieved["metadata"]["active"] is True

    @pytest.mark.asyncio
    async def test_get_many(self, store: StateStore):
        """Test batch get operation"""
        await store.set("key1", "value1")
        await store.set("key2", "value2")
        await store.set("key3", "value3")

        result = await store.get_many(["key1", "key2", "key3", "nonexistent"])

        assert result == {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }

    @pytest.mark.asyncio
    async def test_set_many(self, store: StateStore):
        """Test batch set operation"""
        items = {
            "batch1": "value1",
            "batch2": "value2",
            "batch3": "value3"
        }

        await store.set_many(items)

        assert await store.get("batch1") == "value1"
        assert await store.get("batch2") == "value2"
        assert await store.get("batch3") == "value3"

    @pytest.mark.asyncio
    async def test_increment(self, store: StateStore):
        """Test atomic increment"""
        # Increment non-existent key (should start at 0)
        result = await store.increment("counter")
        assert result == 1

        # Increment again
        result = await store.increment("counter")
        assert result == 2

        # Increment by different amount
        result = await store.increment("counter", 5)
        assert result == 7

    @pytest.mark.asyncio
    async def test_decrement(self, store: StateStore):
        """Test atomic decrement"""
        await store.set("countdown", 10)

        result = await store.decrement("countdown")
        assert result == 9

        result = await store.decrement("countdown", 3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_get_or_default(self, store: StateStore):
        """Test get with default value"""
        # Key exists
        await store.set("existing", "value")
        result = await store.get_or_default("existing", "default")
        assert result == "value"

        # Key doesn't exist
        result = await store.get_or_default("missing", "default")
        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_if_not_exists(self, store: StateStore):
        """Test conditional set"""
        # First set should succeed
        result = await store.set_if_not_exists("unique", "value1")
        assert result is True
        assert await store.get("unique") == "value1"

        # Second set should fail (key exists)
        result = await store.set_if_not_exists("unique", "value2")
        assert result is False
        assert await store.get("unique") == "value1"  # Unchanged

    @pytest.mark.asyncio
    async def test_get_and_delete(self, store: StateStore):
        """Test atomic get-and-delete"""
        await store.set("temp", "value")

        # Get and delete
        value = await store.get_and_delete("temp")
        assert value == "value"

        # Key should be gone
        assert not await store.exists("temp")

        # Non-existent key
        value = await store.get_and_delete("nonexistent")
        assert value is None


# Test suite for in-memory backend
class TestInMemoryStateStore(StateStoreTestSuite):
    """Tests for in-memory state store"""

    @pytest.fixture
    async def store(self):
        """Create in-memory store for testing"""
        store = create_state_store("memory")
        yield store
        await store.close()


# Test suite for Redis backend (requires Redis running)
class TestRedisStateStore(StateStoreTestSuite):
    """Tests for Redis state store"""

    @pytest.fixture
    async def store(self):
        """Create Redis store for testing"""
        try:
            store = create_state_store("redis", url="redis://localhost:6379/15")

            # Test connection
            if not await store.ping():
                pytest.skip("Redis not available")

            # Clean up test database
            await store.close()

            # Reconnect
            store = create_state_store("redis", url="redis://localhost:6379/15")

            yield store

            # Cleanup
            await store.close()

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    @pytest.mark.asyncio
    async def test_redis_specific_ttl(self, store):
        """Test Redis-specific TTL methods"""
        from datetime import timedelta
        import asyncio

        # Set key with TTL
        await store.set("ttl_test", "value", ttl=timedelta(seconds=10))

        # Check TTL
        ttl = await store.ttl("ttl_test")
        assert ttl is not None
        assert 8 <= ttl <= 10  # Allow some time variance

        # Extend TTL
        await store.expire("ttl_test", timedelta(seconds=20))
        ttl = await store.ttl("ttl_test")
        assert ttl is not None
        assert 18 <= ttl <= 20

    @pytest.mark.asyncio
    async def test_redis_keys_pattern(self, store):
        """Test Redis keys pattern matching"""
        await store.set("user:1", "alice")
        await store.set("user:2", "bob")
        await store.set("post:1", "hello")

        user_keys = await store.keys("user:*")
        assert "user:1" in user_keys
        assert "user:2" in user_keys
        assert "post:1" not in user_keys


# Integration tests
@pytest.mark.asyncio
async def test_factory_memory():
    """Test factory creates in-memory store"""
    store = create_state_store("memory")
    assert store is not None
    await store.set("test", "value")
    assert await store.get("test") == "value"
    await store.close()


@pytest.mark.asyncio
async def test_factory_redis():
    """Test factory creates Redis store"""
    try:
        store = create_state_store("redis", url="redis://localhost:6379/15")

        # Test connection
        if await store.ping():
            await store.set("test", "value")
            assert await store.get("test") == "value"
        else:
            pytest.skip("Redis not available")

        await store.close()
    except Exception:
        pytest.skip("Redis not available")


def test_factory_invalid_backend():
    """Test factory raises error for invalid backend"""
    with pytest.raises(ValueError, match="Unknown state backend"):
        create_state_store("invalid_backend")
