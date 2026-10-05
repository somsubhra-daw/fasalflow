# FasalFlow Architecture

## High-level flow

Website frontend
    |
    v
FastAPI API
    |
    +--> Authentication / authorization
    +--> Farmer domain
    +--> Cold-storage domain
    +--> Market / supporting data
    +--> Intelligence
    |
    v
PostgreSQL + PostGIS

The intelligence layer consumes supply, storage, demand, market and other validated data, then produces role-specific risk signals and recommendations.

## Role-specific intelligence

### Farmer

Inputs:
- expected harvest
- available produce
- market prices and arrivals
- visible buyer demand
- storage options
- logistics context

Outputs:
- surplus risk
- price pressure risk
- unsold-produce risk
- timing/storage/selling recommendations

### Cold-storage operator

Inputs:
- capacity
- current inventory
- loading events
- release events
- expected market demand
- market price/arrival trends

Outputs:
- capacity risk
- release pressure
- inventory/aging risk
- demand weakness
- release and market recommendations

## Data-provider strategy

Development starts with synthetic data. Provider interfaces should isolate external sources from domain logic so future government/private integrations can be added or replaced independently.
