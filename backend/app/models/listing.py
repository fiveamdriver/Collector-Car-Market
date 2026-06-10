from datetime import date, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuctionResult(Base):
    __tablename__ = "auction_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str]
    model_line: Mapped[str]
    generation: Mapped[str]
    variant: Mapped[str]
    year: Mapped[int]
    transmission: Mapped[str]
    is_widebody: Mapped[Optional[bool]]
    mileage: Mapped[Optional[int]]
    thumbnail_url: Mapped[Optional[str]]
    sold_price: Mapped[int]
    auction_source: Mapped[str]
    auction_url: Mapped[Optional[str]]
    sold_date: Mapped[date]
    lot_title: Mapped[Optional[str]]
    paint_to_sample: Mapped[Optional[bool]]
    production_number: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class ActiveListing(Base):
    __tablename__ = "active_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str]
    model_line: Mapped[str]
    generation: Mapped[Optional[str]]
    variant: Mapped[Optional[str]]
    year: Mapped[int]
    transmission: Mapped[Optional[str]]
    mileage: Mapped[Optional[int]]
    color: Mapped[Optional[str]]
    asking_price: Mapped[Optional[int]]
    listing_source: Mapped[str]
    listing_url: Mapped[str]
    listed_date: Mapped[Optional[date]]
    paint_to_sample: Mapped[Optional[bool]]
    production_number: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
