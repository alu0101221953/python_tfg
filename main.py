"""
Sistema tutor inteligente para Python básico.
TFG · Víctor Cánovas del Pino · Universidad de La Laguna · 2025-2026
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TFG", version="0.1.0")


@app.get("/")
def index():
    return JSONResponse(content={
        "mensaje": "TFG API funcionando",
        "version": "0.1.0",
    })