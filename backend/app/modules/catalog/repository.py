import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import CatalogItemType
from app.modules.catalog.models import CatalogItem, PriceList, PriceListItem, UnitOfMeasure


class CatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_units(self, tenant_id: uuid.UUID) -> list[UnitOfMeasure]:
        stmt = (
            select(UnitOfMeasure)
            .where(UnitOfMeasure.tenant_id == tenant_id)
            .order_by(UnitOfMeasure.name)
        )
        return list(self.db.scalars(stmt).all())

    def get_unit(self, tenant_id: uuid.UUID, unit_id: uuid.UUID) -> UnitOfMeasure | None:
        stmt = select(UnitOfMeasure).where(
            UnitOfMeasure.tenant_id == tenant_id,
            UnitOfMeasure.id == unit_id,
        )
        return self.db.scalar(stmt)

    def create_unit(self, **kwargs) -> UnitOfMeasure:
        unit = UnitOfMeasure(**kwargs)
        self.db.add(unit)
        self.db.flush()
        return unit

    def list_items(
        self,
        tenant_id: uuid.UUID,
        *,
        item_type: CatalogItemType | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[CatalogItem]:
        stmt = (
            select(CatalogItem)
            .where(CatalogItem.tenant_id == tenant_id)
            .options(selectinload(CatalogItem.unit))
            .order_by(CatalogItem.name)
            .offset(skip)
            .limit(limit)
        )
        if item_type:
            stmt = stmt.where(CatalogItem.item_type == item_type)
        if is_active is not None:
            stmt = stmt.where(CatalogItem.is_active.is_(is_active))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                CatalogItem.name.ilike(pattern) | CatalogItem.sku.ilike(pattern)
            )
        return list(self.db.scalars(stmt).all())

    def get_item(self, tenant_id: uuid.UUID, item_id: uuid.UUID) -> CatalogItem | None:
        stmt = (
            select(CatalogItem)
            .where(CatalogItem.tenant_id == tenant_id, CatalogItem.id == item_id)
            .options(selectinload(CatalogItem.unit))
        )
        return self.db.scalar(stmt)

    def get_item_by_sku(self, tenant_id: uuid.UUID, sku: str) -> CatalogItem | None:
        stmt = select(CatalogItem).where(
            CatalogItem.tenant_id == tenant_id,
            CatalogItem.sku == sku,
        )
        return self.db.scalar(stmt)

    def create_item(self, **kwargs) -> CatalogItem:
        item = CatalogItem(**kwargs)
        self.db.add(item)
        self.db.flush()
        return item

    def delete_item(self, item: CatalogItem) -> None:
        self.db.delete(item)

    def list_price_lists(self, tenant_id: uuid.UUID) -> list[PriceList]:
        stmt = (
            select(PriceList)
            .where(PriceList.tenant_id == tenant_id)
            .options(selectinload(PriceList.items).selectinload(PriceListItem.catalog_item))
            .order_by(PriceList.name)
        )
        return list(self.db.scalars(stmt).all())

    def get_price_list(self, tenant_id: uuid.UUID, price_list_id: uuid.UUID) -> PriceList | None:
        stmt = (
            select(PriceList)
            .where(PriceList.tenant_id == tenant_id, PriceList.id == price_list_id)
            .options(selectinload(PriceList.items).selectinload(PriceListItem.catalog_item))
        )
        return self.db.scalar(stmt)

    def get_price_list_by_code(self, tenant_id: uuid.UUID, code: str) -> PriceList | None:
        stmt = select(PriceList).where(
            PriceList.tenant_id == tenant_id,
            PriceList.code == code,
        )
        return self.db.scalar(stmt)

    def create_price_list(self, **kwargs) -> PriceList:
        row = PriceList(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row

    def get_price_list_item(
        self,
        price_list_id: uuid.UUID,
        catalog_item_id: uuid.UUID,
    ) -> PriceListItem | None:
        stmt = select(PriceListItem).where(
            PriceListItem.price_list_id == price_list_id,
            PriceListItem.catalog_item_id == catalog_item_id,
        )
        return self.db.scalar(stmt)

    def add_price_list_item(self, **kwargs) -> PriceListItem:
        row = PriceListItem(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row
