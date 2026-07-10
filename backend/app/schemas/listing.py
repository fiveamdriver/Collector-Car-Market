from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

# The API is read-only: all writes happen through the ingest scripts in
# backend/data/, which write via the ORM. These schemas serialize DB rows
# outward and deliberately carry no validators — a single out-of-spec row
# must not turn into a 500 for the whole endpoint.


class AuctionResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    make: str
    model_line: str
    generation: str
    variant: str
    year: int
    transmission: str
    is_widebody: Optional[bool] = None
    mileage: Optional[int] = None
    thumbnail_url: Optional[str] = None
    sold_price: Optional[int] = None
    auction_source: str
    auction_url: Optional[str] = None
    sold_date: Optional[date] = None
    lot_title: Optional[str] = None
    exterior_color: Optional[str] = None
    paint_to_sample: Optional[bool] = None
    production_number: Optional[str] = None
    created_at: datetime


class ActiveListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
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
    created_at: datetime
