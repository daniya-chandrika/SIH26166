"""
Local Mock Supabase Storage and PostgreSQL Database Emulator.
Enables offline testing, CI automation, and hermetic verification of repository and storage logic.
"""
import copy
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class MockSupabaseStorage:
    """
    File-system backed storage emulator mimicking Supabase Storage API.
    """

    def __init__(self, base_dir: str | Path = "./data/supabase_storage_mock"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Initialize default buckets
        for b in ["lunar-raw", "lunar-metadata", "lunar-processed", "lunar-results"]:
            (self.base_dir / b).mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        bucket: str,
        storage_path: str,
        file_data: Union[bytes, Path],
        content_type: str = "application/octet-stream",
        upsert: bool = True
    ) -> Dict[str, Any]:
        bucket_dir = self.base_dir / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        dest_file = bucket_dir / storage_path.lstrip("/")
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_data, Path):
            shutil.copy2(file_data, dest_file)
        elif isinstance(file_data, bytes):
            dest_file.write_bytes(file_data)
        else:
            raise ValueError("Unsupported file_data type")

        return {
            "Key": f"{bucket}/{storage_path.lstrip('/')}",
            "Id": str(uuid.uuid4()),
            "size": dest_file.stat().st_size
        }

    def create_signed_url(self, bucket: str, storage_path: str, expires_in_seconds: int = 3600) -> str:
        clean_path = storage_path.lstrip("/")
        token = uuid.uuid4().hex[:16]
        return f"https://mock-supabase.local/storage/v1/object/sign/{bucket}/{clean_path}?token={token}&expires={expires_in_seconds}"

    def download_bytes(self, bucket: str, storage_path: str) -> bytes:
        target = self.base_dir / bucket / storage_path.lstrip("/")
        if not target.exists():
            raise FileNotFoundError(f"Storage object not found: {bucket}/{storage_path}")
        return target.read_bytes()

    def exists(self, bucket: str, storage_path: str) -> bool:
        return (self.base_dir / bucket / storage_path.lstrip("/")).exists()


class MockSupabaseDB:
    """
    JSON-persisted or in-memory database emulator mimicking PostgreSQL / Supabase PostgREST tables.
    """

    def __init__(self, persistence_file: Optional[Union[str, Path]] = None):
        self.persistence_file = Path(persistence_file).resolve() if persistence_file else None
        self.tables: Dict[str, List[Dict[str, Any]]] = {
            "regions": [],
            "images": [],
            "image_metadata": [],
            "image_quality": [],
            "image_footprints": [],
            "image_pairs": [],
            "experiments": [],
            "processing_logs": []
        }
        self._load_or_seed()

    def _load_or_seed(self):
        if self.persistence_file and self.persistence_file.exists():
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self.tables:
                            self.tables[k] = v
                    if self.tables["regions"]:
                        return
            except Exception:
                pass
        self._seed_regions()
        self._save()

    def _save(self):
        if self.persistence_file:
            try:
                self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.persistence_file, "w", encoding="utf-8") as f:
                    json.dump(self.tables, f, indent=2)
            except Exception:
                pass

    def _seed_regions(self):
        default_regions = [
            ("R01", "South Pole - Shackleton Rim", -89.90, 0.00),
            ("R02", "South Pole - Faustini / Shoemaker", -87.10, 84.30),
            ("R03", "Tycho Crater Central Peak", -43.31, -11.36),
            ("R04", "Mare Tranquillitatis - Apollo 11", 0.67, 23.47),
            ("R05", "Oceanus Procellarum - Aristarchus", 23.70, -47.40),
            ("R06", "South Pole-Aitken Basin Interior", -53.00, 169.00),
            ("R07", "Mare Imbrium - Archimedes Crater", 29.70, -4.00),
            ("R08", "Copernicus Crater Rim and Floor", 9.62, -20.08),
            ("R09", "Mare Serenitatis - Posidonius", 31.80, 29.90),
            ("R10", "Hertzsprung Basin Far-Side", 1.60, -128.60)
        ]
        for code, name, lat, lon in default_regions:
            if not any(r.get("region_code") == code for r in self.tables["regions"]):
                self.tables["regions"].append({
                    "id": str(uuid.uuid4()),
                    "region_code": code,
                    "region_name": name,
                    "description": f"Lunar region {name}",
                    "center_latitude": lat,
                    "center_longitude": lon,
                    "created_at": datetime.utcnow().isoformat() + "Z"
                })

    def select(self, table: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._load_or_seed()
        rows = self.tables.get(table, [])
        if not filters:
            return copy.deepcopy(rows)

        filtered = []
        for r in rows:
            match = True
            for k, v in filters.items():
                expected = v[3:] if isinstance(v, str) and v.startswith("eq.") else v
                if str(r.get(k)) != str(expected):
                    match = False
                    break
            if match:
                filtered.append(copy.deepcopy(r))
        return filtered

    def insert(self, table: str, records: Union[Dict[str, Any], List[Dict[str, Any]]], upsert: bool = False) -> List[Dict[str, Any]]:
        self._load_or_seed()
        rec_list = [records] if isinstance(records, dict) else records
        inserted = []
        for rec in rec_list:
            row = copy.deepcopy(rec)
            if "id" not in row or not row["id"]:
                row["id"] = str(uuid.uuid4())
            if "created_at" not in row:
                row["created_at"] = datetime.utcnow().isoformat() + "Z"

            if upsert and table == "images" and "sha256" in row:
                existing_idx = next((i for i, r in enumerate(self.tables[table]) if r.get("sha256") == row["sha256"]), None)
                if existing_idx is not None:
                    self.tables[table][existing_idx].update(row)
                    inserted.append(self.tables[table][existing_idx])
                    continue

            self.tables[table].append(row)
            inserted.append(row)
        self._save()
        return copy.deepcopy(inserted)

    def update(self, table: str, update_data: Dict[str, Any], match_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._load_or_seed()
        updated = []
        for r in self.tables.get(table, []):
            match = True
            for k, v in match_params.items():
                expected = v[3:] if isinstance(v, str) and v.startswith("eq.") else v
                if str(r.get(k)) != str(expected):
                    match = False
                    break
            if match:
                r.update(update_data)
                updated.append(copy.deepcopy(r))
        self._save()
        return updated

    def delete(self, table: str, match_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self._load_or_seed()
        to_delete = []
        remaining = []
        for r in self.tables.get(table, []):
            match = True
            for k, v in match_params.items():
                expected = v[3:] if isinstance(v, str) and v.startswith("eq.") else v
                if str(r.get(k)) != str(expected):
                    match = False
                    break
            if match:
                to_delete.append(r)
            else:
                remaining.append(r)
        self.tables[table] = remaining
        self._save()
        return to_delete
