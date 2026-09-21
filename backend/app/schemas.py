"""Pydantic transport schemas shared by future FastAPI endpoints."""

from pydantic import BaseModel, Field


class OrderPayload(BaseModel):
    external_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    demand: float = Field(gt=0)
    priority: int
    status: str = "pending"


class VehiclePayload(BaseModel):
    external_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: float = Field(gt=0)
    status: str = "available"
