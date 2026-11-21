from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import admin, auth_zus, calculator, documents, guidance

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API dla aplikacji Zasiłkowy Przewodnik Przyszłego Rodzica (HackNation 2026 — wyzwanie ZUS). "
        "Udostępnia zintegrowany kalkulator zasiłkowy, symulacje mObywatel/ZUS/PUE/e-ZLA, analizę wniosków PDF "
        "oraz panel administracyjny parametrów prawnych."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_zus.router, prefix=settings.api_prefix)
app.include_router(calculator.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(guidance.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/health", tags=["System"])
def healthcheck():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}
