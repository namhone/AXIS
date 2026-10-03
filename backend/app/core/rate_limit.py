"""Small process-local rate limiter for expensive API operations.

The backend currently runs as a single process in local development. Keeping
the limiter here avoids adding a runtime dependency while making the policy
easy to replace with a shared store when multiple workers are deployed.
"""

from collections import defaultdict
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> int:
        with self._lock:
            now = monotonic()
            timestamps = self._requests[key]
            cutoff = now - self.window_seconds
            self._requests[key] = timestamps = [timestamp for timestamp in timestamps if timestamp > cutoff]
            if len(timestamps) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - timestamps[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limited",
                        "message": "Too many AI requests. Please try again later.",
                        "details": {"retry_after": retry_after},
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            timestamps.append(now)
            return self.limit - len(timestamps)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


class LockoutRateLimiter:
    def __init__(self, limit: int, window_seconds: int, lockout_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._locked_until: dict[str, float] = {}
        self._lock = Lock()

    def check(self, key: str) -> int:
        with self._lock:
            now = monotonic()
            locked_until = self._locked_until.get(key, 0)
            if locked_until > now:
                self._raise_rate_limited(locked_until - now)
            if locked_until:
                self._locked_until.pop(key, None)
                self._requests.pop(key, None)

            cutoff = now - self.window_seconds
            timestamps = self._requests[key]
            self._requests[key] = timestamps = [timestamp for timestamp in timestamps if timestamp > cutoff]
            if len(timestamps) >= self.limit:
                self._locked_until[key] = now + self.lockout_seconds
                self._raise_rate_limited(self.lockout_seconds)

            timestamps.append(now)
            return self.limit - len(timestamps)

    @staticmethod
    def _raise_rate_limited(retry_after: float) -> None:
        seconds = max(1, int(retry_after))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many AI requests. Please try again later.",
                "details": {"retry_after": seconds},
            },
            headers={"Retry-After": str(seconds)},
        )

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._locked_until.clear()


def client_key(request: Request, user_id: object) -> str:
    """Prefer authenticated identity, with IP as a defense-in-depth suffix."""

    host = request.client.host if request.client else "unknown"
    return f"{user_id}:{host}"


def rate_limit_dependency(
    limiter: SlidingWindowRateLimiter,
) -> Callable:
    def enforce(request: Request, user_id: object) -> None:
        limiter.check(client_key(request, user_id))

    return enforce
