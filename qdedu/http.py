"""Cliente HTTP com rate limiting e retry/backoff exponencial."""
from __future__ import annotations

import logging
import threading
import time

import httpx

from .config import settings

log = logging.getLogger("qdedu.http")


class RateLimiter:
    """Limitador simples token-bucket-ish baseado em intervalo mínimo."""

    def __init__(self, rps: float) -> None:
        self._min_interval = 1.0 / rps if rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_at - now
            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()
            self._next_at = now + self._min_interval


class HttpClient:
    """Wrapper fino sobre httpx.Client com rate limit e retries idempotentes."""

    # Status que justificam nova tentativa (transientes / rate limit upstream).
    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(
        self,
        rate_rps: float | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self._limiter = RateLimiter(rate_rps if rate_rps is not None else settings.rate_rps)
        self._max_retries = max_retries if max_retries is not None else settings.max_retries
        self._client = httpx.Client(
            timeout=timeout if timeout is not None else settings.timeout,
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._limiter.wait()
            try:
                resp = self._client.get(url, params=params)
            except httpx.HTTPError as exc:  # rede caiu, DNS, timeout
                last_exc = exc
                log.warning("GET %s falhou (%s); tentativa %d", url, exc, attempt + 1)
            else:
                if resp.status_code not in self.RETRY_STATUS:
                    return resp
                last_exc = httpx.HTTPStatusError(
                    f"status {resp.status_code}", request=resp.request, response=resp
                )
                log.warning(
                    "GET %s -> %d; tentativa %d", url, resp.status_code, attempt + 1
                )
            if attempt < self._max_retries:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s
        assert last_exc is not None
        raise last_exc

    def get_text(self, url: str) -> str:
        """Baixa um recurso textual (ex.: txt_url do diário)."""
        resp = self.get(url)
        resp.raise_for_status()
        return resp.text

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
