import logging
from typing import Any
from ratelimit import limits, sleep_and_retry
from pubchem_api_crawler.config import settings

import requests

LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36",
    "Accept": "application/json",
    "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
    "Accept-Encoding": "none",
    "Accept-Language": "en-US,en;q=0.8",
    "Connection": "keep-alive",
}


@sleep_and_retry
@limits(calls=settings.rate_limit_calls, period=settings.rate_limit_period)
def _send_rest_query(url: str, post_data: Any | None = None) -> dict[str, Any]:
    """
    Send REST API query

    Args:
        url (str): the query url

    Returns:
        dict[str, Any]: the query JSON response
    """
    LOGGER.debug(f"Query url: {url}")
    if post_data:
        r = requests.post(url, headers=HEADERS, data=post_data)
    else:
        r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    try:
        LOGGER.debug(r.headers["X-Throttling-Control"])
    except KeyError:
        pass
    return r.json()
