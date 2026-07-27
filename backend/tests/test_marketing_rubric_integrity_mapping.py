"""Unit tests: rubric IntegrityError mapping (no global exception framework)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.marketing.exceptions import MarketingRubricDuplicateError
from app.modules.marketing.schemas import RubricCreate
from app.modules.marketing.service.rubrics import (
    MarketingRubricService,
    _is_rubric_code_unique_violation,
)


class _FakeOrig:
    def __init__(
        self,
        *,
        sqlstate: str | None = None,
        constraint_name: str | None = None,
        message: str = "integrity",
    ):
        self.sqlstate = sqlstate
        self.pgcode = sqlstate
        self.diag = SimpleNamespace(constraint_name=constraint_name)
        self._message = message

    def __str__(self) -> str:
        return self._message


def test_unique_violation_on_rubric_code_maps_true():
    exc = IntegrityError(
        "stmt",
        {},
        _FakeOrig(
            sqlstate="23505",
            constraint_name="uq_marketing_rubrics_tenant_code",
            message='duplicate key value violates unique constraint "uq_marketing_rubrics_tenant_code"',
        ),
    )
    assert _is_rubric_code_unique_violation(exc) is True


def test_not_null_violation_maps_false():
    exc = IntegrityError(
        "stmt",
        {},
        _FakeOrig(
            sqlstate="23502",
            constraint_name=None,
            message='null value in column "created_at" of relation "marketing_rubrics"',
        ),
    )
    assert _is_rubric_code_unique_violation(exc) is False


def test_other_unique_constraint_maps_false():
    exc = IntegrityError(
        "stmt",
        {},
        _FakeOrig(
            sqlstate="23505",
            constraint_name="marketing_rubrics_pkey",
            message='duplicate key value violates unique constraint "marketing_rubrics_pkey"',
        ),
    )
    assert _is_rubric_code_unique_violation(exc) is False


def test_create_rubric_not_null_integrity_is_not_duplicate():
    db = MagicMock()
    repo = MagicMock()
    repo.get_rubric_by_code.return_value = None
    repo.create_rubric.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakeOrig(sqlstate="23502", message="null value in column created_at"),
    )

    service = MarketingRubricService(db, uuid.uuid4())
    service.repo = repo
    user = SimpleNamespace(id=uuid.uuid4())
    payload = RubricCreate(code="offer", name="Offer")

    with pytest.raises(IntegrityError):
        service.create_rubric(user, payload)

    db.rollback.assert_called_once()


def test_create_rubric_unique_integrity_is_duplicate():
    db = MagicMock()
    repo = MagicMock()
    repo.get_rubric_by_code.return_value = None
    repo.create_rubric.side_effect = IntegrityError(
        "INSERT",
        {},
        _FakeOrig(
            sqlstate="23505",
            constraint_name="uq_marketing_rubrics_tenant_code",
            message="uq_marketing_rubrics_tenant_code",
        ),
    )

    service = MarketingRubricService(db, uuid.uuid4())
    service.repo = repo
    user = SimpleNamespace(id=uuid.uuid4())
    payload = RubricCreate(code="offer", name="Offer")

    with pytest.raises(MarketingRubricDuplicateError):
        service.create_rubric(user, payload)

    db.rollback.assert_called_once()
