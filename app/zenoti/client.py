"""Async Zenoti API client with API-key and JWT auth support."""
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ZenotiAuthError(Exception):
    pass


class ZenotiAPIError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"Zenoti API {status}: {message}")


class ZenotiClient:
    def __init__(self):
        self._base = settings.zenoti_base_url.rstrip("/")
        self._api_key = settings.zenoti_api_key
        self._jwt_token: str | None = None
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def __aenter__(self):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self._http = httpx.AsyncClient(base_url=self._base, headers=headers, timeout=30)
        if not self._api_key and settings.zenoti_client_id:
            await self._authenticate_jwt()
        return self

    async def __aexit__(self, *_):
        if self._http:
            await self._http.aclose()

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"apikey {self._api_key}"}
        if self._jwt_token:
            return {"Authorization": f"bearer {self._jwt_token}"}
        raise ZenotiAuthError("No Zenoti credentials configured. Set ZENOTI_API_KEY in .env")

    async def _authenticate_jwt(self):
        """Exchange client credentials for a JWT bearer token."""
        resp = await self._http.post(
            "/connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.zenoti_client_id,
                "client_secret": settings.zenoti_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        self._jwt_token = resp.json()["access_token"]

    # ------------------------------------------------------------------ #
    # Low-level request helper
    # ------------------------------------------------------------------ #

    async def _get(self, path: str, params: dict | None = None) -> Any:
        resp = await self._http.get(path, params=params, headers=self._auth_headers())
        if resp.status_code == 401:
            raise ZenotiAuthError("Invalid or expired Zenoti credentials.")
        if not resp.is_success:
            raise ZenotiAPIError(resp.status_code, resp.text[:400])
        return resp.json()

    async def _paginate(self, path: str, params: dict | None = None, result_key: str = "objects") -> list[dict]:
        """Yield all pages from a paginated Zenoti endpoint."""
        params = dict(params or {})
        params.setdefault("page", 0)
        params.setdefault("size", settings.sync_page_size)
        results: list[dict] = []
        while True:
            data = await self._get(path, params)
            # Zenoti wraps results either in data[result_key] or data directly
            page_items: list = (
                data.get(result_key)
                or data.get("appointments")
                or data.get("guests")
                or data.get("invoices")
                or data.get("employees")
                or data.get("services")
                or data.get("centers")
                or (data if isinstance(data, list) else [])
            )
            if not page_items:
                break
            results.extend(page_items)
            if len(page_items) < params["size"]:
                break
            params["page"] += 1
        return results

    # ------------------------------------------------------------------ #
    # Public API methods
    # ------------------------------------------------------------------ #

    async def get_centers(self) -> list[dict]:
        data = await self._get("/centers")
        return data.get("centers") or data.get("objects") or []

    async def get_guests(self, center_id: str) -> list[dict]:
        return await self._paginate(
            f"/centers/{center_id}/guests",
            result_key="guests",
        )

    async def get_employees(self, center_id: str) -> list[dict]:
        return await self._paginate(
            f"/centers/{center_id}/employees",
            result_key="employees",
        )

    async def get_services(self, center_id: str) -> list[dict]:
        return await self._paginate(
            f"/centers/{center_id}/catalog/services",
            result_key="services",
        )

    async def get_appointments(self, center_id: str, start_date: str, end_date: str) -> list[dict]:
        """start_date / end_date: 'YYYY-MM-DD'."""
        return await self._paginate(
            f"/centers/{center_id}/appointments",
            params={"start_date": start_date, "end_date": end_date},
            result_key="appointments",
        )

    async def get_invoices(self, center_id: str, start_date: str, end_date: str) -> list[dict]:
        return await self._paginate(
            f"/invoices",
            params={"center_id": center_id, "start_date": start_date, "end_date": end_date},
            result_key="invoices",
        )
