from typing import Any, Dict, List, Optional, Type, TypeVar, Union, overload
from pydantic import BaseModel, ValidationError
import aiohttp
import logging
import ssl
import certifi

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


@overload
async def fetch(
    url: str,
    model: Type[T],
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    is_list: bool = False,
    timeout: float = 10.0,
) -> T: ...
@overload
async def fetch(
    url: str,
    model: Type[T],
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    is_list: bool = True,
    timeout: float = 10.0,
) -> List[T]: ...
@overload
async def fetch(
    url: str,
    model: None = None,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    is_list: bool = False,
    timeout: float = 10.0,
) -> Dict[str, Any]: ...
@overload
async def fetch(
    url: str,
    model: None = None,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    is_list: bool = True,
    timeout: float = 10.0,
) -> List[Dict[str, Any]]: ...


async def fetch(
    url: str,
    model: Optional[Type[T]] = None,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    is_list: bool = False,
    timeout: float = 10.0,
) -> Union[T, List[T], Dict[str, Any], List[Dict[str, Any]]]:
    """Async, type-safe HTTP fetcher using aiohttp."""
    headers = headers or {}
    method = method.upper()

    # Create SSL context with certifi certificates
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout),
        connector=aiohttp.TCPConnector(ssl=ssl_context),
    ) as session:
        try:
            async with session.request(
                method, url, headers=headers, params=params, json=json
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if model is None:
                    return data

                if is_list:
                    return [model(**item) for item in data]  # type: ignore
                return model(**data)

        except aiohttp.ClientResponseError as e:
            logger.error("HTTP error %s: %s", e.status, e.message)
        except aiohttp.ClientError as e:
            logger.error("Network error: %s | URL: %s %s", e, method, url)
        except ValidationError as e:
            logger.error("Validation error: %s | URL: %s %s", e, method, url)
        except Exception as e:
            logger.error("Unexpected error: %s | URL: %s %s", e, method, url)

    return None  # type: ignore
