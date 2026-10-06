from datetime import date, timedelta
from decimal import Decimal
from typing import List

from app.ingestion.providers.base import (
    MarketDataProvider,
    BuyerDemandProvider,
    WeatherDataProvider,
    NormalizedMarketRecord,
    NormalizedDemandRecord,
    NormalizedWeatherRecord,
)


class MockMarketProvider:
    """Mock/Synthetic market data provider for Purba Bardhaman region."""

    def fetch_market_records(
        self, district: str, commodity_code: str, date_from: date, date_to: date
    ) -> List[NormalizedMarketRecord]:
        records: List[NormalizedMarketRecord] = []
        markets = ["Memari Regulated Market", "Burdwan Sadar Market", "Kalna Krishi Mandi"]

        curr = date_from
        base_price = Decimal("20.00")
        day_offset = 0

        while curr <= date_to:
            for m_name in markets:
                # Deterministic synthetic wave based on day offset
                price_fluctuation = Decimal(day_offset % 5) * Decimal("0.50")
                modal_price = base_price + price_fluctuation
                min_price = modal_price - Decimal("2.00")
                max_price = modal_price + Decimal("2.50")
                arrivals = Decimal("40000.00") + Decimal((day_offset * 1500) % 30000)

                records.append(
                    NormalizedMarketRecord(
                        market_name=m_name,
                        district=district,
                        commodity_code=commodity_code,
                        record_date=curr,
                        min_price_per_kg=min_price,
                        modal_price_per_kg=modal_price,
                        max_price_per_kg=max_price,
                        arrivals_kg=arrivals,
                        source="synthetic",
                    )
                )
            curr += timedelta(days=1)
            day_offset += 1

        return records


class MockBuyerDemandProvider:
    """Mock/Synthetic buyer demand provider."""

    def fetch_demand_records(
        self, district: str, commodity_code: str
    ) -> List[NormalizedDemandRecord]:
        today = date.today()
        return [
            NormalizedDemandRecord(
                buyer_name="Bengal Agro Processing Unit",
                buyer_type="PROCESSOR",
                district=district,
                commodity_code=commodity_code,
                quantity_kg=Decimal("120000.00"),
                required_from=today,
                required_until=today + timedelta(days=14),
                max_price_per_kg=Decimal("23.00"),
                quality_grade="A",
                source="synthetic",
            ),
            NormalizedDemandRecord(
                buyer_name="Damodar Wholesale Trading Co",
                buyer_type="WHOLESALER",
                district=district,
                commodity_code=commodity_code,
                quantity_kg=Decimal("80000.00"),
                required_from=today + timedelta(days=2),
                required_until=today + timedelta(days=10),
                max_price_per_kg=Decimal("21.50"),
                quality_grade="B",
                source="synthetic",
            ),
            NormalizedDemandRecord(
                buyer_name="Kolkata Fresh Retail Chain",
                buyer_type="RETAILER",
                district=district,
                commodity_code=commodity_code,
                quantity_kg=Decimal("45000.00"),
                required_from=today + timedelta(days=1),
                required_until=today + timedelta(days=7),
                max_price_per_kg=Decimal("24.00"),
                quality_grade="A",
                source="synthetic",
            ),
        ]


class MockWeatherProvider:
    """Mock weather forecast provider."""

    def fetch_weather_forecast(
        self, district: str, date_from: date, date_to: date
    ) -> List[NormalizedWeatherRecord]:
        records: List[NormalizedWeatherRecord] = []
        curr = date_from
        while curr <= date_to:
            records.append(
                NormalizedWeatherRecord(
                    district=district,
                    forecast_date=curr,
                    temp_celsius=Decimal("28.5"),
                    rainfall_mm=Decimal("0.0"),
                    humidity_percent=Decimal("65.0"),
                    source="synthetic",
                )
            )
            curr += timedelta(days=1)
        return records
