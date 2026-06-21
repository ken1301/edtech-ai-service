import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import uvicorn

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from adapters.inbound.rest.lesson2_router import router as lesson2_router
from adapters.inbound.rest.create_lesson_router import router as create_lesson_router

from infrastructure.container import Container
from infrastructure.observability.middleware import SocraticContextMiddleware
from infrastructure.monitoring.metrics_middleware import MetricsMiddleware
from infrastructure.logging import setup_logging
from infrastructure import logging

load_dotenv()
setup_logging()

container = Container()
container.wire(modules=["adapters.inbound.rest.lesson2_router"])
container.wire(modules=["adapters.inbound.rest.create_lesson_router"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        await container.cache_adapter().close()
    except Exception:
        pass
    try:
        container.profile_store().close()
    except Exception:
        pass
    try:
        container.session_store().close()
    except Exception:
        pass


app = FastAPI(title=" AI Service API", version="1.0.0", lifespan=lifespan)

# Add observability middleware
app.add_middleware(MetricsMiddleware)
app.add_middleware(SocraticContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[container.config().NESTJS_BACKEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["X-Correlation-ID", "Content-Type", "Authorization"],
    expose_headers=["X-Correlation-ID"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.container = container
app.include_router(lesson2_router, prefix="/lesson2", tags=["Lesson 2"])
app.include_router(create_lesson_router, prefix="/create-lesson", tags=["Create Lesson"])

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Socratic AI Chat API",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info(f"Starting Socratic AI Chat API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
