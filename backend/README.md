# FasalFlow Backend

Production-ready FastAPI backend for agricultural market-intelligence and decision-support.

---

## Architecture Overview

```
External / Mock Providers (MockMarketProvider, MockBuyerDemandProvider)
                          ↓
Normalizers & Validation (validate_and_normalize_market_record)
                          ↓
PostgreSQL / PostGIS Database (Normalized tables, constraints, indexes)
                          ↓
Domain Services (Auth, Farmer, Cold Store, Market)
                          ↓
Shared Intelligence Engine (Supply-Demand Gap Calculation)
             ┌────────────┴────────────┐
             ↓                         ↓
   Farmer Intelligence      Cold Store Intelligence
 (Surplus & Price Risk,    (Capacity & Release Risk,
  Pre-booking & Storage)    Staggered Dispatching)
```

---

## Key Design Principles

1. **Role-Authoritative Security**: The backend independently enforces `FARMER` and `COLD_STORE_OPERATOR` permissions via cryptographic JWT and dependency guards (`require_farmer`, `require_cold_store_operator`).
2. **Zero External Government API Dependency**: Pluggable provider architecture with built-in mock providers (`MockMarketProvider`, `MockBuyerDemandProvider`) ensuring local development runs seamlessly offline.
3. **Optimized Inventory Design**: Write operations to cold-store stock maintain an immutable audit history (`ColdStoreEvent`) while atomically updating a read-optimized current balance (`ColdStoreInventory`) with row-level locking (`with_for_update()`).
4. **Role-Specific Decision Support**: Identical underlying market metrics produce distinct, actionable recommendations for farmers versus cold-store operators.
5. **Deterministic Arithmetic**: No fake AI or LLM hallucinated calculations. Risk scores and supply gaps are calculated using explicit, transparent domain rules and statistical moving averages.

---

## Local Setup & Development

### 1. Prerequisites
- Python 3.12+
- `uv` (recommended) or standard `pip`
- Docker & Docker Compose (optional for local PostgreSQL)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Dependency Installation
Using `uv`:
```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r backend/requirements.txt pytest httpx
```

### 4. Database Migrations
Run Alembic migrations to set up the database schema:
```bash
cd backend
alembic upgrade head
```

### 5. Seed Synthetic Pilot Data
Seed realistic pilot data for the Purba Bardhaman (Potato) agricultural cluster:
```bash
cd backend
python -m app.db.seed
```

### 6. Start Development Server
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## Automated Test Suite

Run the full automated test suite covering all domains, authentication, health checks, cold storage operations, markets, and intelligence engines:
```bash
PYTHONPATH=backend pytest backend/tests/
```
