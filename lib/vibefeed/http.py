import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Some state sites reject non-browser user agents.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
TIMEOUT = 60


class _TimeoutSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", TIMEOUT)
        return super().request(*args, **kwargs)


def http_session() -> requests.Session:
    s = _TimeoutSession()
    s.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=3, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    return s
