"""Run the JARVIS API as a restart-safe 24/7 service."""
from __future__ import annotations
import asyncio, os, uvicorn
from app.main import app
from app.service import Watchdog, install_signal_handlers

async def serve() -> None:
    config = uvicorn.Config(app, host=os.getenv("JARVIS_HOST", "0.0.0.0"), port=int(os.getenv("JARVIS_PORT", "8000")), log_level=os.getenv("JARVIS_LOG_LEVEL", "info"))
    await uvicorn.Server(config).serve()

async def main() -> None:
    watchdog = Watchdog(serve); install_signal_handlers(watchdog); await watchdog.run()

if __name__ == "__main__": asyncio.run(main())
