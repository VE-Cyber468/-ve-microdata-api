from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="VE MicroData — UK Postcode Intelligence API",
    description="Vanguard Enterprises micro-data API for UK postcode intelligence.",
    version="1.0.0",
)


class PostcodeRequest(BaseModel):
    postcode: str


@app.get("/")
def root():
    return {
        "service": "VE MicroData — UK Postcode Intelligence API",
        "status": "online",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/postcode")
def postcode_lookup(request: PostcodeRequest):
    postcode = request.postcode.strip().upper()

    return {
        "postcode": postcode,
        "status": "received",
    }
