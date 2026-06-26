from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Valid transmission values stored in the database.
TransmissionType = Literal["PDK", "Manual", "Automatic"]


class AuctionResultCreate(BaseModel):
    make: str
    model_line: str
    generation: str
    variant: str
    year: int
    transmission: TransmissionType
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

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if not 1945 <= value <= 2030:
            raise ValueError(f"year {value} is outside the valid range 1945–2030")
        return value

    @field_validator("sold_price")
    @classmethod
    def validate_sold_price(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("sold_price must be a positive integer")
        return value

    @field_validator("mileage")
    @classmethod
    def validate_mileage(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("mileage cannot be negative")
        return value


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
    transmission: Optional[TransmissionType] = None
    mileage: Optional[int] = None
    color: Optional[str] = None
    asking_price: Optional[int] = None
    listing_source: str
    listing_url: str
    listed_date: Optional[date] = None
    paint_to_sample: Optional[bool] = None
    production_number: Optional[str] = None

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if not 1945 <= value <= 2030:
            raise ValueError(f"year {value} is outside the valid range 1945–2030")
        return value


class ActiveListingRead(ActiveListingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
