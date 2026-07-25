#!/usr/bin/env python3
"""Copy legacy backend/uploads media to R2. Dry-run is the default and never deletes."""

from __future__ import annotations

import argparse
import hashlib
import json

from sqlalchemy import JSON, bindparam, text

from app.core.config import settings
from app.database import SessionLocal
from app.services.storage import UPLOAD_DIR, _r2_client, store_upload


SCALAR_REFERENCE_COLUMNS = {
    "generated_ads": ("image_url", "video_url", "thumbnail_url"),
    "facebook_ads": ("image_url", "video_url", "thumbnail_url"),
    "winning_ads": ("image_url",),
    "ai_personas": ("base_image_url",),
}
JSON_REFERENCE_COLUMNS = {
    "brand_scraped_ads": ("media_urls",),
    "products": ("product_shots",),
}


def local_name(reference: str) -> str | None:
    if not reference or not reference.startswith("/uploads/"):
        return None
    name = reference.removeprefix("/uploads/")
    return name if name and "/" not in name and "\\" not in name else None


def planned_rows(db):
    for table, columns in SCALAR_REFERENCE_COLUMNS.items():
        for column in columns:
            for row in db.execute(text(f"SELECT id, {column} FROM {table} WHERE {column} LIKE '/uploads/%'")):
                filename = local_name(row[1])
                if filename:
                    yield table, column, str(row[0]), filename, "scalar"
    for table, columns in JSON_REFERENCE_COLUMNS.items():
        for column in columns:
            for row in db.execute(text(f"SELECT id, {column} FROM {table} WHERE {column} IS NOT NULL")):
                for reference in local_references(row[1]):
                    filename = local_name(reference)
                    if filename:
                        yield table, column, str(row[0]), filename, "json"


def local_references(value) -> set[str]:
    if isinstance(value, str):
        return {value} if local_name(value) else set()
    if isinstance(value, list):
        return set().union(*(local_references(item) for item in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(local_references(item) for item in value.values())) if value else set()
    return set()


def replace_reference(value, old: str, new: str):
    if isinstance(value, str):
        return new if value == old else value
    if isinstance(value, list):
        return [replace_reference(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: replace_reference(item, old, new) for key, item in value.items()}
    return value


def fingerprint(stream) -> dict:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
    return {"size": size, "sha256": digest.hexdigest()}


def remote_fingerprint(client, filename: str) -> dict | None:
    try:
        head = client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=filename)
        body = client.get_object(Bucket=settings.R2_BUCKET_NAME, Key=filename)["Body"]
        result = fingerprint(body)
        if result["size"] != head["ContentLength"]:
            raise RuntimeError("R2 object size changed while verifying")
        return result
    except Exception as error:
        if getattr(error, "response", {}).get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def migrate(apply: bool) -> dict:
    if apply and not settings.r2_enabled:
        raise RuntimeError("R2 must be fully configured before --apply")
    db = SessionLocal()
    items, exceptions = [], []
    client = _r2_client() if settings.r2_enabled else None
    try:
        for table, column, record_id, filename, reference_kind in planned_rows(db):
            source = UPLOAD_DIR / filename
            item = {"table": table, "column": column, "id": record_id, "filename": filename, "action": "would-copy"}
            if not source.is_file():
                item["exception"] = "local source is missing"
                exceptions.append(item)
                items.append(item)
                continue
            with source.open("rb") as media:
                item["local"] = fingerprint(media)
            if not client:
                item["remote"] = None
                item["verified"] = False
                item["exception"] = "R2 is not configured; remote checksum is unavailable"
                exceptions.append(item)
                items.append(item)
                continue
            item["remote"] = remote_fingerprint(client, filename)
            item["verified"] = item["local"] == item["remote"]
            if apply:
                if not item["verified"]:
                    with source.open("rb") as media:
                        store_upload(media, filename)
                    item["remote"] = remote_fingerprint(client, filename)
                    item["verified"] = item["local"] == item["remote"]
                if item["verified"]:
                    destination = f"{settings.R2_PUBLIC_URL.rstrip('/')}/{filename}"
                    source_reference = f"/uploads/{filename}"
                    if reference_kind == "scalar":
                        db.execute(text(f"UPDATE {table} SET {column} = :destination WHERE id = :id"), {"destination": destination, "id": record_id})
                    else:
                        current = db.execute(text(f"SELECT {column} FROM {table} WHERE id = :id"), {"id": record_id}).scalar_one()
                        rewritten = replace_reference(current, source_reference, destination)
                        statement = text(f"UPDATE {table} SET {column} = :reference WHERE id = :id").bindparams(bindparam("reference", type_=JSON))
                        db.execute(statement, {"reference": rewritten, "id": record_id})
                    item.update({"action": "copied", "destination": destination})
                else:
                    item["exception"] = "R2 checksum or size did not match local source"
                    exceptions.append(item)
            items.append(item)
        if apply:
            db.commit()
        return {"items": items, "exceptions": exceptions}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Copy verified local media and rewrite its database reference")
    args = parser.parse_args()
    print(json.dumps({"mode": "apply" if args.apply else "dry-run", **migrate(args.apply), "deletions": 0}, indent=2))


if __name__ == "__main__":
    main()
