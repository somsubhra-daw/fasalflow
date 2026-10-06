from decimal import Decimal
from typing import Optional
from app.ingestion.providers.base import NormalizedMarketRecord, NormalizedDemandRecord


class DataQualityValidationError(ValueError):
    pass


def validate_and_normalize_market_record(record: NormalizedMarketRecord) -> NormalizedMarketRecord:
    """Validate price logic (min <= modal <= max), non-negativity, and arrivals."""
    if record.min_price_per_kg < 0 or record.modal_price_per_kg < 0 or record.max_price_per_kg < 0:
        raise DataQualityValidationError(f"Negative prices not allowed in market record: {record}")

    if not (record.min_price_per_kg <= record.modal_price_per_kg <= record.max_price_per_kg):
        raise DataQualityValidationError(
            f"Invalid price order: min={record.min_price_per_kg}, modal={record.modal_price_per_kg}, max={record.max_price_per_kg}"
        )

    if record.arrivals_kg < 0:
        raise DataQualityValidationError(f"Negative arrivals not allowed: {record.arrivals_kg}")

    return record


def validate_and_normalize_demand_record(record: NormalizedDemandRecord) -> NormalizedDemandRecord:
    """Validate demand quantity, dates, and non-negative maximum price."""
    if record.quantity_kg <= 0:
        raise DataQualityValidationError(f"Demand quantity must be > 0: {record.quantity_kg}")

    if record.max_price_per_kg < 0:
        raise DataQualityValidationError(f"Max price cannot be negative: {record.max_price_per_kg}")

    if record.required_until < record.required_from:
        raise DataQualityValidationError(
            f"Invalid demand date window: from {record.required_from} to {record.required_until}"
        )

    return record
