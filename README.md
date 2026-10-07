# VE MicroData — UK Postcode Intelligence API
Vanguard Enterprises micro-data API. Accepts a complete UK postcode and returns compact ONS-derived postcode intelligence.

## Endpoints
- `GET /health`
- `GET /lookup?postcode=N12%200BP`
- `/docs` interactive OpenAPI documentation

## Data
Production requires the August 2026 ONS postcode lookup ZIP at `data/NSPCL_AUG26_UK_LU.zip` or `POSTCODE_ZIP` pointing to it. The dataset is deliberately excluded from Git because of its size. No latitude/longitude is claimed; the source supplies British National Grid eastings/northings.

## Render
`render.yaml` contains the free Frankfurt web-service configuration. A production data-loading/storage step is still required before `/lookup` can serve postcode records on Render.
