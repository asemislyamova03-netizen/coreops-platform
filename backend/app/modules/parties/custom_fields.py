import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CustomFieldType
from app.core.exceptions import ConflictError
from app.modules.parties.models import CustomFieldDefinition, CustomFieldValue, ENTITY_PARTY


class CustomFieldService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    def list_definitions(self, entity_type: str) -> list[CustomFieldDefinition]:
        stmt = (
            select(CustomFieldDefinition)
            .where(
                CustomFieldDefinition.tenant_id == self.tenant_id,
                CustomFieldDefinition.entity_type == entity_type,
            )
            .order_by(CustomFieldDefinition.sort_order)
        )
        return list(self.db.scalars(stmt).all())

    def get_values_map(self, entity_type: str, entity_id: uuid.UUID) -> dict[str, Any]:
        stmt = select(CustomFieldValue).where(
            CustomFieldValue.tenant_id == self.tenant_id,
            CustomFieldValue.entity_type == entity_type,
            CustomFieldValue.entity_id == entity_id,
        )
        rows = self.db.scalars(stmt).all()
        return {row.field_key: row.value_json.get("value") for row in rows}

    def validate_and_prepare(
        self,
        entity_type: str,
        values: dict[str, Any] | None,
        *,
        applies_to: dict | None = None,
    ) -> dict[str, Any]:
        if not values:
            values = {}

        definitions = self.list_definitions(entity_type)
        if applies_to:
            definitions = [
                d
                for d in definitions
                if not d.applies_to_json or _matches_applies_to(d.applies_to_json, applies_to)
            ]

        allowed_keys = {d.field_key for d in definitions}
        unknown = set(values.keys()) - allowed_keys
        if unknown:
            raise ConflictError(f"Unknown custom fields: {', '.join(sorted(unknown))}")

        prepared: dict[str, Any] = {}
        for definition in definitions:
            if definition.field_key not in values:
                if definition.is_required:
                    raise ConflictError(f"Required custom field missing: {definition.field_key}")
                continue
            prepared[definition.field_key] = _coerce_value(
                values[definition.field_key],
                definition.field_type,
                definition,
            )

        return prepared

    def upsert_values(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        values: dict[str, Any],
    ) -> None:
        for field_key, value in values.items():
            existing = self.db.scalar(
                select(CustomFieldValue).where(
                    CustomFieldValue.tenant_id == self.tenant_id,
                    CustomFieldValue.entity_type == entity_type,
                    CustomFieldValue.entity_id == entity_id,
                    CustomFieldValue.field_key == field_key,
                )
            )
            payload = {"value": value}
            if existing:
                existing.value_json = payload
            else:
                self.db.add(
                    CustomFieldValue(
                        tenant_id=self.tenant_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        field_key=field_key,
                        value_json=payload,
                    )
                )
        self.db.flush()


def _matches_applies_to(definition_filter: dict, context: dict) -> bool:
    return all(context.get(key) == val for key, val in definition_filter.items())


def _coerce_value(raw: Any, field_type: str, definition: CustomFieldDefinition) -> Any:
    if raw is None:
        return None

    try:
        ftype = CustomFieldType(field_type)
    except ValueError:
        ftype = None

    if ftype == CustomFieldType.STRING:
        return str(raw)
    if ftype == CustomFieldType.TEXT:
        return str(raw)
    if ftype == CustomFieldType.NUMBER:
        return float(raw)
    if ftype == CustomFieldType.MONEY:
        return str(Decimal(str(raw)))
    if ftype == CustomFieldType.BOOLEAN:
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("1", "true", "yes", "on")
    if ftype == CustomFieldType.DATE:
        if isinstance(raw, date):
            return raw.isoformat()
        return str(raw)
    if ftype == CustomFieldType.DATETIME:
        if isinstance(raw, datetime):
            return raw.isoformat()
        return str(raw)
    if ftype == CustomFieldType.SELECT:
        options = definition.options_json.get("choices", [])
        if options and raw not in options:
            raise ConflictError(
                f"Invalid value for '{definition.field_key}': must be one of {options}"
            )
        return raw
    if ftype == CustomFieldType.MULTI_SELECT:
        if not isinstance(raw, list):
            raise ConflictError(f"Field '{definition.field_key}' expects a list")
        return raw
    if ftype in (CustomFieldType.JSON, CustomFieldType.REFERENCE, CustomFieldType.FILE):
        return raw

    return raw
