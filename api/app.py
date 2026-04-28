import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import CountryAgent

logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — compiling agent graph...")
    app.state.agent = CountryAgent()
    logger.info("Agent ready.")
    yield
    logger.info("Shutting down.")

app = FastAPI(
    title="Country Information Agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    country: str | None = None
    fields: list[str] | None = None
    error: str | None = None

@app.get("/", include_in_schema=False)
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    result = app.state.agent.run(body.query)

    intent = result.get("intent")
    return AskResponse(
        answer=result.get("answer") or "No answer generated.",
        country=intent.country if intent else None,
        fields=intent.fields if intent else None,
        error=result.get("error"),
    )