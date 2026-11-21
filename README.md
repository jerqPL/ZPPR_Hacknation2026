# Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR)

Nowoczesna aplikacja webowa (RWD) wspierająca przyszłych rodziców i rodziców małych dzieci w ustalaniu uprawnień oraz wysokości świadczeń z ubezpieczenia chorobowego i macierzyńskiego ZUS (stan prawny 2026).

## Architektura i stos technologiczny

- **Frontend (`frontend/`)**: Next.js (App Router) + React + TypeScript + Tailwind CSS (Responsive Web Design, jasny i ciemny motyw).
- **Backend (`backend/`)**: Python 3.12 + FastAPI + Pydantic v2 + `pypdf`, integracja przez **REST API** (`/api/v1/...`, dokumentacja OpenAPI/Swagger pod `/docs`).
- **Uruchamianie**: Docker Compose ([docker-compose.yml](docker-compose.yml)) z trwałym wolumenem dla parametrów prawnych (`zppr_data`), healthcheckami i kontenerami bez uprawnień roota.
- **CI**: GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) uruchamiający testy `pytest` oraz build produkcyjny Next.js.

## Główne funkcjonalności

| Obszar | Ścieżka UI | Endpoint REST API |
| --- | --- | --- |
| Świadczenia w czasie ciąży (chorobowy kod B, po ustaniu zatrudnienia art. 7/46, rehabilitacyjne, zasiłek w wys. macierzyńskiego) | `/ciaza` | `POST /api/v1/calculator/pregnancy` |
| Zintegrowany kalkulator zasiłkowy (poród, podział opieki, rodzic samotny, łączenie z pracą obojga rodziców, adopcja, rodzina zastępcza, wcześniak, „Za życiem”, indywidualna podstawa z art. 36–48a, wyrównanie do 100% z art. 31 ust. 4) | `/kalkulator` | `POST /api/v1/calculator/integrated`, `POST /api/v1/calculator/benefit-base` |
| Analiza wniosków PDF (Z-3, Z-3a, ZAM, ZAS-53, poświadczenie ubezpieczenia) z ekranem weryfikacji pól oraz przykłady demonstracyjne | `/sprawy-pdf` | `GET /api/v1/documents/sample-cases`, `POST /api/v1/documents/analyze-pdf` |
| Dokumenty, terminy (w tym kalkulator terminu 21 dni), kreator i podgląd wniosków do druku/pobrania | `/dokumenty` | `GET /api/v1/documents/guidance`, `POST /api/v1/documents/submit` |
| Symulacje: mObywatel (trwała sesja), dane ZUS, zadłużenie składek, e-ZLA, PUE/eZUS | `/pue-zus` | `/api/v1/auth/*`, `/api/v1/zus/*` |
| Zagrożenia, ryzyka utraty zasiłku i szczególna ochrona z Kodeksu pracy | `/ryzyka` | `GET /api/v1/guidance/risks` |
| Wsparcie w szczególnych sytuacjach, katalog organizacji charytatywnych i oficjalne linki | `/wsparcie` | `GET /api/v1/guidance/support-organizations`, `GET /api/v1/guidance/official-links` |
| Panel administracyjny (pełna konfiguracja parametrów prawnych z autoryzacją `X-Admin-Key`) | `/admin` | `GET/PUT /api/v1/admin/parameters`, `POST /api/v1/admin/parameters/reset` |

## Uruchomienie (Docker)

Wymagany jest wyłącznie **Docker Desktop** (z Docker Compose).

```bash
docker compose up --build
```

Po uruchomieniu:
- **Aplikacja webowa**: `http://localhost:3000`
- **REST API (Swagger)**: `http://localhost:8000/docs`
- **Domyślny klucz administratora** (edytowalny przez `ZPPR_ADMIN_API_KEY`): `zppr-admin-2026`

### Zatrzymanie aplikacji

```bash
docker compose down
```