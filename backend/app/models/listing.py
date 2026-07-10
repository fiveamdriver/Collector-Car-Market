from datetime import date, datetime
from typing import Optional

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuctionResult(Base):
    __tablename__ = "auction_results"
    __table_args__ = (
        # Matches the API's canonical query shape: filter on taxonomy columns,
        # then ORDER BY sold_date DESC LIMIT n.
        Index(
            "ix_auction_results_mlgv_sold_date",
            "model_line", "generation", "variant", "sold_date",
        ),
        # Dedup backstop: every ingest script dedupes on auction_url in
        # application memory; this makes the database enforce it. Postgres
        # treats NULLs as distinct, so URL-less rows are unaffected.
        Index("ux_auction_results_auction_url", "auction_url", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    make: Mapped[str]
    model_line: Mapped[str] = mapped_column(index=True)
    generation: Mapped[str] = mapped_column(index=True)
    variant: Mapped[str] = mapped_column(index=True)
    year: Mapped[int]
    transmission: Mapped[str]
    is_widebody: Mapped[Optional[bool]]
    mileage: Mapped[Optional[int]]
    thumbnail_url: Mapped[Optional[str]]
    sold_price: Mapped[Optional[int]]
    auction_source: Mapped[str]
    auction_url: Mapped[Optional[str]]
    sold_date: Mapped[Optional[date]] = mapped_column(index=True)
    lot_title: Mapped[Optional[str]]
    exterior_color: Mapped[Optional[str]]
    paint_to_sample: Mapped[Optional[bool]]
    production_number: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class ActiveListing(Base):
    __tablename__ = "active_listings"
    __table_args__ = (
        Index("ix_active_listings_mlgv", "model_line", "generation", "variant"),
    )

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
