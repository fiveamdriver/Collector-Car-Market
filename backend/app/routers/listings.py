from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.listing import ActiveListing, AuctionResult
from app.schemas.listing import ActiveListingRead, AuctionResultRead

router = APIRouter()


# --- Stats ---

class ModelLineStats(BaseModel):
    model_line: str
    count: int
    # Rows with a non-null sold_price — the denominator behind avg_sold_price.
    # Clients combining lines into a weighted average must weight by this,
    # not by count, or unsold lots skew the blend.
    priced_count: int
    avg_sold_price: Optional[int] = None


@router.get("/stats/model-lines", response_model=list[ModelLineStats])
async def get_model_line_stats(db: AsyncSession = Depends(get_db)) -> list[ModelLineStats]:
    """Return sold count and average price grouped by model line."""
    query = select(
        AuctionResult.model_line,
        func.count().label("count"),
        func.count(AuctionResult.sold_price).label("priced_count"),
        func.avg(AuctionResult.sold_price).label("avg_sold_price"),
    ).group_by(AuctionResult.model_line)

    rows = (await db.execute(query)).all()
    return [
        ModelLineStats(
            model_line=row.model_line,
            count=row.count,
            priced_count=row.priced_count,
            avg_sold_price=round(row.avg_sold_price) if row.avg_sold_price else None,
        )
        for row in rows
    ]


class MonthlyPoint(BaseModel):
    month: str  # "YYYY-MM"
    avg_price: int
    count: int
    # Exact total, so callers merging several series into one line can recover a
    # true weighted average instead of re-averaging rounded averages.
    sum_price: int


class GroupStats(BaseModel):
    key: str
    count: int
    # Rows with a non-null sold_price — the denominator behind the price fields.
    # `count` includes unsold lots, so the two are deliberately not the same.
    priced_count: int
    avg_sold_price: Optional[int] = None
    min_sold_price: Optional[int] = None
    max_sold_price: Optional[int] = None
    # Exact total, for callers that roll several groups into one card.
    sum_sold_price: int = 0
    monthly: list[MonthlyPoint] = []


# Whitelist of groupable columns. Restricting to this mapping (rather than
# getattr on user input) keeps the group-by column out of caller control.
_GROUPABLE = {
    "generation": AuctionResult.generation,
    "variant": AuctionResult.variant,
}


@router.get("/stats/aggregate", response_model=list[GroupStats])
async def get_aggregate_stats(
    group_by: Literal["generation", "variant"] = Query(
        ..., description="Column to group the aggregates by."
    ),
    make: Optional[str] = None,
    model_line: Optional[str] = None,
    generation: Optional[str] = None,
    variant: Optional[str] = None,
    transmission: Optional[str] = None,
    monthly: bool = Query(
        default=False,
        description="Include a per-group monthly average/count series (for sparklines).",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[GroupStats]:
    """Aggregate auction results in the database instead of shipping rows.

    The index pages only ever render counts, averages, and trend lines. Computing
    those here turns a multi-megabyte row dump into a payload of a few kilobytes.
    """
    group_col = _GROUPABLE[group_by]

    filters = []
    if make:
        filters.append(AuctionResult.make == make)
    if model_line:
        filters.append(AuctionResult.model_line == model_line)
    if generation:
        filters.append(AuctionResult.generation == generation)
    if variant:
        filters.append(AuctionResult.variant == variant)
    if transmission:
        filters.append(AuctionResult.transmission == transmission)

    query = (
        select(
            group_col.label("key"),
            func.count().label("count"),
            func.count(AuctionResult.sold_price).label("priced_count"),
            func.avg(AuctionResult.sold_price).label("avg_sold_price"),
            func.min(AuctionResult.sold_price).label("min_sold_price"),
            func.max(AuctionResult.sold_price).label("max_sold_price"),
            func.coalesce(func.sum(AuctionResult.sold_price), 0).label("sum_sold_price"),
        )
        .where(*filters)
        .group_by(group_col)
    )
    rows = (await db.execute(query)).all()

    series: dict[str, list[MonthlyPoint]] = {}
    if monthly:
        # Casting the date to text yields "YYYY-MM-DD" on both Postgres and
        # SQLite, so slicing the first 7 chars gives a portable month key
        # without reaching for a dialect-specific date function.
        month_col = func.substr(cast(AuctionResult.sold_date, String), 1, 7)
        monthly_query = (
            select(
                group_col.label("key"),
                month_col.label("month"),
                func.avg(AuctionResult.sold_price).label("avg_price"),
                func.count(AuctionResult.sold_price).label("count"),
                func.sum(AuctionResult.sold_price).label("sum_price"),
            )
            .where(
                *filters,
                AuctionResult.sold_date.is_not(None),
                AuctionResult.sold_price.is_not(None),
            )
            .group_by(group_col, month_col)
            .order_by(month_col)
        )
        for row in (await db.execute(monthly_query)).all():
            series.setdefault(row.key, []).append(
                MonthlyPoint(
                    month=row.month,
                    avg_price=round(row.avg_price),
                    count=row.count,
                    sum_price=row.sum_price,
                )
            )

    return [
        GroupStats(
            key=row.key,
            count=row.count,
            priced_count=row.priced_count,
            avg_sold_price=round(row.avg_sold_price) if row.avg_sold_price else None,
            min_sold_price=row.min_sold_price,
            max_sold_price=row.max_sold_price,
            sum_sold_price=row.sum_sold_price,
            monthly=series.get(row.key, []),
        )
        for row in rows
    ]


# --- Auction Results ---

@router.get("/auction-results", response_model=list[AuctionResultRead])
async def list_auction_results(
    make: Optional[str] = None,
    model_line: Optional[str] = None,
    generation: Optional[str] = None,
    variant: Optional[str] = None,
    transmission: Optional[str] = None,
    limit: int = Query(default=500, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
) -> list[AuctionResultRead]:
    """Return auction results filtered by the given fields, ordered newest first."""
    query = select(AuctionResult)
    if make:
        query = query.where(AuctionResult.make == make)
    if model_line:
        query = query.where(AuctionResult.model_line == model_line)
    if generation:
        query = query.where(AuctionResult.generation == generation)
    if variant:
        query = query.where(AuctionResult.variant == variant)
    if transmission:
        query = query.where(AuctionResult.transmission == transmission)
    query = query.order_by(AuctionResult.sold_date.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/auction-results/{record_id}", response_model=AuctionResultRead)
async def get_auction_result(
    record_id: int,
    db: AsyncSession = Depends(get_db),
) -> AuctionResultRead:
    row = await db.get(AuctionResult, record_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auction result {record_id} not found",
        )
    return row


# --- Active Listings ---

@router.get("/active-listings", response_model=list[ActiveListingRead])
async def list_active_listings(
    make: Optional[str] = None,
    model_line: Optional[str] = None,
    generation: Optional[str] = None,
    variant: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list[ActiveListingRead]:
    """Return active listings filtered by the given fields."""
    query = select(ActiveListing)
    if make:
        query = query.where(ActiveListing.make == make)
    if model_line:
        query = query.where(ActiveListing.model_line == model_line)
    if generation:
        query = query.where(ActiveListing.generation == generation)
    if variant:
        query = query.where(ActiveListing.variant == variant)
    result = await db.execute(query)
    return result.scalars().all()
