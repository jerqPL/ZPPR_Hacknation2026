# Zasiłkowy Przewodnik Przyszłego Rodzica (ZPPR)

Nowoczesna aplikacja webowa (RWD) wspierająca przyszłych rodziców i rodziców małych dzieci w ustalaniu uprawnień oraz wysokości świadczeń z ubezpieczenia chorobowego i macierzyńskiego ZUS (stan prawny 2026).

## Architektura i stos technologiczny

- **Frontend (`frontend/`)**: Next.js (App Router) + React + TypeScript + Tailwind CSS (Responsive Web Design, jasny i ciemny motyw).
- **Backend (`backend/`)**: Python 3.12 + FastAPI + Pydantic v2 + `pypdf` + `fpdf2` (z osadzoną czcionką Unicode `DejaVuSans`), integracja przez **REST API** (`/api/v1/...`, dokumentacja OpenAPI/Swagger pod `/docs`).
- **Uruchamianie**: Docker Compose ([docker-compose.yml](docker-compose.yml)) z trwałym wolumenem dla parametrów prawnych (`zppr_data`), healthcheckami i kontenerami bez uprawnień roota.
- **CI**: GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) uruchamiający testy `pytest`, kontrolę typów (`npm run lint`) oraz build produkcyjny Next.js.

## Główne funkcjonalności

| Obszar | Ścieżka UI | Endpoint REST API |
| --- | --- | --- |
| Świadczenia w czasie ciąży (chorobowy kod B, po ustaniu zatrudnienia art. 7/46, zwolnienia z wyczekiwania art. 4 ust. 3, rehabilitacyjne, art. 30 ust. 3 i ust. 1 pkt 2) | `/ciaza` | `POST /api/v1/calculator/pregnancy` |
| Zintegrowany kalkulator zasiłkowy (poród, podział opieki, rodzic samotny, łączenie z pracą obojga rodziców, adopcja, rodzina zastępcza, wcześniak, „Za życiem”, indywidualna podstawa z art. 36–49, wyrównanie do 100% z art. 31 ust. 4) | `/kalkulator` | `POST /api/v1/calculator/integrated`, `POST /api/v1/calculator/benefit-base` |
| Uniwersalny parser wniosków PDF (AcroForm, XFA XML, warstwa tekstowa — 24+ druków ZUS m.in. Z-3, Z-3a, ZAM, ZAS-53, ERU, e-ZLA) z ekranem weryfikacji pól oraz przykłady demonstracyjne | `/sprawy-pdf` | `GET /api/v1/documents/sample-cases`, `POST /api/v1/documents/analyze-pdf` |
| Dokumenty, terminy (dynamiczny kalkulator terminu z art. 30a), 10 formalnych wzorów wniosków zgodnych z Dz.U. 2025 poz. 322 i Dz.U. 2026 poz. 1316 (w tym odpis skrócony/zupełny USC) oraz eksport do pliku PDF (A4) | `/dokumenty` | `GET /api/v1/documents/guidance`, `POST /api/v1/documents/submit`, `POST /api/v1/documents/pdf` |
| Symulacje: mObywatel (trwała sesja), dane ZUS, zadłużenie składek, e-ZLA, PUE/eZUS | `/pue-zus` | `/api/v1/auth/*`, `/api/v1/zus/*` |
| Zagrożenia, ryzyka utraty zasiłku (art. 2a, art. 17, art. 40, art. 67) i szczególna ochrona trwałości stosunku pracy z Kodeksu pracy (art. 177 KP) | `/ryzyka` | `GET /api/v1/guidance/risks` |
| Wsparcie w szczególnych sytuacjach, katalog organizacji wyłącznie charytatywnych i oficjalne linki | `/wsparcie` | `GET /api/v1/guidance/support-organizations`, `GET /api/v1/guidance/official-links` |
| Panel administracyjny (pełna konfiguracja parametrów prawnych z autoryzacją `X-Admin-Key`) | `/admin` | `GET/PUT /api/v1/admin/parameters`, `POST /api/v1/admin/parameters/reset` |

## Uruchomienie (Docker)

Wymagany jest wyłącznie **Docker Desktop** (z Docker Compose).

```bash
docker compose up --build
```

Po uruchomieniu:
- **Aplikacja webowa**: `http://localhost:3000` (lub `http://127.0.0.1:3000`)
- **REST API (Swagger)**: `http://localhost:8000/docs`
- **Domyślny klucz administratora** (edytowalny przez `ZPPR_ADMIN_API_KEY`): `zppr-admin-2026`

### Zatrzymanie aplikacji

```bash
docker compose down
```

### Publiczny link przez Cloudflare Tunnel (darmowy, bez konfiguracji)

Frontend automatycznie przekazuje zapytania `/api/v1/*` do backendu, więc **jeden tunel** wystawia całą aplikację (frontend + API) bez problemów z CORS:

```bash
docker compose --profile tunnel up --build
```

Po uruchomieniu w logach usługi `cloudflared` pojawi się publiczny link `https://<losowa-nazwa>.trycloudflare.com` (można go też podejrzeć przez `docker compose logs cloudflared`).

> Jeśli masz własny stały tunel (Named Tunnel w Cloudflare Zero Trust z publiczną domeną skierowaną na `http://frontend:3000`):
> ```bash
> CLOUDFLARE_TUNNEL_TOKEN=<twój_token> docker compose --profile tunnel-named up --build -d
> ```
> Zatrzymanie z profilem tunelu: `docker compose --profile tunnel down`.

## Informacja o wykorzystaniu narzędzi AI (HackNation 2026)

Zgodnie z wymogami regulaminowymi zadania konkursowego ZUS (§ 4 oraz § 9) informujemy, że podczas projektowania, implementacji, audytu prawnego względem dokumentacji źródłowej z folderu `docs/` oraz tworzenia testów automatycznych wykorzystano narzędzia wspomagania programowania oparte na generatywnej sztucznej inteligencji (asystenci AI). Cała logika obliczeniowa, szablony dokumentów oraz parser PDF w działającej aplikacji działają w sposób w pełni deterministyczny (bez wywołań zewnętrznych modeli LLM w runtime) i są weryfikowane zestawem testów automatycznych `pytest`.