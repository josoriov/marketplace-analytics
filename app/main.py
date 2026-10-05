from fastapi import FastAPI


app = FastAPI(title="Marketplace Seller Analytics API")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    """Return a minimal liveness response for the API.

    Returns:
        dict[str, str]: A static payload indicating that the FastAPI service is
            running.

    Notes:
        This endpoint only reports application liveness. It does not verify
        downstream dependencies such as PostgreSQL.
    """
    return {"status": "ok"}
