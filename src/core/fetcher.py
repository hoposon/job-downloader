from __future__ import annotations
import time
import logging
from typing import Any, Dict, List, Optional

# Prefer curl_cffi (Chrome-like TLS/HTTP2). Fall back to requests if not present.
try:
    from curl_cffi import requests as http  # type: ignore
    _IMPERS = "chrome"  # or "chrome120"
    _HAS_CFFI = True
except Exception:  # pragma: no cover
    import requests as http  # type: ignore
    _IMPERS = None
    _HAS_CFFI = False


class DmwClient:
    def __init__(
        self,
        api_base: str,
        api_key: str = "",
        user_agent: str = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/139.0 Safari/537.36"
        ),
        timeout: int = 30,
        polite_delay: float = 0.3,
    ):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.polite_delay = polite_delay

        self.session = http.Session()
        # curl_cffi sessions can impersonate a browser; set once.
        if _HAS_CFFI and _IMPERS:
            self.session.impersonate = _IMPERS  # type: ignore[attr-defined]

        # Browser-like default headers
        self.session.headers.update({
            "user-agent": user_agent,
            "accept": "application/json",
            "origin": "https://dmw.gov.ph",
            "referer": "https://dmw.gov.ph/",
            "accept-language": "en-US,en;q=0.9",
        })
        if api_key:
            # match the working fetch: lower-case header name
            self.session.headers.update({"x-api-key": api_key})

    def fetch_page(self, jobsite: str, page: int) -> Dict[str, Any]:
        params = {"jobsite": jobsite, "page": page}
        if _HAS_CFFI and _IMPERS:
            r = self.session.get(self.api_base, params=params, timeout=self.timeout)
        else:
            # fallback (may get 401 on bot-protected edges)
            r = self.session.get(self.api_base, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def fetch_all(self, jobsite: str, max_pages: Optional[int] = None, progress=None) -> List[Dict[str, Any]]:
        data0 = self.fetch_page(jobsite, 1)
        meta = data0.get("meta", {})
        last_page = int(meta.get("lastPage") or 1)
        total = int(meta.get("total") or 0)
        per_page = int(meta.get("perPage") or 0)
        rows = data0.get("data") or []
        if progress:
            progress(f"Meta: total={total}, perPage={per_page}, lastPage={last_page}")

        all_rows: List[Dict[str, Any]] = list(rows)
        if max_pages is not None:
            last_page = min(last_page, max_pages)

        for page in range(2, last_page + 1):
            if progress:
                progress(f"Fetching page {page}/{last_page} …")
            try:
                data = self.fetch_page(jobsite, page)
                all_rows.extend(data.get("data") or [])
            except Exception as e:
                logging.error("Error on page %d: %s", page, e)
                break
            time.sleep(self.polite_delay)

        if progress:
            progress(f"Collected {len(all_rows)} rows (API total said {total}).")
        return all_rows
