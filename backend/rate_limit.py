import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


# In-memory request log for local protection. Use Redis for multi-server production.
request_log = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int):
    async def limiter(request: Request):
        client_host = request.client.host if request.client else "unknown"
        key = (client_host, request.url.path)
        now = time.time()
        window_start = now - window_seconds
        timestamps = request_log[key]

        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again."
            )

        timestamps.append(now)

    return limiter
