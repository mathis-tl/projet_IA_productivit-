from fastapi import FastAPI
from app.core.database import engine, Base
from app.routers import health, auth, pages, blocks, tasks, links, ai_traces, ai_analyzes

# Init DB
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProductivityAI API",
    version="0.3.0"
)

# Routes
app.include_router(health.router, prefix="/health")
app.include_router(auth.router)
app.include_router(pages.router)
app.include_router(blocks.router)
app.include_router(tasks.router)
app.include_router(links.router)
app.include_router(ai_traces.router)
app.include_router(ai_analyzes.router)

