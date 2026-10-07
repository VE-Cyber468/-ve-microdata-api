# VE MicroData — GB Postcode Intelligence API
Vanguard Enterprises postcode lookup for England, Scotland and Wales.

## Endpoints
- GET /health — checks the postcode database
- GET /lookup?postcode=EN1%201AA — exact postcode lookup
- GET /postcode?postcode=EN1%201AA — equivalent lookup
- POST /postcode with JSON {"postcode":"EN1 1AA"} — retains the original endpoint
- GET /docs — interactive API documentation

## Data
The supplied OS Code-Point Open version 2026.3.0 ZIP is included at codepo_gb.zip. It contains 1,749,109 records. main.py builds an indexed SQLite database on first startup, streaming the source in small batches. The generated database is excluded from Git and can be rebuilt after deployment.

Incomplete postcodes return 422. Postcodes absent from this dataset return 404. Northern Ireland is not included. Coordinates are British National Grid eastings/northings, not latitude/longitude. Area names come from the supplied Codelist.xlsx; unavailable names return null while source codes remain available.

The data licence and copyright acknowledgements are preserved in LICENCE.txt and in lookup responses. This update does not add marketplace billing, customer authentication or metering.

## Run
pip install -r requirements.txt
python main.py
uvicorn main:app --host 0.0.0.0 --port 8000

## Render
The existing pip-install build and uvicorn main:app start commands work unchanged: the database builds before application startup completes. render.yaml also offers a build-time import. Keep one Uvicorn worker to avoid concurrent first-start builds. Render services configured directly do not automatically inherit changes to render.yaml.
