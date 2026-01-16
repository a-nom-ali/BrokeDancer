"""
Unit tests for utils module.
"""

import unittest
import time
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils import (
    mask_credential,
    validate_ethereum_address,
    validate_order_id,
    validate_market_slug,
    safe_float_conversion,
    safe_decimal_conversion,
    is_approximately_equal,
    EPSILON_SIZE,
    EPSILON_PRICE,
    EPSILON_BALANCE,
    RateLimiter,
    BalanceCache,
    RetryConfig,
    retry_with_backoff,
    CircuitBreaker,
    CircuitBreakerState,
)


class TestCredentialMasking(unittest.TestCase):
    """Test credential masking functionality."""

    def test_mask_credential_normal(self):
        """Test masking with normal length credential."""
        result = mask_credential("abc123xyz789", 4)
        self.assertEqual(result, "abc1***")

    def test_mask_credential_short(self):
        """Test masking with credential shorter than visible chars."""
        result = mask_credential("abc", 4)
        self.assertEqual(result, "***")

    def test_mask_credential_empty(self):
        """Test masking with empty credential."""
        result = mask_credential("", 4)
        self.assertEqual(result, "***")

    def test_mask_credential_custom_visible_chars(self):
        """Test masking with custom visible characters."""
        result = mask_credential("secret123", 6)
        self.assertEqual(result, "secret***")


class TestValidation(unittest.TestCase):
    """Test validation functions."""

    def test_validate_ethereum_address_valid(self):
        """Test valid Ethereum address."""
        valid_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        self.assertTrue(validate_ethereum_address(valid_address))

    def test_validate_ethereum_address_invalid(self):
        """Test invalid Ethereum addresses."""
        self.assertFalse(validate_ethereum_address(""))
        self.assertFalse(validate_ethereum_address("not_an_address"))
        self.assertFalse(validate_ethereum_address("0x123"))  # Too short
        self.assertFalse(validate_ethereum_address("742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"))  # No 0x

    def test_validate_order_id_valid(self):
        """Test valid order IDs."""
        self.assertTrue(validate_order_id("order123"))
        self.assertTrue(validate_order_id("a" * 255))  # Max length

    def test_validate_order_id_invalid(self):
        """Test invalid order IDs."""
        self.assertFalse(validate_order_id(""))
        self.assertFalse(validate_order_id("a" * 256))  # Too long

    def test_validate_market_slug_valid(self):
        """Test valid market slugs."""
        self.assertTrue(validate_market_slug("btc-updown-15m-1765301400"))
        self.assertTrue(validate_market_slug("test_market-123"))

    def test_validate_market_slug_invalid(self):
        """Test invalid market slugs."""
        self.assertFalse(validate_market_slug(""))
        self.assertFalse(validate_market_slug("market with spaces"))
        self.assertFalse(validate_market_slug("market@special"))
        self.assertFalse(validate_market_slug("a" * 256))  # Too long


class TestSafeConversions(unittest.TestCase):
    """Test safe conversion functions."""

    def test_safe_float_conversion_valid(self):
        """Test safe float conversion with valid inputs."""
        self.assertEqual(safe_float_conversion("123.45"), 123.45)
        self.assertEqual(safe_float_conversion(100), 100.0)
        self.assertEqual(safe_float_conversion(3.14), 3.14)

    def test_safe_float_conversion_invalid(self):
        """Test safe float conversion with invalid inputs."""
        self.assertEqual(safe_float_conversion("not_a_number", 0.0), 0.0)
        self.assertEqual(safe_float_conversion(None, 5.0), 5.0)
        self.assertEqual(safe_float_conversion("", 10.0), 10.0)

    def test_safe_decimal_conversion_valid(self):
        """Test safe decimal conversion with valid inputs."""
        result = safe_decimal_conversion("123.45")
        self.assertEqual(result, Decimal("123.45"))

    def test_safe_decimal_conversion_invalid(self):
        """Test safe decimal conversion with invalid inputs."""
        result = safe_decimal_conversion("not_a_number", "0.0")
        self.assertEqual(result, Decimal("0.0"))


class TestNumericPrecision(unittest.TestCase):
    """Test numeric precision utilities."""

    def test_epsilon_constants(self):
        """Test epsilon constants are defined correctly."""
        self.assertEqual(EPSILON_SIZE, 1e-9)
        self.assertEqual(EPSILON_PRICE, 1e-4)
        self.assertEqual(EPSILON_BALANCE, 1e-2)

    def test_is_approximately_equal_true(self):
        """Test approximately equal returns True for close values."""
        self.assertTrue(is_approximately_equal(1.0, 1.00005, EPSILON_PRICE))
        self.assertTrue(is_approximately_equal(0.99, 0.99009, EPSILON_PRICE))

    def test_is_approximately_equal_false(self):
        """Test approximately equal returns False for distant values."""
        self.assertFalse(is_approximately_equal(1.0, 1.1, EPSILON_PRICE))
        self.assertFalse(is_approximately_equal(0.5, 0.6, EPSILON_PRICE))


class TestRateLimiter(unittest.TestCase):
    """Test rate limiter functionality."""

    def test_rate_limiter_allows_initial_requests(self):
        """Test rate limiter allows initial requests."""
        limiter = RateLimiter(max_requests=3, time_window=1.0)
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())

    def test_rate_limiter_blocks_excess_requests(self):
        """Test rate limiter blocks excess requests."""
        limiter = RateLimiter(max_requests=2, time_window=1.0)
        self.assertTrue(limiter.allow_request())
        self.assertTrue(limiter.allow_request())
        self.assertFalse(limiter.allow_request())  # Third request blocked

    def test_rate_limiter_reset(self):
        """Test rate limiter reset functionality."""
        limiter = RateLimiter(max_requests=1, time_window=1.0)
        limiter.allow_request()
        self.assertFalse(limiter.allow_request())  # Blocked
        limiter.reset()
        self.assertTrue(limiter.allow_request())  # Allowed after reset

    def test_rate_limiter_time_window(self):
        """Test rate limiter respects time window."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)
        limiter.allow_request()
        limiter.allow_request()
        self.assertFalse(limiter.allow_request())  # Blocked
        time.sleep(0.15)  # Wait for window to expire
        self.assertTrue(limiter.allow_request())  # Allowed after window


class TestBalanceCache(unittest.TestCase):
    """Test balance cache functionality."""

    def test_balance_cache_initial_state(self):
        """Test balance cache initial state."""
        cache = BalanceCache(ttl=60.0)
        self.assertIsNone(cache.get())
        self.assertFalse(cache.is_valid())

    def test_balance_cache_set_and_get(self):
        """Test setting and getting cached balance."""
        cache = BalanceCache(ttl=60.0)
        cache.set(100.0)
        self.assertEqual(cache.get(), 100.0)
        self.assertTrue(cache.is_valid())

    def test_balance_cache_expiration(self):
        """Test balance cache expiration."""
        cache = BalanceCache(ttl=0.1)
        cache.set(100.0)
        self.assertEqual(cache.get(), 100.0)
        time.sleep(0.15)
        self.assertIsNone(cache.get())  # Expired

    def test_balance_cache_invalidate(self):
        """Test balance cache invalidation."""
        cache = BalanceCache(ttl=60.0)
        cache.set(100.0)
        cache.invalidate()
        self.assertIsNone(cache.get())
        self.assertFalse(cache.is_valid())

    def test_balance_cache_get_or_fetch_success(self):
        """Test get_or_fetch with successful fetch."""
        cache = BalanceCache(ttl=60.0)
        fetch_func = Mock(return_value=150.0)
        balance = cache.get_or_fetch(fetch_func)
        self.assertEqual(balance, 150.0)
        fetch_func.assert_called_once()

    def test_balance_cache_get_or_fetch_cached(self):
        """Test get_or_fetch uses cached value."""
        cache = BalanceCache(ttl=60.0)
        cache.set(100.0)
        fetch_func = Mock(return_value=150.0)
        balance = cache.get_or_fetch(fetch_func)
        self.assertEqual(balance, 100.0)  # Uses cached
        fetch_func.assert_not_called()

    def test_balance_cache_get_or_fetch_failure_with_stale(self):
        """Test get_or_fetch returns stale cache on fetch failure."""
        cache = BalanceCache(ttl=0.1)
        cache.set(100.0)
        time.sleep(0.15)  # Expire cache
        fetch_func = Mock(side_effect=Exception("Network error"))
        balance = cache.get_or_fetch(fetch_func)
        self.assertEqual(balance, 100.0)  # Returns stale cache

    def test_balance_cache_get_or_fetch_failure_no_cache(self):
        """Test get_or_fetch returns 0 on failure with no cache."""
        cache = BalanceCache(ttl=60.0)
        fetch_func = Mock(side_effect=Exception("Network error"))
        balance = cache.get_or_fetch(fetch_func)
        self.assertEqual(balance, 0.0)


class TestRetryConfig(unittest.TestCase):
    """Test retry configuration."""

    def test_retry_config_delay_calculation(self):
        """Test retry config delay calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False
        )
        self.assertEqual(config.get_delay(0), 1.0)  # 1 * 2^0
        self.assertEqual(config.get_delay(1), 2.0)  # 1 * 2^1
        self.assertEqual(config.get_delay(2), 4.0)  # 1 * 2^2
        self.assertEqual(config.get_delay(3), 8.0)  # 1 * 2^3
        self.assertEqual(config.get_delay(4), 10.0)  # Max delay capped


class TestRetryDecorator(unittest.TestCase):
    """Test retry decorator."""

    def test_retry_succeeds_first_attempt(self):
        """Test function succeeds on first attempt."""
        mock_func = Mock(return_value="success")
        decorated = retry_with_backoff(max_attempts=3)(mock_func)
        result = decorated()
        self.assertEqual(result, "success")
        mock_func.assert_called_once()

    def test_retry_succeeds_after_failures(self):
        """Test function succeeds after initial failures."""
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        decorated = retry_with_backoff(max_attempts=3, initial_delay=0.01)(mock_func)
        result = decorated()
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)

    def test_retry_fails_all_attempts(self):
        """Test function fails after all retry attempts."""
        mock_func = Mock(side_effect=Exception("fail"))
        decorated = retry_with_backoff(max_attempts=2, initial_delay=0.01)(mock_func)
        with self.assertRaises(Exception):
            decorated()
        self.assertEqual(mock_func.call_count, 2)


class TestCircuitBreaker(unittest.TestCase):
    """Test circuit breaker functionality."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3)
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            breaker.record_failure()
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)

    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets failure count on success."""
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(breaker._failure_count, 0)

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker enters HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        breaker.record_failure()
        breaker.record_failure()
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)
        time.sleep(0.15)
        self.assertEqual(breaker.state, CircuitBreakerState.HALF_OPEN)

    def test_circuit_breaker_call_success(self):
        """Test circuit breaker call with successful function."""
        breaker = CircuitBreaker()
        func = Mock(return_value="success")
        result = breaker.call(func)
        self.assertEqual(result, "success")
        func.assert_called_once()

    def test_circuit_breaker_call_failure(self):
        """Test circuit breaker call with failing function."""
        breaker = CircuitBreaker(failure_threshold=2)
        func = Mock(side_effect=Exception("fail"))
        with self.assertRaises(Exception):
            breaker.call(func)
        self.assertEqual(breaker._failure_count, 1)

    def test_circuit_breaker_blocks_when_open(self):
        """Test circuit breaker blocks calls when OPEN."""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure()
        func = Mock()
        with self.assertRaises(RuntimeError) as ctx:
            breaker.call(func)
        self.assertIn("OPEN", str(ctx.exception))
        func.assert_not_called()

    def test_circuit_breaker_reset(self):
        """Test circuit breaker manual reset."""
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure()
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)
        breaker.reset()
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(breaker._failure_count, 0)


if __name__ == '__main__':
    unittest.main()
