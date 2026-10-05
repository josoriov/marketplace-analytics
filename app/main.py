from fastapi import FastAPI

app = FastAPI(title="Marketplace Seller Analytics API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Application liveness; PostgreSQL is checked by the pipeline."""
    return {"status": "ok"}
