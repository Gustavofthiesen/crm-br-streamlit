"""Repository helpers with audit logging."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from .models import AuditLog


def serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def model_to_dict(instance: Any, include_private: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in inspect(instance).mapper.column_attrs:
        key = column.key
        if not include_private and key == "password_hash":
            continue
        data[key] = serialize_value(getattr(instance, key))
    return data


def _json_dump(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


class CRUDRepository:
    def __init__(
        self,
        session: Session,
        model: type,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> None:
        self.session = session
        self.model = model
        self.user_id = user_id
        self.ip_address = ip_address

    def list(self, limit: int = 500) -> list[Any]:
        statement = select(self.model)
        if hasattr(self.model, "id"):
            statement = statement.order_by(self.model.id.desc())
        return list(self.session.scalars(statement.limit(limit)).all())

    def get(self, record_id: int) -> Any | None:
        return self.session.get(self.model, record_id)

    def create(self, data: dict[str, Any]) -> Any:
        cleaned = self._clean_payload(data)
        record = self.model(**cleaned)
        try:
            self.session.add(record)
            self.session.flush()
            self._add_audit("create", None, model_to_dict(record))
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def update(self, record_id: int, data: dict[str, Any]) -> Any:
        record = self.get(record_id)
        if record is None:
            raise ValueError("Registro não encontrado.")

        old_values = model_to_dict(record)
        cleaned = self._clean_payload(data)
        for key, value in cleaned.items():
            setattr(record, key, value)

        try:
            self.session.flush()
            self._add_audit("update", old_values, model_to_dict(record))
            self.session.commit()
            self.session.refresh(record)
            return record
        except Exception:
            self.session.rollback()
            raise

    def delete(self, record_id: int) -> None:
        record = self.get(record_id)
        if record is None:
            raise ValueError("Registro não encontrado.")
        old_values = model_to_dict(record)
        try:
            self.session.delete(record)
            self._add_audit("delete", old_values, None, entity_id=record_id)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _clean_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        ignored = {"id", "created_at", "updated_at"}
        return {key: value for key, value in data.items() if key not in ignored}

    def _add_audit(
        self,
        action: str,
        old_values: dict[str, Any] | None,
        new_values: dict[str, Any] | None,
        entity_id: int | None = None,
    ) -> None:
        if self.model is AuditLog:
            return
        if entity_id is None and new_values:
            entity_id = new_values.get("id")
        log = AuditLog(
            user_id=self.user_id,
            entity_type=self.model.__tablename__,
            entity_id=entity_id,
            action=action,
            old_values=_json_dump(old_values),
            new_values=_json_dump(new_values),
            ip_address=self.ip_address,
        )
        self.session.add(log)


def rows_to_dicts(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [model_to_dict(row) for row in rows]
