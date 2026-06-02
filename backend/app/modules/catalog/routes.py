import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.entitlements import require_feature
from app.core.enums import CatalogItemType
from app.core.modules import require_module
from app.core.tenancy import TenantContext
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
from app.modules.catalog.service import CatalogService

items_router = APIRouter(prefix="/catalog/items", tags=["catalog"])
price_lists_router = APIRouter(prefix="/catalog/price-lists", tags=["catalog"])
units_router = APIRouter(prefix="/catalog/units", tags=["catalog"])


def _service(ctx: TenantContext, db: Session) -> CatalogService:
    return CatalogService(db, ctx.tenant.id)


@units_router.get("", response_model=list[UnitOfMeasureResponse])
def list_units(
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> list[UnitOfMeasureResponse]:
    return _service(ctx, db).list_units()


@units_router.post("", response_model=UnitOfMeasureResponse, status_code=201)
def create_unit(
    payload: UnitOfMeasureCreate,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> UnitOfMeasureResponse:
    result = _service(ctx, db).create_unit(payload)
    db.commit()
    return result


@items_router.get("", response_model=list[CatalogItemResponse])
def list_catalog_items(
    item_type: CatalogItemType | None = None,
    is_active: bool | None = None,
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> list[CatalogItemResponse]:
    return _service(ctx, db).list_items(
        item_type=item_type,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )


@items_router.post("", response_model=CatalogItemResponse, status_code=201)
def create_catalog_item(
    payload: CatalogItemCreate,
    ctx: TenantContext = Depends(require_feature("catalog.items.create")),
    db: Session = Depends(get_db),
) -> CatalogItemResponse:
    result = _service(ctx, db).create_item(ctx.user, payload)
    db.commit()
    return result


@items_router.get("/{item_id}", response_model=CatalogItemResponse)
def get_catalog_item(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> CatalogItemResponse:
    return _service(ctx, db).get_item(item_id)


@items_router.patch("/{item_id}", response_model=CatalogItemResponse)
def update_catalog_item(
    item_id: uuid.UUID,
    payload: CatalogItemUpdate,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> CatalogItemResponse:
    result = _service(ctx, db).update_item(ctx.user, item_id, payload)
    db.commit()
    return result


@items_router.delete("/{item_id}", status_code=204)
def delete_catalog_item(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> None:
    _service(ctx, db).delete_item(item_id)
    db.commit()


@price_lists_router.get("", response_model=list[PriceListResponse])
def list_price_lists(
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> list[PriceListResponse]:
    return _service(ctx, db).list_price_lists()


@price_lists_router.post("", response_model=PriceListResponse, status_code=201)
def create_price_list(
    payload: PriceListCreate,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> PriceListResponse:
    result = _service(ctx, db).create_price_list(ctx.user, payload)
    db.commit()
    return result


@price_lists_router.get("/{price_list_id}", response_model=PriceListResponse)
def get_price_list(
    price_list_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> PriceListResponse:
    return _service(ctx, db).get_price_list(price_list_id)


@price_lists_router.patch("/{price_list_id}", response_model=PriceListResponse)
def update_price_list(
    price_list_id: uuid.UUID,
    payload: PriceListUpdate,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> PriceListResponse:
    result = _service(ctx, db).update_price_list(ctx.user, price_list_id, payload)
    db.commit()
    return result


@price_lists_router.post(
    "/{price_list_id}/items",
    response_model=PriceListItemResponse,
    status_code=201,
)
def add_price_list_item(
    price_list_id: uuid.UUID,
    payload: PriceListItemCreate,
    ctx: TenantContext = Depends(require_module("catalog")),
    db: Session = Depends(get_db),
) -> PriceListItemResponse:
    result = _service(ctx, db).add_price_list_item(price_list_id, payload)
    db.commit()
    return result
