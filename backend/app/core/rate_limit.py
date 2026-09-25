"""Small process-local rate limiter for expensive API operations.

The backend currently runs as a single process in local development. Keeping
the limiter here avoids adding a runtime dependency while making the policy
easy to replace with a shared store when multiple workers are deployed.
"""

from collections import defaultdict
from collections.abc import Callable
from time import monotonic

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> int:
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
        self._requests.clear()


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
