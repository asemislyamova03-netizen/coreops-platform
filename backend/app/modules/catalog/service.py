import uuid

from sqlalchemy.orm import Session

from app.core.enums import CatalogItemType
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.catalog.models import ENTITY_CATALOG_ITEM
from app.modules.catalog.repository import CatalogRepository
from app.modules.catalog.schemas import (
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    PriceListCreate,
    PriceListItemCreate,
    PriceListItemResponse,
    PriceListResponse,
    PriceListUpdate,
    UnitOfMeasureCreate,
    UnitOfMeasureResponse,
)
from app.modules.parties.custom_fields import CustomFieldService


class CatalogService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = CatalogRepository(db)
        self.custom_fields = CustomFieldService(db, tenant_id)

    def list_units(self) -> list[UnitOfMeasureResponse]:
        return [UnitOfMeasureResponse.model_validate(u) for u in self.repo.list_units(self.tenant_id)]

    def create_unit(self, payload: UnitOfMeasureCreate) -> UnitOfMeasureResponse:
        units = self.repo.list_units(self.tenant_id)
        if any(u.code == payload.code for u in units):
            raise ConflictError("Unit code already exists")

        unit = self.repo.create_unit(
            tenant_id=self.tenant_id,
            code=payload.code,
            name=payload.name,
            symbol=payload.symbol,
        )
        return UnitOfMeasureResponse.model_validate(unit)

    def list_items(self, **filters) -> list[CatalogItemResponse]:
        items = self.repo.list_items(self.tenant_id, **filters)
        return [self._to_item_response(item) for item in items]

    def get_item(self, item_id: uuid.UUID) -> CatalogItemResponse:
        item = self._get_item_or_404(item_id)
        return self._to_item_response(item)

    def create_item(self, user: User, payload: CatalogItemCreate) -> CatalogItemResponse:
        if payload.sku:
            if self.repo.get_item_by_sku(self.tenant_id, payload.sku):
                raise ConflictError("SKU already exists")

        if payload.unit_id:
            if not self.repo.get_unit(self.tenant_id, payload.unit_id):
                raise NotFoundError("Unit of measure not found")

        custom_values = self.custom_fields.validate_and_prepare(
            ENTITY_CATALOG_ITEM, payload.custom_fields
        )

        item = self.repo.create_item(
            tenant_id=self.tenant_id,
            item_type=payload.item_type,
            name=payload.name,
            description=payload.description,
            sku=payload.sku,
            unit_id=payload.unit_id,
            base_price=payload.base_price,
            currency=payload.currency,
            is_active=payload.is_active,
            custom_fields_json={},
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        if custom_values:
            self.custom_fields.upsert_values(ENTITY_CATALOG_ITEM, item.id, custom_values)

        self.db.flush()
        return self.get_item(item.id)

    def update_item(
        self,
        user: User,
        item_id: uuid.UUID,
        payload: CatalogItemUpdate,
    ) -> CatalogItemResponse:
        item = self._get_item_or_404(item_id)

        if payload.sku and payload.sku != item.sku:
            if self.repo.get_item_by_sku(self.tenant_id, payload.sku):
                raise ConflictError("SKU already exists")

        if payload.unit_id is not None:
            if payload.unit_id and not self.repo.get_unit(self.tenant_id, payload.unit_id):
                raise NotFoundError("Unit of measure not found")
            item.unit_id = payload.unit_id

        for field in (
            "item_type",
            "name",
            "description",
            "sku",
            "base_price",
            "currency",
            "is_active",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(item, field, value)

        if payload.custom_fields is not None:
            custom_values = self.custom_fields.validate_and_prepare(
                ENTITY_CATALOG_ITEM, payload.custom_fields
            )
            self.custom_fields.upsert_values(ENTITY_CATALOG_ITEM, item.id, custom_values)

        item.updated_by_user_id = user.id
        self.db.flush()
        return self.get_item(item.id)

    def delete_item(self, item_id: uuid.UUID) -> None:
        item = self._get_item_or_404(item_id)
        self.repo.delete_item(item)
        self.db.flush()

    def list_price_lists(self) -> list[PriceListResponse]:
        return [self._to_price_list_response(pl) for pl in self.repo.list_price_lists(self.tenant_id)]

    def get_price_list(self, price_list_id: uuid.UUID) -> PriceListResponse:
        price_list = self._get_price_list_or_404(price_list_id)
        return self._to_price_list_response(price_list)

    def create_price_list(self, user: User, payload: PriceListCreate) -> PriceListResponse:
        if self.repo.get_price_list_by_code(self.tenant_id, payload.code):
            raise ConflictError("Price list code already exists")

        price_list = self.repo.create_price_list(
            tenant_id=self.tenant_id,
            code=payload.code,
            name=payload.name,
            currency=payload.currency,
            is_active=payload.is_active,
            valid_from=payload.valid_from,
            valid_to=payload.valid_to,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self.db.flush()
        return self.get_price_list(price_list.id)

    def update_price_list(
        self,
        user: User,
        price_list_id: uuid.UUID,
        payload: PriceListUpdate,
    ) -> PriceListResponse:
        price_list = self._get_price_list_or_404(price_list_id)

        if payload.name is not None:
            price_list.name = payload.name
        if payload.currency is not None:
            price_list.currency = payload.currency
        if payload.is_active is not None:
            price_list.is_active = payload.is_active
        if payload.valid_from is not None:
            price_list.valid_from = payload.valid_from
        if payload.valid_to is not None:
            price_list.valid_to = payload.valid_to

        price_list.updated_by_user_id = user.id
        self.db.flush()
        return self.get_price_list(price_list.id)

    def add_price_list_item(
        self,
        price_list_id: uuid.UUID,
        payload: PriceListItemCreate,
    ) -> PriceListItemResponse:
        price_list = self._get_price_list_or_404(price_list_id)
        item = self._get_item_or_404(payload.catalog_item_id)

        if self.repo.get_price_list_item(price_list.id, item.id):
            raise ConflictError("Catalog item already exists in this price list")

        row = self.repo.add_price_list_item(
            tenant_id=self.tenant_id,
            price_list_id=price_list.id,
            catalog_item_id=item.id,
            price=payload.price,
            min_quantity=payload.min_quantity,
        )
        self.db.flush()
        return PriceListItemResponse(
            id=row.id,
            catalog_item_id=item.id,
            catalog_item_name=item.name,
            price=row.price,
            min_quantity=row.min_quantity,
        )

    def _get_item_or_404(self, item_id: uuid.UUID):
        item = self.repo.get_item(self.tenant_id, item_id)
        if not item:
            raise NotFoundError("Catalog item not found")
        return item

    def _get_price_list_or_404(self, price_list_id: uuid.UUID):
        price_list = self.repo.get_price_list(self.tenant_id, price_list_id)
        if not price_list:
            raise NotFoundError("Price list not found")
        return price_list

    def _to_item_response(self, item) -> CatalogItemResponse:
        custom = self.custom_fields.get_values_map(ENTITY_CATALOG_ITEM, item.id)
        return CatalogItemResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            item_type=item.item_type,
            name=item.name,
            description=item.description,
            sku=item.sku,
            unit_id=item.unit_id,
            base_price=item.base_price,
            currency=item.currency,
            is_active=item.is_active,
            custom_fields=custom,
            unit=item.unit,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _to_price_list_response(self, price_list) -> PriceListResponse:
        items = [
            PriceListItemResponse(
                id=row.id,
                catalog_item_id=row.catalog_item_id,
                catalog_item_name=row.catalog_item.name,
                price=row.price,
                min_quantity=row.min_quantity,
            )
            for row in price_list.items
        ]
        return PriceListResponse(
            id=price_list.id,
            tenant_id=price_list.tenant_id,
            code=price_list.code,
            name=price_list.name,
            currency=price_list.currency,
            is_active=price_list.is_active,
            valid_from=price_list.valid_from,
            valid_to=price_list.valid_to,
            items=items,
            created_at=price_list.created_at,
        )
