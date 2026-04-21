"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.warehouse.database import init_db
from app.routers import sync_router, analysis_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Zenoti Data Warehouse & Analysis",
    description="Connect to Zenoti API, sync data into a local warehouse, and run cost-savings analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sync_router)
app.include_router(analysis_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
