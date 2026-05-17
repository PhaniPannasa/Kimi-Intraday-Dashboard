from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.rest_routes import router as rest_router
from api.websocket_manager import router as ws_router
from core.scheduler.market_scheduler import scheduler
from core.pipeline import pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Engine starting...")

    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        trigger="interval",
        seconds=60,
    )
    scheduler.start()
    print(f"Scheduler started with {scheduler.get_job_count()} jobs")

    yield

    print("Engine shutting down...")
    scheduler.shutdown()


app = FastAPI(title="Intraday Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
