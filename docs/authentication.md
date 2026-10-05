# Authentication

## MVP roles

### Farmer
Uses the farmer website area to manage farm/supply information and consume farmer-specific market intelligence.

### Cold-storage operator
Uses the cold-storage area to manage facility capacity, inventory and release events and consume storage-specific intelligence.

## Boundary

The frontend controls navigation and presentation. The backend validates identity and authorization on every protected API operation.

Keep role names stable and centralized so both frontend and backend use the same canonical values:
- `FARMER`
- `COLD_STORE_OPERATOR`
