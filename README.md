# FasalFlow

FasalFlow is an agricultural market-intelligence and decision-support platform designed around two primary user roles: farmers and cold-storage operators.

## Current scope

The first release is a website frontend with role-based login and a modular backend. Development uses synthetic/test data so external government APIs are not required.

## Repository structure

- `frontend/` — web application, authentication flows, dashboards and shared UI
- `backend/` — FastAPI application, database models, services and APIs
- `data/` — synthetic development data and seed files
- `docs/` — architecture and API documentation
- `infra/` — local development and deployment configuration
- `tests/` — cross-component/integration test assets

## Primary roles

- Farmer
- Cold-storage operator

Buyer and market datasets can be used as supporting data sources without making them primary login roles in the MVP.

## Development principle

External data providers must remain replaceable. Synthetic datasets and provider interfaces will be used first; government/API integrations can be added later without changing the core intelligence layer.
