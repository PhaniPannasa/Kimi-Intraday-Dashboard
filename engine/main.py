import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.rest_routes import router as rest_router
from api.websocket_manager import router as ws_router
from core.scheduler.market_scheduler import scheduler
from core.pipeline import pipeline
from core.data.upstox_ws import upstox_ws
from db.timescale import db as timescale_db


async def _consume_ws():
    """Keep WebSocket listener running — on_tick dispatched via thread."""
    await upstox_ws.listen()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Engine starting...")

    # Wire Upstox WebSocket ticks into the pipeline TickBuffer
    upstox_ws.on_tick = pipeline.handle_upstox_tick

    # Connect and subscribe to all symbols in Full mode
    try:
        await upstox_ws.connect()
        all_keys = list(pipeline.symbol_map.values())
        await upstox_ws.subscribe(all_keys, mode="full")
        # Start consuming WS messages in background
        asyncio.create_task(_consume_ws())
        print(f"Upstox WS connected, subscribed to {len(all_keys)} symbols")
    except Exception as e:
        print(f"Upstox WS connection deferred: {e}")

    # Connect to TimescaleDB
    try:
        await timescale_db.connect()
        await timescale_db.run_migrations()
        print("TimescaleDB connected and migrated")
    except Exception as e:
        print(f"TimescaleDB connection deferred: {e}")

    scheduler.register_job(
        "pipeline_cycle",
        pipeline.run_cycle,
        trigger="interval",
        seconds=60,
        next_run_time=None,  # fire immediately on first run
    )
    scheduler.start()
    # Force immediate first cycle
    asyncio.create_task(pipeline.run_cycle())
    print(f"Scheduler started with {scheduler.get_job_count()} jobs, first cycle triggered")

    yield

    print("Engine shutting down...")
    await upstox_ws.close()
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
