from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth_router, profiles, detect, simplify, chat, exercises
from app.ai import simplify_engine

app = FastAPI(title="LexiLoop API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    simplify_engine.load_model()


@app.get("/")
async def root():
    return {"status": "ok", "service": "LexiLoop API"}


app.include_router(auth_router.router)
app.include_router(profiles.router)
app.include_router(detect.router)
app.include_router(simplify.router)
app.include_router(chat.router)
app.include_router(exercises.router)
