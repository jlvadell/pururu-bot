import time
from enum import Enum

from pururu.common import utils
from pururu.common.exceptions import CircuitBreakerException


class CircuitBreakerState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_timeout: int, open_fallback=None, on_half_open=None):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.logger = utils.get_logger(__name__)
        self.last_failure_time = 0
        self.open_fallback = open_fallback
        self.on_half_open = on_half_open

    def call(self, func, *args, **kwargs):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                if self.on_half_open:
                    try:
                        self.on_half_open()
                    except Exception as recovery_error:
                        self._handle_failure(recovery_error)
                        raise CircuitBreakerException("Half-open recovery failed.") from recovery_error
            elif self.open_fallback:
                return self.open_fallback(func, *args, **kwargs)
            else:
                raise CircuitBreakerException("Circuit is open; call is rejected.")

        try:
            result = func(*args, **kwargs)
            self._reset_on_success()
            return result
        except Exception as e:
            self._handle_failure(e)
            raise e

    def _reset_on_success(self):
        self.failure_count = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED

    def _handle_failure(self, exception):
        self.logger.debug(f"Circuit breaker failure: {exception}")
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == CircuitBreakerState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self._trigger_open_state()

    def _trigger_open_state(self):
        self.state = CircuitBreakerState.OPEN
