from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
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
