# Data Strategy

The MVP does not depend on live government APIs.

## Development data

Use synthetic JSON/CSV data under `data/sample/` for:
- farmers
- farms
- commodities
- farmer supply
- buyers
- buyer demand
- cold stores
- cold-store events
- markets
- market prices
- market arrivals
- weather observations

All generated records should be clearly marked as test/synthetic data.

## Provider abstraction

External data should enter through ingestion/provider modules and be normalized into internal schemas. Domain services must never depend directly on a specific government's website or API.
