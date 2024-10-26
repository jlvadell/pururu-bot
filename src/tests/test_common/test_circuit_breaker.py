import time
from unittest.mock import Mock

import pytest
from hamcrest import assert_that, equal_to, calling, raises

from pururu.common.circuit_breaker import CircuitBreaker, CircuitBreakerState
from pururu.common.exceptions import CircuitBreakerException


def set_up(failure_threshold=3, recovery_timeout=2):
    return CircuitBreaker(failure_threshold, recovery_timeout)


def test_initial_success_call():
    # Given
    breaker = set_up()
    mock_function = Mock(return_value="success")
    # When
    result = breaker.call(mock_function)
    # Then
    assert_that(result, equal_to("success"))
    assert_that(breaker.state, equal_to(CircuitBreakerState.CLOSED))
    assert_that(mock_function.call_count, equal_to(1))


def test_circuit_open_call():
    # Given
    breaker = set_up(failure_threshold=1, recovery_timeout=5000)
    breaker.state = CircuitBreakerState.OPEN
    breaker.last_failure_time = time.time()
    mock_function = Mock(return_value="success")
    # When-Then
    assert_that(calling(breaker.call).with_args(mock_function), raises(CircuitBreakerException))
    assert_that(breaker.state, equal_to(CircuitBreakerState.OPEN))
    assert_that(mock_function.call_count, equal_to(0))


def test_circuit_opens_after_threshold():
    # Given
    breaker = set_up(failure_threshold=2, recovery_timeout=2)
    mock_function = Mock(side_effect=Exception("Function failed"))
    # when
    with pytest.raises(Exception):
        breaker.call(mock_function)
    with pytest.raises(Exception):
        breaker.call(mock_function)
    # Then
    assert_that(breaker.state, equal_to(CircuitBreakerState.OPEN))
    assert_that(breaker.failure_count, equal_to(2))


def test_half_open_success_closes_circuit():
    # Given
    breaker = set_up()
    breaker.state = CircuitBreakerState.HALF_OPEN
    mock_function = Mock(return_value="success")
    # When
    result = breaker.call(mock_function)
    # Then
    assert_that(result, equal_to("success"))
    assert_that(breaker.state, equal_to(CircuitBreakerState.CLOSED))


def test_open_state_calls_fallback():
    # Given
    fallback_function = Mock(return_value="fallback result")
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=5000, open_fallback=fallback_function)
    breaker.last_failure_time = time.time()
    breaker.state = CircuitBreakerState.OPEN
    # When
    result = breaker.call(lambda: Exception("error"))
    # Then
    assert_that(result, equal_to("fallback result"))
    assert_that(fallback_function.call_count, equal_to(1))


def test_half_open_failure_reopens_circuit():
    # Given
    recovery_function = Mock(side_effect=Exception("Recovery failed"))
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=1, on_half_open=recovery_function)
    breaker.last_failure_time = time.time() - 10
    breaker.state = CircuitBreakerState.OPEN
    # When
    with pytest.raises(CircuitBreakerException):
        breaker.call(lambda: "ok")
    # Then
    assert_that(breaker.state, equal_to(CircuitBreakerState.OPEN))
