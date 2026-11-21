# Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR) — HackNation 2026

Szkielet aplikacji webowej (RWD) przygotowany zgodnie z wymaganiami wyzwania **ZUS — Zasiłkowy Przewodnik Przyszłego Rodzica** (HackNation 2026).

## Architektura i stos technologiczny

- **Frontend (`frontend/`)**: Next.js 15 (App Router) + React 19 + TypeScript + Tailwind CSS (Responsive Web Design).
- **Backend (`backend/`)**: Python 3.12 + FastAPI + Pydantic v2 + `pypdf`, komunikacja przez **REST API** (`/api/v1/...`, dokumentacja OpenAPI/Swagger pod `/docs`).
- **Konteneryzacja**: `docker-compose.yml` uruchamiający jednocześnie warstwę prezentacji i REST API.

## Pokrycie wymagań konkursowych

| Wymaganie z treści zadania | Moduł Frontend | Endpoint REST API |
| --- | --- | --- |
| a) Świadczenia w czasie ciąży (chorobowy kod B, rehabilitacyjne, zasiłek w wys. macierzyńskiego) | `/ciaza` | `POST /api/v1/calculator/pregnancy` |
| b–f, j) Zintegrowany kalkulator (poród, podział opieki, łączenie z pracą, adopcja/rodzina zastępcza, wcześniak, Za życiem, indywidualna podstawa) | `/kalkulator` | `POST /api/v1/calculator/integrated` |
| Upload i testowanie przykładowych wniosków PDF / spraw ZUS | `/sprawy-pdf` | `GET /api/v1/documents/sample-cases`, `POST /api/v1/documents/analyze-pdf` |
| g) Dokumenty, terminy, płatnik (>20) vs ZUS, symulacja wniosków (urlop, ZAM, akt urodzenia USC) | `/dokumenty` | `GET /api/v1/documents/guidance`, `POST /api/v1/documents/submit` |
| Symulacje: mObywatel, dane ZUS, zadłużenie składek, e-ZLA, PUE/eZUS | `/pue-zus` | `/api/v1/auth/*`, `/api/v1/zus/*` |
| h) Zagrożenia, ryzyka utraty/obniżenia zasiłku, ochrona z KP | `/ryzyka` | `GET /api/v1/guidance/risks` |
| i) Szczególne sytuacje, podmioty wyłącznie charytatywne, oficjalne linki (ZUS, MRPiPS, PIP, USC) | `/wsparcie` | `GET /api/v1/guidance/support-organizations`, `GET /api/v1/guidance/official-links` |
| Panel administracyjny (edycja parametrów prawnych przy zmianach legislacyjnych) | `/admin` | `GET/PUT /api/v1/admin/parameters`, `POST /api/v1/admin/parameters/reset` |

## Uruchomienie lokalne

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Testy jednostkowe / API:

```bash
cd backend
.venv/bin/pytest -v
```

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Aplikacja dostępna pod `http://localhost:3000`, dokumentacja REST API pod `http://localhost:8000/docs`.

### 3. Docker Compose

```bash
docker compose up --build
```

## Zakres wykorzystania AI

- Wyliczenia uprawnień i kwot zasiłków są realizowane **w pełni deterministycznie** przez silnik reguł w `backend/app/services/calculator_service.py` na podstawie konfigurowalnych parametrów z `backend/data/legal_parameters.json` (eliminacja ryzyka halucynacji prawnych).
- Architektura przewiduje opcjonalne podpięcie modułu AI/OCR w `backend/app/services/pdf_parser_service.py` dla skanowanych wniosków PDF bez warstwy tekstowej oraz konwersacyjnego asystenta wyjaśnień.