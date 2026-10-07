"""VE postcode lookup backed by the supplied OS Code-Point Open dataset."""
from contextlib import asynccontextmanager
import csv
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import zipfile

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
SOURCE = Path(os.getenv('POSTCODE_ZIP', str(ROOT / 'codepo_gb.zip')))
DATABASE = Path(os.getenv('POSTCODE_DB', str(ROOT / 'postcodes.sqlite'))).resolve()
ATTRIBUTION = (
    'Contains Ordnance Survey data © Crown copyright and database right 2026. '
    'Contains Royal Mail data © Royal Mail copyright and database right 2026. '
    'Contains National Statistics data © Crown copyright and database right 2026.'
)
FORMAT = re.compile(r'(?:GIR0AA|[A-Z]{1,2}[0-9][A-Z0-9]?[0-9][A-Z]{2})\Z')
COUNTRIES = {'E92000001': 'England', 'W92000004': 'Wales', 'S92000003': 'Scotland'}
NAMES = json.loads((ROOT / 'area_names.json').read_text())


def normalise(value: str) -> str:
    compact = re.sub(r'\s+', '', value).upper()
    if not FORMAT.fullmatch(compact):
        raise HTTPException(422, 'Enter a complete postcode, including the final three characters.')
    return compact[:-3] + ' ' + compact[-3:]


def build_database() -> int:
    """Stream the ZIP to SQLite; replace only after a complete build."""
    fingerprint = f'{SOURCE.stat().st_size}:{SOURCE.stat().st_mtime_ns}'
    if DATABASE.exists():
        with sqlite3.connect(DATABASE) as db:
            try:
                meta = dict(db.execute('SELECT key, value FROM metadata'))
                if meta.get('source') == fingerprint:
                    return int(meta['record_count'])
            except sqlite3.DatabaseError:
                pass
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATABASE.with_suffix('.building')
    temporary.unlink(missing_ok=True)
    try:
        with sqlite3.connect(temporary) as db, zipfile.ZipFile(SOURCE) as archive:
            db.execute('CREATE TABLE postcodes (postcode TEXT PRIMARY KEY, quality INTEGER, eastings INTEGER, northings INTEGER, country TEXT, nhs_region TEXT, nhs_area TEXT, county TEXT, district TEXT, ward TEXT) WITHOUT ROWID')
            db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
            count = 0
            for name in archive.namelist():
                if not name.startswith('Data/CSV/') or not name.endswith('.csv'):
                    continue
                with archive.open(name) as stream:
                    batch = []
                    for row in csv.reader(io.TextIOWrapper(stream, encoding='utf-8-sig')):
                        if len(row) != 10:
                            raise ValueError(f'Unexpected columns in {name}')
                        compact = re.sub(r'\s+', '', row[0]).upper()
                        row[0] = compact[:-3] + ' ' + compact[-3:]
                        batch.append(row)
                        count += 1
                        if len(batch) == 5000:
                            db.executemany('INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?)', batch)
                            batch.clear()
                    if batch:
                        db.executemany('INSERT INTO postcodes VALUES (?,?,?,?,?,?,?,?,?,?)', batch)
            if count == 0:
                raise ValueError('No postcode records found')
            db.executemany('INSERT INTO metadata VALUES (?,?)', [('source', fingerprint), ('record_count', str(count))])
            db.commit()
        temporary.replace(DATABASE)
        return count
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.record_count = build_database()
    yield


app = FastAPI(
    title='VE MicroData — GB Postcode Intelligence API',
    description='Exact postcode lookup for England, Scotland and Wales using OS Code-Point Open. Northern Ireland is not included.',
    version='1.1.0',
    lifespan=lifespan,
)


class PostcodeRequest(BaseModel):
    postcode: str


@app.get('/')
def root():
    return {'service': app.title, 'status': 'online', 'lookup': '/lookup?postcode=EN1%201AA', 'docs': '/docs', 'coverage': 'Great Britain'}


@app.get('/health')
def health():
    try:
        with sqlite3.connect(f'{DATABASE.as_uri()}?mode=ro', uri=True) as db:
            count = int(db.execute("SELECT value FROM metadata WHERE key='record_count'").fetchone()[0])
    except (sqlite3.Error, TypeError):
        raise HTTPException(503, 'Postcode database is unavailable')
    return {'status': 'healthy', 'data_ready': True, 'record_count': count, 'coverage': 'Great Britain'}


def lookup(value: str):
    postcode = normalise(value)
    try:
        with sqlite3.connect(f'{DATABASE.as_uri()}?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM postcodes WHERE postcode = ?', (postcode,)).fetchone()
    except sqlite3.Error:
        raise HTTPException(503, 'Postcode database is unavailable')
    if row is None:
        raise HTTPException(404, 'Postcode not found in this Great Britain dataset. Northern Ireland is not covered.')
    result = dict(row)
    country = result.pop('country')
    result['country_code'] = country
    result['country'] = COUNTRIES.get(country)
    for field in ['county', 'district', 'ward']:
        code = result.pop(field) or None
        result[f'{field}_code'] = code
        result[field] = NAMES.get(code)
    if result['quality'] == 90 or (result['eastings'] == 0 and result['northings'] == 0):
        result['eastings'] = result['northings'] = None
    result.update(status='found', coordinate_system='British National Grid (EPSG:27700)', source='OS Code-Point Open', dataset_version='2026.3.0', attribution=ATTRIBUTION)
    return result


@app.get('/lookup')
def get_lookup(postcode: str):
    return lookup(postcode)


@app.get('/postcode')
def get_postcode(postcode: str):
    return lookup(postcode)


@app.post('/postcode')
def post_postcode(request: PostcodeRequest):
    return lookup(request.postcode)


if __name__ == '__main__':
    print(f'Indexed {build_database():,} postcode records')
