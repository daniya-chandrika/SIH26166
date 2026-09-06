"""
Supabase Database Connection Manager.
"""
from typing import Optional, Dict, Any, List, Union

from storage.client import SupabaseAPIClient
from storage.emulator import MockSupabaseDB


class SupabaseDBConnection:
    """
    Manages database access, transparently routing queries to live Supabase PostgREST
    or the in-memory MockSupabaseDB emulator when running tests or offline.
    """

    def __init__(
        self,
        api_client: Optional[SupabaseAPIClient] = None,
        use_mock: bool = False,
        mock_db: Optional[MockSupabaseDB] = None
    ):
        self.client = api_client or SupabaseAPIClient()
        self.use_mock = use_mock or (not self.client.is_configured)
        self.mock_db = mock_db or MockSupabaseDB()

    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if self.use_mock:
            return self.mock_db.select(table, filters)
        return self.client.table_select(table, filters)

    def insert(self, table: str, records: Union[Dict[str, Any], List[Dict[str, Any]]], upsert: bool = False) -> List[Dict[str, Any]]:
        if self.use_mock:
            return self.mock_db.insert(table, records, upsert=upsert)
        return self.client.table_insert(table, records, upsert=upsert)

    def update(self, table: str, update_data: Dict[str, Any], match_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.use_mock:
            return self.mock_db.update(table, update_data, match_params)
        return self.client.table_update(table, update_data, match_params)

    def delete(self, table: str, match_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.use_mock:
            return self.mock_db.delete(table, match_params)
        return self.client.table_delete(table, match_params)
