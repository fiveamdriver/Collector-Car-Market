from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.listing import ActiveListing, AuctionResult
from app.schemas.listing import (
    ActiveListingCreate,
    ActiveListingRead,
    AuctionResultCreate,
    AuctionResultRead,
)

router = APIRouter()


# --- Auction Results ---

@router.get("/auction-results", response_model=list[AuctionResultRead])
async def list_auction_results(
    make: Optional[str] = None,
    model_line: Optional[str] = None,
    generation: Optional[str] = None,
    variant: Optional[str] = None,
    transmission: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(AuctionResult)
    if make:
        q = q.where(AuctionResult.make == make)
    if model_line:
        q = q.where(AuctionResult.model_line == model_line)
    if generation:
        q = q.where(AuctionResult.generation == generation)
    if variant:
        q = q.where(AuctionResult.variant == variant)
    if transmission:
        q = q.where(AuctionResult.transmission == transmission)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/auction-results/{id}", response_model=AuctionResultRead)
async def get_auction_result(id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(AuctionResult, id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Auction result not found")
    return row


@router.post("/auction-results", response_model=AuctionResultRead, status_code=status.HTTP_201_CREATED)
async def create_auction_result(payload: AuctionResultCreate, db: AsyncSession = Depends(get_db)):
    row = AuctionResult(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# --- Active Listings ---

@router.get("/active-listings", response_model=list[ActiveListingRead])
async def list_active_listings(
    make: Optional[str] = None,
    model_line: Optional[str] = None,
    generation: Optional[str] = None,
    variant: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ActiveListing)
    if make:
        q = q.where(ActiveListing.make == make)
    if model_line:
        q = q.where(ActiveListing.model_line == model_line)
    if generation:
        q = q.where(ActiveListing.generation == generation)
    if variant:
        q = q.where(ActiveListing.variant == variant)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/active-listings", response_model=ActiveListingRead, status_code=status.HTTP_201_CREATED)
async def create_active_listing(payload: ActiveListingCreate, db: AsyncSession = Depends(get_db)):
    row = ActiveListing(**payload.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
