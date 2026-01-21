"""
Circuit Breaker for LLM service
"""
import time
import logging
from enum import Enum
from typing import Callable, Any

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to protect against cascading failures

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Allow one test request to check if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60
    ):
        """
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (half-open)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)"""
        if self.state == CircuitState.OPEN:
            # Check if timeout expired -> transition to HALF_OPEN
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: OPEN -> HALF_OPEN (testing)")
                return False
            return True
        return False

    def record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            # Successful test request -> close circuit
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info("Circuit breaker: HALF_OPEN -> CLOSED (service recovered)")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record failed request"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Test request failed -> back to OPEN
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker: HALF_OPEN -> OPEN (service still down)")

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                # Too many failures -> open circuit
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit breaker: CLOSED -> OPEN "
                    f"({self.failure_count} failures, threshold={self.failure_threshold})"
                )

    def get_state(self) -> dict:
        """Get circuit breaker state for monitoring"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "timeout": self.timeout,
            "last_failure_time": self.last_failure_time
        }


# Singleton instance
circuit_breaker = CircuitBreaker(
    failure_threshold=settings.circuit_breaker_failure_threshold,
    timeout=settings.circuit_breaker_timeout
)
