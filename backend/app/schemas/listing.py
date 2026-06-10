from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuctionResultCreate(BaseModel):
    make: str
    model_line: str
    generation: str
    variant: str
    year: int
    transmission: str
    mileage: Optional[int] = None
    thumbnail_url: Optional[str] = None
    sold_price: int
    auction_source: str
    auction_url: Optional[str] = None
    sold_date: date
    lot_title: Optional[str] = None
    paint_to_sample: Optional[bool] = None
    production_number: Optional[str] = None


class AuctionResultRead(AuctionResultCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ActiveListingCreate(BaseModel):
    make: str
    model_line: str
    generation: Optional[str] = None
    variant: Optional[str] = None
    year: int
    transmission: Optional[str] = None
    mileage: Optional[int] = None
    color: Optional[str] = None
    asking_price: Optional[int] = None
    listing_source: str
    listing_url: str
    listed_date: Optional[date] = None
    paint_to_sample: Optional[bool] = None
    production_number: Optional[str] = None


class ActiveListingRead(ActiveListingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
