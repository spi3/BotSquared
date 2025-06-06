import asyncio
import time
from functools import wraps

def rate_limit(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        for _ in range(0, 3):
            rate_limit = self._rate_limit()
            while rate_limit != 0:
                await asyncio.sleep(rate_limit)
                rate_limit = self._rate_limit()
            self.last_api_call = time.time()
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error {func.__name__}() - {e!r} {e} - Retrying...")
                await asyncio.sleep(self.rate_limit)
        return None
    return wrapper 