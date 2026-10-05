# FasalFlow

Agricultural market-intelligence and decision-support platform for farmers and cold-storage operators.

## MVP scope

- Website frontend only
- Two primary login roles:
  - Farmer
  - Cold-storage operator
- FastAPI backend
- PostgreSQL + PostGIS
- Synthetic/test data for development
- Government/private data providers added later through isolated adapters

## Repository layout

```
fasalflow/
├── frontend/                  # React + TypeScript website
│   ├── public/
│   └── src/
│       ├── app/               # app-level configuration
│       ├── assets/
│       ├── components/        # shared components
│       │   └── ui/
│       ├── features/
│       │   ├── auth/          # login, session and role guards
│       │   ├── farmer/        # farmer dashboard and workflows
│       │   ├── cold-store/    # cold-store dashboard and workflows
│       │   ├── intelligence/  # charts/cards for backend intelligence
│       │   └── market/        # supporting market views
│       ├── layouts/
│       ├── lib/
│       │   ├── api/
│       │   └── auth/
│       ├── routes/
│       ├── types/
│       └── utils/
│
├── backend/                   # FastAPI API
│   ├── app/
│   │   ├── api/v1/endpoints/  # HTTP API endpoints
│   │   ├── auth/              # authentication and authorization
│   │   ├── core/              # settings and application config
│   │   ├── db/                # database/session setup
│   │   ├── ingestion/         # synthetic + future external providers
│   │   │   ├── providers/
│   │   │   └── normalizers/
│   │   ├── intelligence/
│   │   │   ├── features/
│   │   │   ├── forecasting/
│   │   │   ├── risk/
│   │   │   └── recommendations/
│   │   ├── models/            # SQLAlchemy models
│   │   ├── repositories/      # data-access layer
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # domain/application services
│   │   └── utils/
│   ├── alembic/               # database migrations
│   └── tests/
│
├── data/
│   ├── raw/                   # raw imported data
│   ├── processed/             # normalized datasets
│   └── sample/                # synthetic development data
├── docs/                      # architecture and implementation docs
├── infra/                     # infrastructure/deployment config
├── scripts/                   # developer utilities
├── tests/                     # cross-component tests
├── docker-compose.yml
└── .env.example
```

## Design principle

The intelligence engine is role-aware:

- **Farmer intelligence:** selling/storage timing, surplus, price-pressure and unsold-produce risks.
- **Cold-store intelligence:** capacity, inventory, release-pressure, aging and demand risks.

Both consume the same normalized market state but produce different recommendations.

External data sources are never hard-wired into business logic. Synthetic providers are used first so development and demos do not depend on the availability of government APIs.
