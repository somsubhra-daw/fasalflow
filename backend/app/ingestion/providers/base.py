from typing import Protocol, List, Dict, Any
from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class NormalizedMarketRecord(BaseModel):
    market_name: str
    district: str
    commodity_code: str
    record_date: date
    min_price_per_kg: Decimal
    modal_price_per_kg: Decimal
    max_price_per_kg: Decimal
    arrivals_kg: Decimal
    source: str = "synthetic"


class NormalizedDemandRecord(BaseModel):
    buyer_name: str
    buyer_type: str
    district: str
    commodity_code: str
    quantity_kg: Decimal
    required_from: date
    required_until: date
    max_price_per_kg: Decimal
    quality_grade: str = "A"
    source: str = "synthetic"


class NormalizedWeatherRecord(BaseModel):
    district: str
    forecast_date: date
    temp_celsius: Decimal
    rainfall_mm: Decimal
    humidity_percent: Decimal
    source: str = "synthetic"


class MarketDataProvider(Protocol):
    """Interface for pluggable market data sources."""
    def fetch_market_records(
        self, district: str, commodity_code: str, date_from: date, date_to: date
    ) -> List[NormalizedMarketRecord]:
        ...


class BuyerDemandProvider(Protocol):
    """Interface for pluggable buyer demand sources."""
    def fetch_demand_records(
        self, district: str, commodity_code: str
    ) -> List[NormalizedDemandRecord]:
        ...


class WeatherDataProvider(Protocol):
    """Interface for pluggable weather sources."""
    def fetch_weather_forecast(
        self, district: str, date_from: date, date_to: date
    ) -> List[NormalizedWeatherRecord]:
        ...
