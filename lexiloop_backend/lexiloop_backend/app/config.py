"""
config.py — central place all secrets/settings are read from.
Nothing in this file is a real secret. Real values live in your local
.env file (never committed) and are loaded here via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- MongoDB ---
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "lexiloop")

    # --- Groq (LLaMA3 access for the LangChain agent) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-70b-8192")

    # --- JWT auth ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-.env")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # --- CNN model checkpoint ---
    CNN_MODEL_PATH: str = os.getenv(
        "CNN_MODEL_PATH", "app/ai/handwriting/checkpoints/model.pth"
    )


settings = Settings()
