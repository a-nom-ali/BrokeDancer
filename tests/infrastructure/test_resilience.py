"""
Tests for Resilience Infrastructure

Tests retry logic, circuit breakers, and timeout handling.
"""

import pytest
import asyncio
from src.infrastructure.resilience import (
    with_retry,
    RetryConfig,
    RetryExhausted,
    with_retry_config,
    retry_async,
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitBreakerState,
    with_timeout,
    TimeoutError,
    with_timeout_async,
    TimeoutContext,
    wait_for_any,
    wait_for_all
)


# ============================================================================
# Retry Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retry_success_no_retries():
    """Test successful operation without retries"""
    call_count = 0

    @with_retry(max_attempts=3)
    async def succeed_immediately():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await succeed_immediately()
    assert result == "success"
    assert call_count == 1  # No retries needed


@pytest.mark.asyncio
async def test_retry_success_after_failures():
    """Test successful operation after some failures"""
    call_count = 0

    @with_retry(max_attempts=3, min_wait_seconds=0.01)
    async def succeed_on_third_try():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"

    result = await succeed_on_third_try()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    """Test retry exhaustion"""
    call_count = 0

    @with_retry(max_attempts=3, min_wait_seconds=0.01)
    async def always_fail():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Permanent failure")

    with pytest.raises(RetryExhausted) as exc_info:
        await always_fail()

    assert call_count == 3
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_exception, ConnectionError)


@pytest.mark.asyncio
async def test_retry_specific_exceptions():
    """Test retry only on specific exception types"""
    call_count = 0

    @with_retry(
        max_attempts=3,
        retry_on=(ConnectionError, TimeoutError),
        min_wait_seconds=0.01
    )
    async def fail_with_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("Should not retry")

    # Should fail immediately without retries (ValueError not in retry_on)
    with pytest.raises(ValueError):
        await fail_with_value_error()

    assert call_count == 1  # No retries


@pytest.mark.asyncio
async def test_retry_config():
    """Test retry with RetryConfig"""
    config = RetryConfig(
        max_attempts=5,
        min_wait_seconds=0.01,
        max_wait_seconds=0.1,
        multiplier=2,
        retry_on=(ConnectionError,)
    )

    call_count = 0

    @with_retry_config(config)
    async def use_config():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Retry me")
        return "success"

    result = await use_config()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_function():
    """Test retry_async utility"""
    call_count = 0

    async def my_function(value: str):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Retry me")
        return f"result: {value}"

    result = await retry_async(
        my_function,
        "test",
        max_attempts=3,
        min_wait_seconds=0.01
    )

    assert result == "result: test"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Test exponential backoff timing"""
    import time

    call_times = []

    @with_retry(
        max_attempts=3,
        min_wait_seconds=0.1,
        max_wait_seconds=1.0,
        multiplier=2
    )
    async def track_timing():
        call_times.append(time.time())
        if len(call_times) < 3:
            raise ConnectionError("Retry me")
        return "success"

    await track_timing()

    # Check that backoff increased between attempts
    # (approximate check due to timing variability)
    if len(call_times) >= 2:
        gap1 = call_times[1] - call_times[0]
        assert gap1 >= 0.1  # First retry after min_wait_seconds


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_closed_state():
    """Test circuit breaker in CLOSED state (normal operation)"""
    breaker = CircuitBreaker("test", failure_threshold=5)

    async def succeed():
        return "success"

    result = await breaker.call(succeed)
    assert result == "success"
    assert breaker.state == CircuitBreakerState.CLOSED
    assert breaker.is_closed


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold failures"""
    breaker = CircuitBreaker(
        "test",
        failure_threshold=3,
        window_seconds=10
    )

    async def always_fail():
        raise ConnectionError("Fail")

    # Fail 3 times (threshold)
    for _ in range(3):
        with pytest.raises(ConnectionError):
            await breaker.call(always_fail)

    # Circuit should now be open
    assert breaker.state == CircuitBreakerState.OPEN
    assert breaker.is_open

    # Next call should fail fast
    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(always_fail)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovery through HALF_OPEN state"""
    breaker = CircuitBreaker(
        "test",
        failure_threshold=2,
        success_threshold=2,
        timeout_seconds=0.1,
        window_seconds=10
    )

    call_count = 0

    async def fail_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Fail")
        return "success"

    # Open circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await breaker.call(fail_then_succeed)

    assert breaker.is_open

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Should now be half-open and succeed
    result = await breaker.call(fail_then_succeed)
    assert result == "success"
    assert breaker.is_half_open

    # Another success should close circuit
    result = await breaker.call(fail_then_succeed)
    assert result == "success"
    assert breaker.is_closed


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_reopens():
    """Test circuit breaker reopens if failure in HALF_OPEN"""
    breaker = CircuitBreaker(
        "test",
        failure_threshold=2,
        timeout_seconds=0.1,
        window_seconds=10
    )

    async def always_fail():
        raise ConnectionError("Fail")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await breaker.call(always_fail)

    assert breaker.is_open

    # Wait for timeout (transitions to half-open)
    await asyncio.sleep(0.15)

    # Failure in half-open should reopen circuit
    with pytest.raises(ConnectionError):
        await breaker.call(always_fail)

    assert breaker.is_open


@pytest.mark.asyncio
async def test_circuit_breaker_force_open():
    """Test manually forcing circuit breaker open"""
    breaker = CircuitBreaker("test", failure_threshold=5)

    assert breaker.is_closed

    # Force open
    await breaker.force_open()
    assert breaker.is_open

    # Should fail fast
    async def succeed():
        return "success"

    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(succeed)


@pytest.mark.asyncio
async def test_circuit_breaker_force_close():
    """Test manually forcing circuit breaker closed"""
    breaker = CircuitBreaker("test", failure_threshold=2, window_seconds=10)

    async def fail():
        raise ConnectionError("Fail")

    # Open circuit
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

    assert breaker.is_open

    # Force close
    await breaker.force_close()
    assert breaker.is_closed


@pytest.mark.asyncio
async def test_circuit_breaker_reset():
    """Test resetting circuit breaker"""
    breaker = CircuitBreaker("test", failure_threshold=2, window_seconds=10)

    async def fail():
        raise ConnectionError("Fail")

    # Cause some failures
    for _ in range(2):
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

    assert breaker.is_open

    # Reset
    await breaker.reset()
    assert breaker.is_closed
    assert breaker._failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_stats():
    """Test circuit breaker statistics"""
    breaker = CircuitBreaker("test_stats", failure_threshold=5)

    stats = breaker.get_stats()
    assert stats["name"] == "test_stats"
    assert stats["state"] == "closed"
    assert stats["failure_count"] == 0
    assert stats["config"]["failure_threshold"] == 5


# ============================================================================
# Timeout Tests
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_success():
    """Test operation completes within timeout"""
    @with_timeout(1.0)
    async def quick_operation():
        await asyncio.sleep(0.01)
        return "success"

    result = await quick_operation()
    assert result == "success"


@pytest.mark.asyncio
async def test_timeout_exceeded():
    """Test operation exceeds timeout"""
    @with_timeout(0.1, operation_name="slow_op")
    async def slow_operation():
        await asyncio.sleep(1.0)
        return "should not reach here"

    with pytest.raises(TimeoutError) as exc_info:
        await slow_operation()

    assert exc_info.value.seconds == 0.1
    assert exc_info.value.operation == "slow_op"


@pytest.mark.asyncio
async def test_timeout_async_function():
    """Test with_timeout_async utility"""
    async def my_function(value: str):
        await asyncio.sleep(0.01)
        return f"result: {value}"

    result = await with_timeout_async(
        my_function,
        "test",
        timeout_seconds=1.0
    )
    assert result == "result: test"


@pytest.mark.asyncio
async def test_timeout_async_exceeds():
    """Test with_timeout_async when timeout exceeded"""
    async def slow_function():
        await asyncio.sleep(1.0)
        return "too slow"

    with pytest.raises(TimeoutError):
        await with_timeout_async(
            slow_function,
            timeout_seconds=0.1,
            operation_name="slow_func"
        )


@pytest.mark.asyncio
async def test_timeout_context_success():
    """Test TimeoutContext with successful operation"""
    async with TimeoutContext(1.0, "test_op"):
        await asyncio.sleep(0.01)
        result = "success"

    assert result == "success"


@pytest.mark.asyncio
async def test_timeout_context_exceeded():
    """Test TimeoutContext when timeout exceeded"""
    with pytest.raises(TimeoutError):
        async with TimeoutContext(0.1, "slow_context"):
            await asyncio.sleep(1.0)


@pytest.mark.asyncio
async def test_wait_for_any():
    """Test waiting for any task to complete"""
    async def fast_task():
        await asyncio.sleep(0.01)
        return "fast"

    async def slow_task():
        await asyncio.sleep(1.0)
        return "slow"

    tasks = [
        asyncio.create_task(fast_task()),
        asyncio.create_task(slow_task())
    ]

    result, remaining = await wait_for_any(tasks, timeout_seconds=2.0)

    assert result == "fast"
    assert len(remaining) == 1

    # Cancel remaining
    for task in remaining:
        task.cancel()


@pytest.mark.asyncio
async def test_wait_for_any_timeout():
    """Test wait_for_any with timeout"""
    async def slow_task():
        await asyncio.sleep(1.0)
        return "too slow"

    tasks = [asyncio.create_task(slow_task())]

    with pytest.raises(TimeoutError):
        await wait_for_any(tasks, timeout_seconds=0.1)


@pytest.mark.asyncio
async def test_wait_for_all():
    """Test waiting for all tasks to complete"""
    async def task1():
        await asyncio.sleep(0.01)
        return "result1"

    async def task2():
        await asyncio.sleep(0.02)
        return "result2"

    tasks = [
        asyncio.create_task(task1()),
        asyncio.create_task(task2())
    ]

    results = await wait_for_all(tasks, timeout_seconds=1.0)
    assert results == ["result1", "result2"]


@pytest.mark.asyncio
async def test_wait_for_all_timeout():
    """Test wait_for_all with timeout"""
    async def slow_task():
        await asyncio.sleep(1.0)
        return "too slow"

    tasks = [asyncio.create_task(slow_task())]

    with pytest.raises(TimeoutError):
        await wait_for_all(tasks, timeout_seconds=0.1)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_retry_with_timeout():
    """Test combining retry and timeout"""
    call_count = 0

    @with_retry(max_attempts=3, min_wait_seconds=0.01)
    @with_timeout(0.5)
    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("Retry me")
        await asyncio.sleep(0.01)
        return "success"

    result = await flaky_operation()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_circuit_breaker_with_retry():
    """Test circuit breaker protecting retried operations"""
    breaker = CircuitBreaker("test", failure_threshold=2, window_seconds=10)

    call_count = 0

    @with_retry(max_attempts=2, min_wait_seconds=0.01)
    async def operation_with_retry():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Fail")

    # Make multiple calls to open the circuit (each will retry internally)
    # First call will fail with RetryExhausted (1 circuit breaker failure)
    with pytest.raises(RetryExhausted):
        await breaker.call(operation_with_retry)

    # Second call will also fail (2nd circuit breaker failure)
    with pytest.raises(RetryExhausted):
        await breaker.call(operation_with_retry)

    # Circuit should now be open after 2 failures
    assert breaker.is_open

    # Next call should fail fast (no retries executed)
    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(operation_with_retry)


@pytest.mark.asyncio
async def test_full_resilience_stack():
    """Test combining retry, circuit breaker, and timeout"""
    breaker = CircuitBreaker("api", failure_threshold=3, window_seconds=10)

    call_count = 0

    @with_retry(max_attempts=2, min_wait_seconds=0.01)
    @with_timeout(0.5)
    async def resilient_api_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Network blip")
        await asyncio.sleep(0.01)
        return f"success_{call_count}"

    # Should succeed after 1 retry
    result = await breaker.call(resilient_api_call)
    assert result == "success_2"
    assert breaker.is_closed
