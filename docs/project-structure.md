# FasalFlow Project Structure

The repository is intentionally a monorepo because the current client is a single website and the backend is a single API.

## Frontend

React + TypeScript website organized by feature. The two primary authenticated areas are:

- `/farmer/*`
- `/cold-store/*`

Authentication is a cross-cutting feature. Role guards should control protected routes, but the backend remains authoritative for authorization.

## Backend

FastAPI is split into API, domain services, persistence and intelligence concerns.

`ingestion/` isolates test data and future external data providers.

`intelligence/` is role-aware:
- forecasting
- risk
- recommendations
- feature generation

## Data

Synthetic data is first-class during development. No feature should require a live government API to run locally.

## Future expansion

A mobile client, admin portal or additional roles can be added later without changing the core repository layout.
