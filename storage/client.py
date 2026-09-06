"""
Supabase REST and Storage API Client.
Handles authentication, Storage endpoints, and PostgREST interactions via requests.
"""
import os
import io
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
import requests


class SupabaseAPIClient:
    """
    Direct HTTP client for Supabase REST (PostgREST) and Storage APIs.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        service_role_key: Optional[str] = None,
        timeout_seconds: int = 30
    ):
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.anon_key = supabase_key or os.getenv("SUPABASE_ANON_KEY", "")
        self.service_role_key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.active_key = self.service_role_key or self.anon_key
        self.timeout = timeout_seconds

        self.rest_url = f"{self.supabase_url}/rest/v1" if self.supabase_url else ""
        self.storage_url = f"{self.supabase_url}/storage/v1" if self.supabase_url else ""

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.active_key and not self.supabase_url.startswith("https://your-project"))

    def _get_headers(self, is_storage: bool = False, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.active_key,
            "Authorization": f"Bearer {self.active_key}"
        }
        if not is_storage:
            headers["Content-Type"] = "application/json"
            headers["Prefer"] = "return=representation"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    # --------------------------------------------------------------------------
    # POSTGREST TABLE METHODS
    # --------------------------------------------------------------------------
    def table_select(self, table: str, query_params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")
        url = f"{self.rest_url}/{table}"
        response = requests.get(url, headers=self._get_headers(), params=query_params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def table_insert(self, table: str, records: Union[Dict[str, Any], List[Dict[str, Any]]], upsert: bool = False) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")
        url = f"{self.rest_url}/{table}"
        headers = self._get_headers()
        if upsert:
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = requests.post(url, headers=headers, json=records, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def table_update(self, table: str, update_data: Dict[str, Any], match_params: Dict[str, str]) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")
        url = f"{self.rest_url}/{table}"
        response = requests.patch(url, headers=self._get_headers(), json=update_data, params=match_params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def table_delete(self, table: str, match_params: Dict[str, str]) -> List[Dict[str, Any]]:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")
        url = f"{self.rest_url}/{table}"
        response = requests.delete(url, headers=self._get_headers(), params=match_params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # --------------------------------------------------------------------------
    # STORAGE METHODS
    # --------------------------------------------------------------------------
    def storage_upload(
        self,
        bucket: str,
        storage_path: str,
        file_bytes: Union[bytes, io.BytesIO, Path],
        content_type: str = "application/octet-stream",
        upsert: bool = True
    ) -> Dict[str, Any]:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")

        clean_path = storage_path.lstrip("/")
        url = f"{self.storage_url}/object/{bucket}/{clean_path}"

        headers = self._get_headers(is_storage=True, extra_headers={
            "Content-Type": content_type,
            "x-upsert": "true" if upsert else "false"
        })

        if isinstance(file_bytes, Path):
            with open(file_bytes, "rb") as f:
                data = f.read()
        elif isinstance(file_bytes, io.BytesIO):
            data = file_bytes.getvalue()
        else:
            data = file_bytes

        response = requests.post(url, headers=headers, data=data, timeout=self.timeout)
        response.raise_for_status()
        return response.json() if response.content else {"Key": f"{bucket}/{clean_path}"}

    def storage_create_signed_url(self, bucket: str, storage_path: str, expires_in_seconds: int = 3600) -> str:
        if not self.is_configured:
            raise ConnectionError("Supabase client is not configured with valid URL and API keys.")
        clean_path = storage_path.lstrip("/")
        url = f"{self.storage_url}/object/sign/{bucket}/{clean_path}"
        headers = self._get_headers()
        payload = {"expiresIn": expires_in_seconds}
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        signed_path = data.get("signedURL", "")
        return f"{self.supabase_url}/storage/v1{signed_path}" if signed_path.startswith("/") else signed_path
