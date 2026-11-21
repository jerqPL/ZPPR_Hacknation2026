from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import io
import os
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from pypdf import PdfReader
from pypdf.generic import ArrayObject, StreamObject
from app.models.guidance import (
    CaseDocumentsAnalysisResult,
    DocumentConflict,
    DocumentDomain,
    ExtractedPdfFields,
    PdfAnalysisResult,
    RecommendedCalculator,
    SampleCase,
    SicknessInsuranceStatus,
)
from app.services.parameter_store import parameter_store

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", *SUPPORTED_IMAGE_EXTENSIONS}

# Przykłady demonstracyjne (weryfikowane testami automatycznymi z silnikiem wyliczeń)
SAMPLE_CASES: list[SampleCase] = [
    SampleCase(
        case_id="case_01_uop_full",
        title="Przykład demonstracyjny #1 (UoP + Z-3): Pracownica (>20 ubezp.), podstawa z nagrodą roczną",
        description=(
            "Zatrudnienie na umowę o pracę od 24 miesięcy: wynagrodzenie zasadnicze 7 500 zł brutto + nagroda roczna "
            "6 000 zł brutto (1/12 = 500 zł/mies.). Łączna średnia: 8 000 zł brutto."
        ),
        scenario="birth",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — indywidualna podstawa wymiaru 6 903,20 zł (z 8 000 zł brutto po -13,71%), stawka 81,5% wypłacana przez pracodawcę.",
        expected_eligible=True,
        expected_base_parent1=6903.20,
        gross_monthly_salary=7500.0,
        custom_benefit_base=6903.20,
        benefit_base_details="Art. 36 i art. 42 ust. 3 ustawy zasiłkowej: (7 500 zł + 1/12 × 6 000 zł) × (1 - 13,71%) = 6 903,20 zł",
        second_parent_gross_salary=8200.0,
        second_parent_custom_base=7075.78,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=120,
        mother_maternity_weeks=20,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=True,
        notes="Przykład demonstracyjny weryfikujący wyliczenie podstawy wymiaru z premią roczną (1/12).",
    ),
    SampleCase(
        case_id="case_02_jdg_twins",
        title="Przykład demonstracyjny #2 (JDG, bliźniaki): Działalność gospodarcza, 2 dzieci, 100%/70%",
        description="Dobrowolne ubezpieczenie chorobowe opłacane terminowo > 12 miesięcy od podstawy 6 000 zł, urodzenie bliźniąt.",
        scenario="birth",
        insurance_title="jdg",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — zasiłek wypłacany przez ZUS: 31 tyg. macierzyńskiego (100%) + 43 tyg. rodzicielskiego (70%), podstawa 5 177,40 zł.",
        expected_eligible=True,
        expected_base_parent1=5177.40,
        gross_monthly_salary=6000.0,
        custom_benefit_base=5177.40,
        benefit_base_details="Art. 48 ust. 1 ustawy zasiłkowej: 6 000,00 zł × (1 - 13,71%) = 5 177,40 zł",
        children_count=2,
        payment_variant="100_70",
        has_za_zyciem=False,
        employer_insured_count=1,
        mother_maternity_weeks=31,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Zasiłek wypłaca ZUS na podstawie wniosku ZAM.",
    ),
    SampleCase(
        case_id="case_03_zlecenie_no_insurance",
        title="Przykład demonstracyjny #3 (Zlecenie — odmowa): Brak dobrowolnego ubezpieczenia chorobowego",
        description="Zleceniobiorca zgłoszony wyłącznie do ubezpieczeń emerytalnego, rentowego i zdrowotnego (brak chorobowego w dniu porodu).",
        scenario="birth",
        insurance_title="zlecenie",
        insured_on_event_date=False,
        expected_decision="ODMOWA — brak podlegania dobrowolnemu ubezpieczeniu chorobowemu w dniu porodu.",
        expected_eligible=False,
        expected_base_parent1=0.0,
        gross_monthly_salary=5400.0,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=12,
        notes="Przykład demonstracyjny dla najczęstszej przyczyny odmowy przy umowie zleceniu.",
    ),
    SampleCase(
        case_id="case_04_za_zyciem",
        title="Przykład demonstracyjny #4 (Art. 43 + Za życiem): Mała firma (≤20 os.), zachowana podstawa",
        description="Umowa o pracę w firmie 10-osobowej (płatnik ZUS), przejście z chorobowego na macierzyński (zachowana podstawa 5 608,85 zł), zaświadczenie 'Za życiem'.",
        scenario="birth",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — wydłużony urlop rodzicielski 65 tyg., podstawa z art. 43: 5 608,85 zł, wypłaca ZUS.",
        expected_eligible=True,
        expected_base_parent1=5608.85,
        gross_monthly_salary=6200.0,
        custom_benefit_base=5608.85,
        benefit_base_details="Art. 43 ustawy zasiłkowej: zachowana podstawa z zasiłku chorobowego = 5 608,85 zł",
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=True,
        employer_insured_count=10,
        mother_maternity_weeks=20,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Wymaga dołączenia zaświadczenia lekarskiego 'Za życiem'.",
    ),
    SampleCase(
        case_id="case_05_adoption_both_parents",
        title="Przykład demonstracyjny #5 (Adopcja): Przysposobienie dziecka (5 lat), podział między rodziców",
        description="Przyjęcie na wychowanie dziecka w wieku 5 lat i wniosek o przysposobienie. Podstawa Rodzica 1: 7 248,36 zł, Rodzica 2: 6 385,46 zł.",
        scenario="adoption",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — 20 tyg. na warunkach macierzyńskiego (14 + 6) + 41 tyg. rodzicielskiego (32 + 9) + 2 tyg. ojcowskiego.",
        expected_eligible=True,
        expected_base_parent1=7248.36,
        gross_monthly_salary=8000.0,
        custom_benefit_base=7248.36,
        benefit_base_details="Art. 36 i art. 42 ust. 2: średnia 12 mies. + 1/12 premii kwartalnych po -13,71% = 7 248,36 zł",
        second_parent_gross_salary=7400.0,
        second_parent_custom_base=6385.46,
        children_count=1,
        child_age_years=5.0,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=45,
        mother_maternity_weeks=14,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=True,
        notes="Przykład demonstracyjny dla rodziców adopcyjnych (limit wieku dziecka do 14 lat).",
    ),
    SampleCase(
        case_id="case_06_foster_non_prof_9_weeks",
        title="Przykład demonstracyjny #6 (Rodzina zastępcza niezawodowa): Dziecko 6,9 r.ż. (reguła min. 9 tyg.)",
        description="Przyjęcie dziecka w wieku 6 lat i 11 miesięcy do rodziny zastępczej niezawodowej — gwarancja 9 tyg. na warunkach macierzyńskiego + 38 tyg. rodzicielskiego.",
        scenario="foster",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — 9 tyg. na warunkach macierzyńskiego + 38 tyg. rodzicielskiego (art. 183 § 3 i § 4 pkt 3 KP), podstawa 5 867,72 zł.",
        expected_eligible=True,
        expected_base_parent1=5867.72,
        gross_monthly_salary=6800.0,
        custom_benefit_base=5867.72,
        benefit_base_details="Art. 36: 6 800,00 zł × (1 - 13,71%) = 5 867,72 zł",
        children_count=1,
        child_age_years=6.9,
        foster_family_type="non_professional",
        foster_deferred_school=False,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=15,
        mother_maternity_weeks=9,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Przykład demonstracyjny weryfikujący minimalny 9-tygodniowy wymiar urlopu dla rodziny zastępczej niezawodowej.",
    ),
    SampleCase(
        case_id="case_07_jdg_art48a_individual_base",
        title="Przykład demonstracyjny #7 (JDG Art. 48a): Krótki okres wysokiej składki na JDG (3 miesiące)",
        description="Ubezpieczona na JDG opłacała dobrowolne chorobowe przez 3 pełne miesiące od maksymalnej podstawy 23 550 zł brutto.",
        scenario="birth",
        insurance_title="jdg",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — indywidualna podstawa wg art. 48a ust. 1: 8 738,16 zł.",
        expected_eligible=True,
        expected_base_parent1=8738.16,
        gross_monthly_salary=23550.0,
        custom_benefit_base=8738.16,
        benefit_base_details="Art. 48a ust. 1: najniższa podstawa 4 877,11 zł + 3/12 nadwyżki = 8 738,16 zł",
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=1,
        mother_maternity_weeks=20,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Przykład demonstracyjny dla proporcjonalnego wyliczenia podstawy na JDG (art. 48a).",
    ),
]


def list_sample_cases() -> list[SampleCase]:
    return SAMPLE_CASES


# Pełny katalog oficjalnych formularzy ZUS (zasiłki, rodzicielstwo, zgłoszenia, zaświadczenia, decyzje)
ZUS_FORM_CATALOG: list[tuple[str, re.Pattern[str], str]] = [
    ("Z-3A", re.compile(r"\bZ[-.\s]?3A\b", re.IGNORECASE), "Zaświadczenie płatnika składek (dla zleceniobiorcy)"),
    ("Z-3B", re.compile(r"\bZ[-.\s]?3B\b", re.IGNORECASE), "Zaświadczenie płatnika składek (archiwalny dla JDG — zlikwidowany 24.10.2026)"),
    ("Z-3", re.compile(r"\bZ[-.]?3\b(?!\s*[AB]\b)", re.IGNORECASE), "Zaświadczenie płatnika składek (dla pracownika)"),
    (
        "ZAM",
        re.compile(r"\bZUS\s+ZAM\b|\bZAS-54\b|\b(?:FORMULARZ|WNIOSEK|DRUK)\s+ZAM\b|(?<!ADRES\s)(?<!MIEJSCE\s)(?<!UL\.\s)\bZAM\b(?!\.)"),
        "Wniosek o zasiłek macierzyński (od 24.10.2026 obejmuje też ZUR i ZAO)",
    ),
    ("ZUR", re.compile(r"\b(?:ZUS\s+)?ZUR\b"), "Wniosek o zasiłek macierzyński za okres urlopu rodzicielskiego (połączony z ZAM)"),
    ("ZAO", re.compile(r"\b(?:ZUS\s+)?ZAO\b|\bZAS-34\b"), "Wniosek o zasiłek macierzyński za okres urlopu ojcowskiego (połączony z ZAM)"),
    ("ZAS-53", re.compile(r"\bZAS-?53\b", re.IGNORECASE), "Wniosek o zasiłek chorobowy"),
    ("ZAS-12", re.compile(r"\bZAS-?12\b", re.IGNORECASE), "Zaświadczenie płatnika składek (dalszy okres zasiłku)"),
    ("ZAS-36", re.compile(r"\bZAS-?36\b", re.IGNORECASE), "Wniosek o zasiłek opiekuńczy z powodu sprawowania opieki nad dzieckiem"),
    ("ZAS-38", re.compile(r"\bZAS-?38\b", re.IGNORECASE), "Wniosek o zasiłek opiekuńczy (inny członek rodziny)"),
    ("Z-15A", re.compile(r"\bZ-?15A\b", re.IGNORECASE), "Wniosek o zasiłek opiekuńczy nad dzieckiem"),
    ("Z-15B", re.compile(r"\bZ-?15B\b", re.IGNORECASE), "Wniosek o zasiłek opiekuńczy nad innym członkiem rodziny"),
    ("Z-10", re.compile(r"\bZ-?10\b", re.IGNORECASE), "Oświadczenie po ustaniu tytułu ubezpieczenia chorobowego"),
    ("Z-12", re.compile(r"\bZ-?12\b|\bZPL\b", re.IGNORECASE), "Wniosek o zasiłek pogrzebowy"),
    ("ZNP-7", re.compile(r"\bZNP-?7\b", re.IGNORECASE), "Wniosek o świadczenie rehabilitacyjne"),
    ("E-ZLA", re.compile(r"\bE-?ZLA\b|\bZUS\s+ZLA\b|ZAŚWIADCZENIE\s+LEKARSKIE\s+O\s+CZASOWEJ\s+NIEZDOLNOŚCI", re.IGNORECASE), "Elektroniczne zaświadczenie lekarskie o niezdolności do pracy"),
    ("POG", re.compile(r"\bZUS\s+POG\b|PISMO\s+OGÓLNE\s+DO\s+ZAKŁADU\s+UBEZPIECZEŃ", re.IGNORECASE), "Pismo ogólne do ZUS (POG)"),
    ("ERU", re.compile(r"\bERU\b"), "Oświadczenie o sytuacji osobistej, rodzinnej, majątkowej i materialnej (rodzicielskie świadczenie uzupełniające Mama 4+)"),
    ("ERSU", re.compile(r"\bERSU\b"), "Wniosek o rodzicielskie świadczenie uzupełniające (Mama 4+)"),
    ("ZUS ZUA", re.compile(r"\bZUS\s+ZUA\b|\bZUA\b"), "Zgłoszenie do ubezpieczeń społecznych i zdrowotnego"),
    ("ZUS ZZA", re.compile(r"\bZUS\s+ZZA\b"), "Zgłoszenie wyłącznie do ubezpieczenia zdrowotnego"),
    ("ZUS ZWUA", re.compile(r"\bZUS\s+ZWUA\b|\bZWUA\b"), "Wyrejestrowanie z ubezpieczeń"),
    ("POŚWIADCZENIE UBEZPIECZENIA", re.compile(r"POŚWIADCZENI[EU]\s+UBEZPIECZENI", re.IGNORECASE), "Poświadczenie ubezpieczenia chorobowego ZUS"),
    ("DECYZJA ZUS", re.compile(r"\bDECYZJA\b.*(?:POSTANAWIA|ODMÓWIĆ\s+PRAWA|PRZYZNAĆ\s+PRAWO)", re.IGNORECASE | re.DOTALL), "Decyzja Zakładu Ubezpieczeń Społecznych"),
    ("US-7", re.compile(r"\bUS-?7\b", re.IGNORECASE), "Wniosek o wydanie zaświadczenia o przebiegu ubezpieczeń"),
    ("RD-3", re.compile(r"\bRD-?3\b", re.IGNORECASE), "Wniosek o zaświadczenie o niezaleganiu w opłacaniu składek"),
    ("WNIOSEK URLOPOWY KP", re.compile(r"WNIOSEK\s+O\s+UDZIELENIE\s+(?:CZĘŚCI\s+)?(?:UZUPEŁNIAJĄCEGO\s+)?URLOPU|WNIOSEK\s+O\s+ŁĄCZENIE\s+URLOPU", re.IGNORECASE), "Wniosek pracowniczy o urlop związany z rodzicielstwem (KP)"),
    ("AKT URODZENIA USC", re.compile(r"ODPIS\s+(?:SKRÓCONY|ZUPEŁNY)\s+AKTU\s+URODZENIA", re.IGNORECASE), "Odpis aktu urodzenia (Urząd Stanu Cywilnego)"),
]

_FORM_PATTERNS = [(code, pat) for code, pat, _ in ZUS_FORM_CATALOG]
_FORM_DESCRIPTIONS = {code: desc for code, _, desc in ZUS_FORM_CATALOG}

_TITLE_HINTS: list[tuple[str, re.Pattern[str]]] = [
    ("ZAM", re.compile(r"WN[IŁL]OSEK\s+(?:O|©)\s+ZASI[ŁL]EK\s+MACIERZY[ŃN]SKI", re.IGNORECASE)),
    ("ZAS-53", re.compile(r"WN[IŁL]OSEK\s+(?:O|©)\s+ZASI[ŁL]EK\s+CHOROBOWY", re.IGNORECASE)),
    ("Z-12", re.compile(r"WN[IŁL]OSEK\s+O\s+ZASI[ŁL]EK\s+POGRZEBOWY", re.IGNORECASE)),
    ("ZNP-7", re.compile(r"WN[IŁL]OSEK\s+O\s+ŚWIADCZENIE\s+REHABILITACYJNE", re.IGNORECASE)),
    ("ERU", re.compile(r"RODZICIELSKIE\s+ŚWIADCZENIE\s+UZUPEŁNIAJĄCE", re.IGNORECASE)),
    ("E-ZLA", re.compile(r"ZAŚWIADCZENIE\s+LEKARSKIE.*NIEZDOLNOŚCI\s+DO\s+PRACY|\bE-?ZLA\b", re.IGNORECASE | re.DOTALL)),
    ("Z-3A", re.compile(r"ZAŚWIADCZENIE\s+PŁATNIKA\s+SKŁADEK.*ZLECEN", re.IGNORECASE | re.DOTALL)),
    ("Z-3B", re.compile(r"ZAŚWIADCZENIE\s+PŁATNIKA\s+SKŁADEK.*POZAROLNICZ", re.IGNORECASE | re.DOTALL)),
    ("Z-3", re.compile(r"ZAŚWIADCZENIE\s+PŁATNIKA\s+SKŁADEK", re.IGNORECASE)),
]

# Kody tytułu ubezpieczenia ZUS (pierwsze 4 cyfry)
_ZUS_TITLE_CODE_MAP: dict[str, tuple[str, bool | None]] = {
    "0110": ("uop", False),
    "0111": ("uop", False),
    "0120": ("uop", False),
    "0411": ("zlecenie", None),
    "0412": ("zlecenie", None),
    "0417": ("zlecenie", None),
    "0426": ("zlecenie", None),
    "0510": ("jdg", False),
    "0511": ("jdg", False),  # osoba współpracująca
    "0512": ("jdg", False),
    "0570": ("jdg", True),   # preferencyjny ZUS (30% min. wynagr.)
    "0572": ("jdg", True),
    "0590": ("jdg", True),   # Mały ZUS Plus
}


def detect_file_kind(filename: str, content: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    if ext == ".pdf" or content.startswith(b"%PDF-"):
        return "pdf"
    if content.startswith((b"\x89PNG", b"\xff\xd8\xff", b"RIFF", b"II*\x00", b"MM\x00*", b"BM")):
        return "image"
    return "pdf"


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _ocr_pil_image(img) -> str:
    import pytesseract  # type: ignore[import-untyped]
    from PIL import ImageOps

    gray = ImageOps.autocontrast(ImageOps.grayscale(img))
    w, h = gray.size
    if w < 1200:
        scale = min(2.5, 1400.0 / max(1, w))
        gray = gray.resize((int(w * scale), int(h * scale)))

    for lang in ("pol", "eng"):
        try:
            txt = pytesseract.image_to_string(gray, lang=lang, config="--oem 1 --psm 6")
            if txt is not None:
                return txt.strip()
        except Exception:
            continue
    return ""


def _ocr_image_bytes(content: bytes) -> tuple[str, bool, list[str]]:
    notes: list[str] = []
    if not is_tesseract_available():
        notes.append("Silnik OCR (tesseract-ocr) nie jest dostępny — zweryfikuj pola ręcznie.")
        return "", False, notes
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as img:
            txt = _ocr_pil_image(img)
            return txt, True, notes
    except Exception as exc:
        notes.append(f"Nie udało się odczytać obrazu przez OCR: {exc}")
        return "", False, notes


def _ocr_pdf_scan_bytes(content: bytes, max_pages: int = 16) -> tuple[str, int, int, bool, list[str]]:
    """
    Thread-safe lokalny OCR (Tesseract PL) dla wielostronicowych skanów PDF (np. sprawy ZUS 8–74 str.).
    Renderuje strony sekwencyjnie przez pypdfium2 (wymagane dla bezpieczeństwa wątkowego),
    a następnie uruchamia Tesseract równolegle na wielu rdzeniach.
    Dla bardzo dużych plików (>16 str.) analizuje pierwsze 10 stron i ostatnie 6 stron (wnioski + Z-3 + decyzja ZUS),
    oraz wykonuje dodatkowy skan wysokiej rozdzielczości dla stron z tabelą zarobków.
    """
    notes: list[str] = []
    if not is_tesseract_available():
        notes.append("Dokument jest skanem bez warstwy tekstowej, a silnik OCR (tesseract-ocr) nie jest zainstalowany.")
        return "", 0, 0, False, notes

    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]
        from PIL import ImageOps
    except Exception as exc:
        notes.append(f"Brak bibliotek do rasteryzacji/OCR skanu PDF: {exc}")
        return "", 0, 0, False, notes

    try:
        doc = pdfium.PdfDocument(content)
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return "", 0, 0, False, notes

        if total_pages <= max_pages:
            selected_indices = list(range(total_pages))
        else:
            head_n = 10
            tail_n = max_pages - head_n
            selected_indices = list(range(head_n)) + list(range(total_pages - tail_n, total_pages))

        # 1. Sekwencyjny render (pypdfium2 nie jest thread-safe!)
        rendered: list[tuple[int, object]] = []
        for idx in selected_indices:
            img = doc[idx].render(scale=1.45).to_pil()
            rendered.append((idx, ImageOps.autocontrast(ImageOps.grayscale(img))))

        # 2. Równoległy OCR stron
        workers = min(4, max(1, os.cpu_count() or 2))

        def _run_ocr(item: tuple[int, object]) -> tuple[int, str]:
            idx, pil_img = item
            return idx, _ocr_pil_image(pil_img)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            page_results = list(ex.map(_run_ocr, rendered))

        # 3. Dodatkowy skan wyższej rozdzielczości dla max 2 stron z tabelą wynagrodzeń / poświadczeniem
        hires_targets = [
            idx
            for idx, txt in page_results
            if re.search(r"SKŁADNIK[IÓW]\s+WYNAGRODZEN|POŚWIADCZENI[EU]\s+UBEZPIECZENI|PODSTAWA\s+WYMIARU\s+SKŁADEK", txt, re.IGNORECASE)
        ][:2]
        if hires_targets:
            hires_rendered = [
                (idx, ImageOps.autocontrast(ImageOps.grayscale(doc[idx].render(scale=2.2).to_pil())))
                for idx in hires_targets
            ]
            with ThreadPoolExecutor(max_workers=workers) as ex:
                hires_results = dict(ex.map(_run_ocr, hires_rendered))
            page_results = [(idx, hires_results.get(idx, txt)) for idx, txt in page_results]

        doc.close()

        ocr_text = "\n\n".join(
            f"[Strona {idx + 1}/{total_pages}]\n{txt}" for idx, txt in page_results if txt.strip()
        ).strip()

        if total_pages > max_pages:
            notes.append(
                f"Dokument jest skanem ({total_pages} str.) — zastosowano lokalny OCR (Tesseract PL) dla {len(selected_indices)} kluczowych stron (pierwsze 10 + ostatnie {max_pages - 10})."
            )
        else:
            notes.append(
                f"Dokument jest skanem bez warstwy tekstowej — zastosowano lokalny OCR (Tesseract PL) dla wszystkich {total_pages} stron."
            )
        return ocr_text, total_pages, len(selected_indices), True, notes
    except Exception as exc:
        notes.append(f"Nie udało się uruchomić lokalnego OCR dla skanu PDF: {exc}")
        return "", 0, 0, False, notes


def _read_raw_xfa_packets(reader: PdfReader) -> list[tuple[str, str]]:
    """Odczytuje pakiety XML XFA (datasets, form, template) ze skompresowanych i nieskompresowanych PDF-ów."""
    packets: list[tuple[str, str]] = []

    try:
        root = reader.trailer.get("/Root")
        if hasattr(root, "get_object"):
            root = root.get_object()
        acro = root.get("/AcroForm") if isinstance(root, dict) else None
        if hasattr(acro, "get_object"):
            acro = acro.get_object()
        xfa_obj = acro.get("/XFA") if isinstance(acro, dict) else None
        if hasattr(xfa_obj, "get_object"):
            xfa_obj = xfa_obj.get_object()

        if isinstance(xfa_obj, StreamObject):
            raw = xfa_obj.get_data()
            if raw:
                packets.append(("xfa", raw.decode("utf-8", errors="ignore")))
        elif isinstance(xfa_obj, ArrayObject):
            i = 0
            while i < len(xfa_obj):
                item = xfa_obj[i]
                if hasattr(item, "get_object"):
                    item = item.get_object()
                if isinstance(item, StreamObject):
                    try:
                        raw = item.get_data()
                        if raw:
                            packets.append(("xfa", raw.decode("utf-8", errors="ignore")))
                    except Exception:
                        pass
                    i += 1
                else:
                    label = str(item).lower()
                    if i + 1 < len(xfa_obj):
                        stream = xfa_obj[i + 1]
                        if hasattr(stream, "get_object"):
                            stream = stream.get_object()
                        if isinstance(stream, StreamObject) and any(
                            k in label for k in ("dataset", "form", "data", "template", "xfa")
                        ):
                            try:
                                raw = stream.get_data()
                                if raw:
                                    packets.append((label, raw.decode("utf-8", errors="ignore")))
                            except Exception:
                                pass
                    i += 2
    except Exception:
        pass

    if not packets:
        try:
            xfa = getattr(reader, "xfa", None)
            if isinstance(xfa, dict):
                for key in ("datasets", "form", "template"):
                    val = xfa.get(key)
                    if isinstance(val, bytes):
                        packets.append((key, val.decode("utf-8", errors="ignore")))
                    elif isinstance(val, str):
                        packets.append((key, val))
        except Exception:
            pass

    return packets


def _walk_xfa_element(
    elem: ET.Element,
    path: list[str],
    entries: list[tuple[str, str]],
) -> None:
    tag = elem.tag.split("}")[-1].strip()
    cur_path = [*path, tag] if tag else path
    txt = (elem.text or "").strip()
    if txt and txt.lower() not in ("0", "false", "off") and len(txt) <= 140 and tag:
        full_key = "/".join(cur_path[-3:])
        entries.append((full_key, txt))
    for child in elem:
        _walk_xfa_element(child, cur_path, entries)


def _extract_acroform_and_xfa_fields(reader: PdfReader) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Wyciąga wypełnione pola z formularzy AcroForm (w tym checkboxy /Btn) oraz Adobe LiveCycle XFA."""
    extracted: dict[str, str] = {}
    entries: list[tuple[str, str]] = []

    def _record(path_key: str, val_str: str) -> None:
        leaf = path_key.split("/")[-1].split(".")[-1].replace("[0]", "").strip()
        if not leaf:
            return
        entries.append((path_key, val_str))
        if leaf not in extracted:
            extracted[leaf] = val_str
        else:
            idx = 2
            while f"{leaf}_{idx}" in extracted:
                idx += 1
            extracted[f"{leaf}_{idx}"] = val_str

    try:
        fields = reader.get_fields() or {}
        for name, field_obj in fields.items():
            if not isinstance(field_obj, dict):
                continue
            val = field_obj.get("/V")
            if val is None and str(field_obj.get("/FT") or "") == "/Btn":
                val = field_obj.get("/AS")
            if val is None:
                continue
            val_str = str(val).strip()
            if not val_str or val_str.lower() in ("/off", "off", "false", "0", "none"):
                continue
            if val_str.startswith("/"):
                val_str = val_str[1:]
            clean_path = re.sub(r"\[\d+\]", "", name).replace(".", "/").strip("/")
            if clean_path:
                _record(clean_path, val_str)
    except Exception:
        pass

    for pkt_label, xml_str in _read_raw_xfa_packets(reader):
        if "<" not in xml_str:
            continue
        if "template" in pkt_label and "datasets" not in xml_str[:400].lower():
            continue
        try:
            root = ET.fromstring(xml_str)
            xfa_entries: list[tuple[str, str]] = []
            _walk_xfa_element(root, [], xfa_entries)
            for path_key, txt in xfa_entries:
                _record(path_key, txt)
        except Exception:
            continue

    return extracted, entries


def _mask_pesel(pesel: str) -> str:
    digits = re.sub(r"\D", "", pesel)
    if len(digits) == 11:
        return f"{digits[:6]}*****"
    return pesel


def _is_valid_pesel(digits: str) -> bool:
    if not re.fullmatch(r"\d{11}", digits):
        return False
    weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
    checksum = sum(int(digits[i]) * weights[i] for i in range(10)) % 10
    control = (10 - checksum) % 10
    return control == int(digits[10])


def _strip_zus_boilerplate(text: str) -> str:
    """
    Usuwa standardowe bloki 'Instrukcja wypełniania', 'Pouczenie' oraz puste/niezaznaczone opcje checkboxów
    z druków ZUS (np. ZAM/Z-3/ZAS-53), aby nie wywoływały fałszywych trafień.
    """
    cleaned = re.sub(
        r"INSTRUKCJA\s+WYPE[ŁL]NIANIA[\s\S]{0,1100}?(?=(?:TWOJE\s+DANE|DANE\s+PŁATNIKA|DANE\s+UBEZPIECZ|DANE\s+WNIOSKODAWC|ZAKRES\s+WNIOSKU|\[Strona|\Z))",
        "\n",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bPOUCZENIE\b[\s\S]{0,1200}?(?=(?:\[Strona|\Z))",
        "\n",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Usuń wiersze zaczynające się od niezaznaczonego pola wyboru (np. "[]", "[ ]", "[|]", "[.]", "[LD]")
    # oraz standardową niezaznaczoną klauzulę na ZAM ("rozwiązał ze mną umowę o pracę z naruszeniem")
    filtered_lines: list[str] = []
    for line in cleaned.splitlines():
        if re.match(r"^\s*(?:\d+\.\s*)?(?:\[\s*\]|\[\s*[|lI\._]\s*\]|\(\s*\)|L\])\s+", line):
            continue
        if re.search(r"ROZWIĄZAŁ\s+ZE\s+MNĄ\s+UMOWĘ\s+O\s+PRACĘ\s+Z\s+NARUSZENIEM", line, re.IGNORECASE):
            continue
        filtered_lines.append(line)
    return "\n".join(filtered_lines)


def _parse_single_amount(raw: str, *, min_val: float = 500.0, max_val: float = 50000.0) -> float | None:
    """Parsuje kwotę np. '7 500,00 zł.', '7.500,50', '950,00', '8 000 zł' -> float."""
    m = re.search(r"(\d{1,2}(?:[\s\xa0\.]\d{3})+(?:[,\.]\d{1,2})?|\d+(?:[,\.]\d{1,2})?)", raw)
    if not m:
        return None
    token = m.group(1).replace(" ", "").replace("\xa0", "")
    if "," in token and "." in token:
        token = token.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,2}\.\d{3}", token):
        token = token.replace(".", "")
    else:
        token = token.replace(",", ".")
    try:
        val = float(token)
        if min_val <= val <= max_val:
            return val
    except ValueError:
        return None
    return None


def _extract_amounts_with_context(
    text: str,
    field_entries: list[tuple[str, str]],
    combined_text: str | None = None,
) -> tuple[list[float], bool]:
    upper = (combined_text if combined_text is not None else text).upper()
    is_net_base = bool(
        re.search(
            r"PODSTAWA\s+WYMIARU\s+ZASIŁKU|PO\s+ODLICZENIU\s+13[,\.]71|PODSTAWA\s+NETTO|PODSTAWAWYMIARUNETTO",
            upper,
        )
    )
    amounts: list[float] = []

    # 1. Pola formularza AcroForm/XFA
    for k, v in field_entries:
        if re.search(r"RAZEM|SUMA|LACZN|ŁĄCZN|OGOL|OGÓŁ|TOTAL|ZADLUZ|ZADŁUŻ|ZALEGL", k, re.IGNORECASE):
            continue
        if re.search(r"KWOT|WYNAGR|PRZYCH|PODSTAW|DOCHOD|BRUTTO|NETTO", k, re.IGNORECASE):
            val = _parse_single_amount(v)
            if val is not None:
                amounts.append(val)

    # 2. Warstwa tekstowa / OCR — pomijamy wiersze podsumowań, podstawy prawne (Dz.U., art.), zadłużenie, dane adresowe
    if not amounts:
        skip_line_pat = re.compile(
            r"\b(?:RAZEM|SUMA|ŁĄCZNIE|OGÓŁEM|TOTAL|DZ\.?\s*U\.|POZ\.|ART\.|ZADŁUŻ|ZALEGŁ|NR\s+SPRAWY|KOD\s+POCZTOW|TELEFON|NIP|REGON|PESEL)\b",
            re.IGNORECASE,
        )
        for line in text.splitlines():
            if skip_line_pat.search(line):
                continue
            dec_matches = re.findall(
                r"(?<!\d)(?<!\d\.)(\d{1,2}[\s\xa0\.]\d{3}[,\.]\d{2}|\d{3,5}[,\.]\d{2})(?!\d|\.\d)",
                line,
            )
            for raw in dec_matches:
                val = _parse_single_amount(raw)
                if val is not None:
                    amounts.append(val)
            if not dec_matches:
                int_matches = re.findall(
                    r"(?<!\d)(?<!\d\.)(\d{1,2}[\s\xa0\.]\d{3}|\d{3,5})(?!\s*[,\.]\d)\s*(?:zł|zl|PLN)\b",
                    line,
                    re.IGNORECASE,
                )
                for raw in int_matches:
                    val = _parse_single_amount(raw)
                    if val is not None:
                        amounts.append(val)

    return amounts, is_net_base


def _pick_primary_and_sort_forms(
    detected: list[str],
    text: str,
    combined_text: str,
    filename: str,
) -> list[str]:
    if len(detected) <= 1:
        return detected

    head_800 = text[:800]
    head_400 = text[:400]
    fn_upper = filename.upper().replace("_", " ")
    pat_map = dict(_FORM_PATTERNS)

    def _score(code: str) -> tuple[int, int]:
        score = 0
        for hint_code, hint_pat in _TITLE_HINTS:
            if hint_code == code and hint_pat.search(head_800):
                score += 200
        pat = pat_map[code]
        if pat.search(head_400):
            score += 120
        if pat.search(fn_upper):
            score += 80
        # W sprawach wielodokumentowych preferuj główny wniosek nad POG/pismem pomocniczym
        if code in ("POG",):
            score -= 60
        m = pat.search(combined_text)
        pos = m.start() if m else 10**9
        return (-score, pos)

    return sorted(detected, key=_score)


def _extract_applicant_name(text: str, field_entries: list[tuple[str, str]]) -> str | None:
    skip_pat = re.compile(r"PLATNIK|PŁATNIK|MATK|DZI|OJC", re.IGNORECASE)
    prefer_pat = re.compile(r"UBEZPIECZ|WNIOSKODAWC|PRACOWNIK|PACJENT", re.IGNORECASE)

    def _find_field(pat: str) -> str | None:
        regex = re.compile(pat, re.IGNORECASE)
        preferred = [v for k, v in field_entries if regex.search(k) and prefer_pat.search(k) and not skip_pat.search(k)]
        if preferred:
            return preferred[0]
        generic = [v for k, v in field_entries if regex.search(k) and not skip_pat.search(k)]
        return generic[0] if generic else None

    imie = _find_field(r"(?:^|[/_])IMI[EĘ]")
    nazwisko = _find_field(r"(?:^|[/_])NAZWISK")
    if imie or nazwisko:
        return " ".join(p for p in [imie, nazwisko] if p).strip() or None

    m_block = re.search(r"WNIOSKODAWCA\s*:\s*\n\s*([A-ZŁŚĆŻŹÓŃ][^\n]{2,80})", text)
    if m_block:
        candidate = m_block.group(1).strip()
        if not candidate.upper().startswith("PESEL"):
            return candidate
    m_inline = re.search(
        r"(?:IMI[ĘE]\s+I\s+NAZWISKO|UBEZPIECZON[YA]|PACJENT)\s*:\s*([A-ZŁŚĆŻŹÓŃ][A-Za-zŁŚĆŻŹÓŃąłśćżźóń\- ]{2,70})",
        text,
        re.IGNORECASE,
    )
    if m_inline:
        candidate = m_inline.group(1).strip()
        if not re.search(r"PESEL|NIP|REGON|DATA", candidate, re.IGNORECASE):
            return candidate
    return None


def _extract_pesel(combined_text: str, field_entries: list[tuple[str, str]]) -> str | None:
    skip_pat = re.compile(r"PLATNIK|PŁATNIK|DZI|MATK|OJC", re.IGNORECASE)
    prefer_pat = re.compile(r"UBEZPIECZ|WNIOSKODAWC|PRACOWNIK|PACJENT", re.IGNORECASE)

    preferred = [v for k, v in field_entries if "PESEL" in k.upper() and prefer_pat.search(k) and not skip_pat.search(k)]
    if preferred:
        return preferred[0]
    generic = [v for k, v in field_entries if "PESEL" in k.upper() and not skip_pat.search(k)]
    if generic:
        return generic[0]

    # Preferuj 11-cyfrowe ciągi po etykiecie PESEL lub przechodzące sumę kontrolną
    m_labeled = re.search(r"PESEL\s*[:\-]?\s*(\d{11}|\d{6}\*{5})", combined_text, re.IGNORECASE)
    if m_labeled:
        return m_labeled.group(1)

    for m_pesel in re.finditer(r"\b(\d{11})\b", combined_text):
        cand = m_pesel.group(1)
        if _is_valid_pesel(cand):
            return cand

    # Fallback dla testowych/zanonimizowanych 11-cyfrowych numerów
    m_any = re.search(r"\b(\d{11})\b", combined_text)
    if m_any:
        return m_any.group(1)
    return None


def _parse_iso_date_token(token: str) -> date | None:
    token = token.strip()
    m_iso = re.fullmatch(r"(\d{4})[-./](\d{2})[-./](\d{2})", token)
    if m_iso:
        try:
            return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        except ValueError:
            return None
    m_pl = re.fullmatch(r"(\d{2})[-./](\d{2})[-./](\d{4})", token)
    if m_pl:
        try:
            return date(int(m_pl.group(3)), int(m_pl.group(2)), int(m_pl.group(1)))
        except ValueError:
            return None
    return None


def _extract_letter_codes_and_ezla(
    clean_text: str,
    field_entries: list[tuple[str, str]],
    detected_forms: list[str],
) -> tuple[str | None, str | None, int | None, list[str], bool | None]:
    """Odczytuje numer e-ZLA, okres niezdolności, liczbę dni i kody literowe (A–E) bez wymuszania kodu B."""
    ezla_num: str | None = None
    m_num = re.search(r"\b((?:E-?ZLA|ZLA)[/\- ]?[A-Z0-9/\-]{4,24}|[A-Z]{2}\s*\d{7,9})\b", clean_text, re.IGNORECASE)
    if m_num and ("E-ZLA" in detected_forms or "ZAS-53" in detected_forms or "ZAS-12" in detected_forms):
        ezla_num = m_num.group(1).strip()

    incapacity_period: str | None = None
    incapacity_days: int | None = None
    m_period = re.search(
        r"(?:NIEZDOLNOŚC[IĄ]\s+DO\s+PRACY|OKRES\s+ZWOLNIENIA|OD\s+DNIA|OD)\s*[:\-]?\s*"
        r"(\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2})\s*(?:DO\s+DNIA|DO|[-–])\s*"
        r"(\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2})",
        clean_text,
        re.IGNORECASE,
    )
    if m_period:
        d1 = _parse_iso_date_token(m_period.group(1))
        d2 = _parse_iso_date_token(m_period.group(2))
        if d1 and d2 and d2 >= d1:
            incapacity_period = f"{d1.isoformat()} – {d2.isoformat()}"
            incapacity_days = (d2 - d1).days + 1

    codes: list[str] = []
    # 1. Z pól AcroForm/XFA
    for k, v in field_entries:
        if re.search(r"KOD.*LITER|KOD_?CHOROB|LETTER_?CODE|KODY", k, re.IGNORECASE):
            for ch in re.findall(r"\b([A-E])\b", v.upper()):
                if ch not in codes:
                    codes.append(ch)

    # 2. Z tekstu (jawne oznaczenie kodu literowego, np. "kod literowy: B", "kod: B", "kody: A, B", "kod B")
    for m_code in re.finditer(
        r"KOD(?:Y)?(?:\s+LITEROW[EY])?\s*[:\-]?\s*[\"„']?([A-E](?:\s*[,/]\s*[A-E])*)[\"”']?(?!\w)",
        clean_text,
        re.IGNORECASE,
    ):
        for ch in re.findall(r"[A-E]", m_code.group(1).upper()):
            if ch not in codes:
                codes.append(ch)

    # Jawny "kod literowy: brak" / "kod: brak" / "bez kodu B"
    explicit_no_code_b = bool(
        re.search(
            r"KOD(?:\s+LITEROW[EY])?\s*[:\-]?\s*(?:BRAK|NIE\s+DOTYCZY|-|—)|BEZ\s+KODU\s*[\"„']?B[\"”']?",
            clean_text,
            re.IGNORECASE,
        )
    )

    has_code_b: bool | None = None
    if "B" in codes:
        has_code_b = True
    elif explicit_no_code_b:
        has_code_b = False
    elif "E-ZLA" in detected_forms:
        # Na wystawionym e-ZLA brak kodu B oznacza zwykłe zwolnienie chorobowe (NIE ciążę!)
        has_code_b = False

    return ezla_num, incapacity_period, incapacity_days, codes, has_code_b


def analyze_pdf_bytes(filename: str, content: bytes) -> PdfAnalysisResult:
    """
    Uniwersalny deterministyczny parser dokumentów ZUS (warstwa tekstowa + AcroForm + XFA XML + lokalny OCR PL dla skanów i obrazów).
    Zasada 'zero zgadywania': każde pole nieodczytane z dokumentu pozostaje puste (None).
    """
    file_kind = detect_file_kind(filename, content)
    text = ""
    form_fields: dict[str, str] = {}
    field_entries: list[tuple[str, str]] = []
    notes: list[str] = []
    ocr_required = False
    ocr_used = False
    page_count = 0
    ocr_pages_processed = 0

    if file_kind == "image":
        page_count = 1
        ocr_text, used, ocr_notes = _ocr_image_bytes(content)
        notes.extend(ocr_notes)
        ocr_used = used
        ocr_pages_processed = 1 if used else 0
        text = ocr_text
        if len(text.strip()) < 20:
            ocr_required = True
    else:
        pdf_parse_failed = False
        try:
            reader = PdfReader(io.BytesIO(content))
            page_count = len(reader.pages)
            pages_text = [(page.extract_text() or "") for page in reader.pages[:16]]
            text = "\n".join(pages_text).strip()
            form_fields, field_entries = _extract_acroform_and_xfa_fields(reader)
        except Exception as exc:
            pdf_parse_failed = True
            ocr_required = True
            notes.append(f"Nie udało się odczytać struktury pliku PDF: {exc}")

        if not pdf_parse_failed and len(text) < 25 and not form_fields:
            ocr_text, total_p, done_p, used, ocr_notes = _ocr_pdf_scan_bytes(content, max_pages=16)
            notes.extend(ocr_notes)
            if total_p:
                page_count = total_p
            ocr_pages_processed = done_p
            ocr_used = used
            if used and len(ocr_text.strip()) >= 20:
                text = ocr_text
                ocr_required = False
            else:
                ocr_required = True
                notes.append(
                    "Dokument nie zawiera warstwy tekstowej ani pól formularza. Zweryfikuj i uzupełnij pola ręcznie."
                )

    fields_blob = "\n".join(f"{k}: {v}" for k, v in field_entries)
    combined_text = f"{text}\n{fields_blob}".strip()
    clean_text = _strip_zus_boilerplate(combined_text)
    upper = combined_text.upper()
    clean_upper = clean_text.upper()

    # 1. Rozpoznawanie kodów formularzy ZUS (z treści + pól, a dopiero awaryjnie z nazwy pliku)
    detected = [code for code, pat in _FORM_PATTERNS if pat.search(combined_text)]
    if not detected:
        fn_upper = filename.upper().replace("_", " ")
        detected = [code for code, pat in _FORM_PATTERNS if pat.search(fn_upper)]
        if detected:
            notes.append(f"Kod formularza ({', '.join(detected)}) rozpoznano pomocniczo na podstawie nazwy pliku.")
    else:
        detected = _pick_primary_and_sort_forms(detected, text, combined_text, filename)

    primary_form = detected[0] if detected else "UNKNOWN"
    form_desc = _FORM_DESCRIPTIONS.get(primary_form)

    # 2. Dane osobowe (ubezpieczony, PESEL)
    applicant_name = _extract_applicant_name(text, field_entries)
    pesel_raw = _extract_pesel(combined_text, field_entries)
    pesel_masked = _mask_pesel(pesel_raw) if pesel_raw else None

    # 3. Kod tytułu ubezpieczenia ZUS (np. 01 10, 04 11, 05 10, 05 70)
    zus_title_code: str | None = None
    m_zcode = re.search(r"(?:KOD\s+TYTUŁU(?:\s+UBEZPIECZENIA)?|TYTUŁ\s+UBEZPIECZENIA)\s*[:\-]?\s*(0[145]\s?\d{2})", clean_upper)
    if m_zcode:
        zus_title_code = re.sub(r"\s+", "", m_zcode.group(1))

    # 4. Tytuł ubezpieczenia — ZERO ZGADYWANIA (zaczyna jako None!)
    suggested_title: str | None = None
    if primary_form in ("ERU", "ERSU"):
        suggested_title = "none"
        notes.append(
            f"Rozpoznano formularz {primary_form} ({form_desc}). Dotyczy rodzicielskiego świadczenia uzupełniającego (Mama 4+), a nie zasiłku macierzyńskiego z ubezpieczenia chorobowego."
        )
    elif zus_title_code and zus_title_code in _ZUS_TITLE_CODE_MAP:
        suggested_title = _ZUS_TITLE_CODE_MAP[zus_title_code][0]
    elif primary_form == "Z-3A" or re.search(r"UMOW[AYĘ]\s+ZLECEN", clean_upper):
        suggested_title = "zlecenie"
    elif (
        primary_form == "Z-3B"
        or re.search(r"DZIAŁALNOŚC[IĄ]\s+GOSPODARCZ|POZAROLNICZ[ĄA]\s+DZIAŁALNOŚ|OSOB[AY]\s+WSPÓŁPRACUJĄC|OSOB[AY]\s+PROWADZĄC[AEY]\s+DZIAŁALNOŚ", clean_upper)
    ):
        suggested_title = "jdg"
    elif re.search(r"UMOW[AYĘ]\s+O\s+PRAC[ĘE]|STOSUNKU\s+PRACY", clean_upper):
        suggested_title = "uop"
    elif primary_form in ("Z-3", "WNIOSEK URLOPOWY KP") or ("Z-3" in detected and primary_form != "ZAM"):
        suggested_title = "uop"
    elif "Z-3A" in detected and primary_form != "ZAM":
        suggested_title = "zlecenie"
    elif "Z-3B" in detected and primary_form != "ZAM":
        suggested_title = "jdg"

    # 5. Zwolnienie chorobowe, kody literowe A-E i ciąża (ZERO wymuszania ciąży!)
    ezla_num, incapacity_period, incapacity_days, letter_codes, has_code_b = _extract_letter_codes_and_ezla(
        clean_text, field_entries, detected
    )
    pregnancy_confirmed: bool | None = None
    if has_code_b is True:
        pregnancy_confirmed = True
    elif re.search(
        r"ZASIŁEK\s+CHOROBOWY\s+W\s+CIĄŻY|W\s+OKRESIE\s+CIĄŻY|STAN\s+CIĄŻY|CIĄŻA\s+POTWIERDZONA|ZASIŁEK\s+W\s+WYSOKOŚCI\s+ZASIŁKU\s+MACIERZYŃSKIEGO",
        clean_upper,
    ):
        pregnancy_confirmed = True
        if has_code_b is None and "E-ZLA" not in detected:
            has_code_b = True
    elif has_code_b is False:
        pregnancy_confirmed = False

    # Szczególne ustanie zatrudnienia / ubezpieczenia (art. 30 / art. 7)
    employment_terminated_special: bool | None = None
    termination_reason: str | None = None
    if re.search(r"ZASIŁEK\s+W\s+WYSOKOŚCI\s+ZASIŁKU\s+MACIERZYŃSKIEGO|Z\s+POWODU\s+(?:LIKWIDACJI|UPADŁOŚCI)", clean_upper):
        employment_terminated_special = True
        termination_reason = "bankruptcy_liquidation"
    elif re.search(r"ŚMIERC[IĄ]\s+PRACODAWCY", clean_upper):
        employment_terminated_special = True
        termination_reason = "employer_death"
    elif re.search(r"NARUSZENIEM\s+PRZEPISÓW\s+PRAWA.*WYROK|PRAWOMOCNYM\s+ORZECZENIEM\s+SĄDU", clean_upper):
        employment_terminated_special = True
        termination_reason = "unlawful_termination_court_ruling"
    elif primary_form == "Z-10" or re.search(r"PO\s+USTANIU\s+(?:TYTUŁU\s+)?UBEZPIECZENIA", clean_upper):
        employment_terminated_special = True
        termination_reason = "post_employment_art7"

    # Zwolnienie z okresu wyczekiwania (art. 4 ust. 3)
    waiting_exemption: str | None = None
    if re.search(r"WYPADEK\s+W\s+DRODZE\s+DO\s+PRACY|W\s+DRODZE\s+DO\s+LUB\s+Z\s+PRACY", clean_upper):
        waiting_exemption = "commute_accident"

    # 6. Liczba dzieci — ZERO ZGADYWANIA (zaczyna jako None!)
    children_count: int | None = None
    for k, v in field_entries:
        if re.search(r"LICZB.*DZIEC|DZIECI|URODZIL", k, re.IGNORECASE):
            m_num = re.search(r"\d+", v)
            if m_num:
                val_c = int(m_num.group(0))
                if 1 <= val_c <= 15:
                    children_count = val_c
                    break
    if children_count is None:
        m_kids = re.search(
            r"URODZIŁAM\s+0?(\d{1,2})\s+DZIECI|LICZBA\s+DZIECI[^\d]{0,15}0?(\d{1,2})|\b([2-9])\s+DZIECI\b",
            clean_upper,
        )
        if m_kids:
            val_c = int(m_kids.group(1) or m_kids.group(2) or m_kids.group(3))
            if 1 <= val_c <= 15:
                children_count = val_c
        elif re.search(r"BLIŹNI[ĘE]T|BLIŹNIAK", clean_upper):
            children_count = 2
        elif re.search(r"TROJACZK", clean_upper):
            children_count = 3

    # 7. Dane macierzyńskie / rodzicielskie (tylko gdy faktycznie obecne w treści!)
    scenario: str | None = None
    if re.search(r"PRZYSPOSOBIENI|ADOPCJ", clean_upper):
        scenario = "adoption"
    elif re.search(r"RODZIN[AYĘ]\s+ZASTĘPCZ", clean_upper):
        scenario = "foster"
    elif (
        primary_form in ("ZAM", "ZUR", "ZAO", "WNIOSEK URLOPOWY KP", "AKT URODZENIA USC")
        or re.search(r"ZASIŁEK\s+MACIERZYŃSKI|URLOP\s+MACIERZYŃSKI|URLOP\s+RODZICIELSKI|URLOP\s+OJCOWSKI|URODZENI[EA]\s+DZIECKA|MARTWE\s+URODZENIE", clean_upper)
    ):
        scenario = "birth"

    payment_variant: str | None = None
    if re.search(r"81[,\.]5\s*%|PEŁNEGO\s+WYMIARU\s+URLOPU\s+MACIERZYŃSKIEGO\s+I\s+RODZICIELSKIEGO", clean_upper):
        payment_variant = "81_5"
    elif re.search(r"100\s*%.*70\s*%", clean_upper):
        payment_variant = "100_70"

    has_za_zyciem: bool | None = None
    for m_zz in re.finditer(
        r"ZAŚWIADCZENI[EA]\s+[\"„']?ZA\s+ŻYCIEM|ART\.\s*4\s+UST\.\s*3\s+USTAWY.*ZA\s+ŻYCIEM",
        clean_upper,
    ):
        window = clean_upper[m_zz.start() : m_zz.end() + 120]
        if not re.search(r"JE[ŚS]LI\s+DOTYCZY|JE[ŻZ]ELI\s+DOTYCZY", window):
            has_za_zyciem = True
            break
    stillbirth: bool | None = True if re.search(r"MARTW(?:E|O)\s*URODZEN|MARTWOURODZON", clean_upper) else None
    premature: bool | None = True if re.search(r"WCZEŚNIAK|UZUPEŁNIAJĄC(?:Y|EGO)\s+URLOP(?:U)?\s+MACIERZYŃSK|MASA\s+PONIŻEJ\s+1000", clean_upper) else None
    combine_work: bool | None = True if re.search(r"ŁĄCZENIE\s+URLOPU\s+RODZICIELSKIEGO\s+Z\s+PRACĄ|ŁĄCZENIE\s+KORZYSTANIA\s+Z\s+URLOPU\s+RODZICIELSKIEGO", clean_upper) else None
    father_paternity: bool | None = True if (primary_form == "ZAO" or re.search(r"URLOP(?:U)?\s+OJCOWSK", clean_upper)) else None
    mother_uninsured: bool | None = True if re.search(r"MATKA\s+(?:DZIECKA\s+)?NIE\s+POSIADA\s+TYTUŁU|MATKA\s+NIEUBEZPIECZONA", clean_upper) else None

    gestation_week: int | None = None
    m_gest = re.search(r"(\d{2})\.?\s*(?:TYDZIEŃ|TYGODNIU|HBD|TC)\s*(?:CIĄŻY)?", clean_upper)
    if m_gest:
        gw = int(m_gest.group(1))
        if 20 <= gw <= 42:
            gestation_week = gw

    birth_weight: int | None = None
    m_wt = re.search(r"(?:MASA\s+URODZENIOWA|WAGA\s+URODZENIOWA)[^\d]{0,15}(\d{3,4})\s*(?:G|GRAM)", clean_upper)
    if m_wt:
        bw = int(m_wt.group(1))
        if 300 <= bw <= 6000:
            birth_weight = bw

    # Data urodzenia dziecka
    child_birth_date: str | None = None
    m_dob = re.search(
        r"(?:DATA\s+URODZENIA\s+DZIECKA|URODZENI[AE]\s+DZIECKA\s+(?:W\s+DNIU\s+)?)[:\-]?\s*(\d{2}[.\-/]\d{2}[.\-/]\d{4}|\d{4}[.\-/]\d{2}[.\-/]\d{2})",
        clean_upper,
    )
    if m_dob:
        d_dob = _parse_iso_date_token(m_dob.group(1))
        if d_dob:
            child_birth_date = d_dob.isoformat()

    # Wymiar etatu
    fte_fraction: float | None = None
    m_fte = re.search(r"WYMIAR(?:ZE)?\s+(?:CZASU\s+PRACY|ETATU)\s*[:\-]?\s*(1/2|1/4|3/4|0[,\.]\d{1,2}|1[,\.]00?)", clean_upper)
    if m_fte:
        tok = m_fte.group(1).replace(",", ".")
        frac_map = {"1/2": 0.5, "1/4": 0.25, "3/4": 0.75}
        fte_fraction = frac_map.get(tok)
        if fte_fraction is None:
            try:
                val_f = float(tok)
                if 0.05 <= val_f <= 1.0:
                    fte_fraction = val_f
            except ValueError:
                pass

    # 8. Daty i okresy
    periods = list(dict.fromkeys(re.findall(r"\b\d{2}[.\-/]\d{2}[.\-/]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", combined_text)))[:10]

    # 9. Liczba ubezpieczonych u płatnika (Z-3 / Z-3a) — ZERO ZGADYWANIA
    emp_count: int | None = None
    emp_match = re.search(r"LICZB[AĘ]\s+UBEZPIECZONYCH[^\d]{0,30}(\d{1,5})", clean_upper)
    if emp_match:
        emp_count = int(emp_match.group(1))
    elif re.search(r"\[[X✓✔]\]\s*POWYŻEJ\s+20\s+UBEZPIECZONYCH", clean_upper):
        emp_count = 21
        notes.append("Na formularzu Z-3 zaznaczono płatnika zgłaszającego powyżej 20 ubezpieczonych.")
    elif re.search(r"\[[X✓✔]\]\s*DO\s+20\s+UBEZPIECZONYCH", clean_upper):
        emp_count = 10
        notes.append("Na formularzu Z-3 zaznaczono płatnika zgłaszającego do 20 ubezpieczonych (wypłaca ZUS).")

    # 10. Zadłużenie składkowe (art. 2a) — rozróżnienie "...figuruje zadłużenie...: NIE" vs ": TAK"
    has_debt: bool | None = None
    debt_pln: float | None = None
    if re.search(
        r"FIGURUJE\s+ZAD[LŁ]U[ŻZ]ENI[EA][\s\S]{0,120}?:\s*NIE\b|"
        r"ZAD[LŁ]U[ŻZ]ENI[EA]\s+Z\s+TYTU[LŁ]U\s+SK[LŁ]ADEK[\s\S]{0,100}?:\s*NIE\b|"
        r"NIE\s+ZALEGA\s+W\s+OP[LŁ]ACANIU\s+SK[LŁ]ADEK|BRAK\s+ZAD[LŁ]U[ŻZ]ENIA",
        clean_upper,
    ):
        has_debt = False
        debt_pln = 0.0
    elif re.search(
        r"FIGURUJE\s+ZAD[LŁ]U[ŻZ]ENI[EA][\s\S]{0,120}?:\s*TAK\b|"
        r"ZAD[LŁ]U[ŻZ]ENI[EA]\s+Z\s+TYTU[LŁ]U\s+SK[LŁ]ADEK|ART\.\s*2A\s+USTAWY|ZALEG[LŁ]O[ŚS]C[IĄ]\s+SK[LŁ]ADKOW",
        clean_upper,
    ):
        has_debt = True
        m_debt = re.search(r"(?:ZAD[LŁ]U[ŻZ]ENI[EA]|ZALEG[LŁ]O[ŚS][ĆC])[^\d]{0,40}(\d{1,3}(?:[\s\xa0\.]\d{3})*[,\.]\d{2})", clean_upper)
        if m_debt:
            debt_pln = _parse_single_amount(m_debt.group(1), min_val=0.01, max_val=500000.0)

    # 11. Ostrożna weryfikacja statusu ubezpieczenia (3-stanowa: confirmed / denied / unknown; odporna na braki diakrytyków OCR)
    has_explicit_denial = bool(
        re.search(
            r"NIE\s+PODLEGA|NIE\s+JEST\s+OBJ[EĘ]T[YA]\s+(?:OBOWI[AĄ]ZKOWYM\s+|DOBROWOLNYM\s+)?UBEZPIECZENIEM\s+CHOROBOWYM|"
            r"BRAK\s+(?:ZG[LŁ]OSZENIA\s+DO\s+)?UBEZPIECZENIA\s+CHOROBOWEGO|BRAK\s+ZG[LŁ]OSZENIA\s+DO\s+UBEZPIECZE[NŃ]|"
            r"ODMOWA\s+PRAWA|ODM[OÓ]WI[CĆ]\s+PRAWA|DECYZJA\s+ODMAWIAJ[AĄ]CA|DECYZJA\s+ODMOWNA|"
            r"WY[LŁ][AĄ]CZON[YA]\s+Z\s+UBEZPIECZENIA|UBEZPIECZENIE\s+CHOROBOWE\s*:\s*NIE|UMOWA\s+DLA\s+POZORU",
            clean_upper,
        )
    )
    has_explicit_confirmation = bool(
        re.search(
            r"PODLEGA(?:Ł[AO]?)?\s+(?:OBOWIĄZKOWEMU\s+|DOBROWOLNEMU\s+)?UBEZPIECZENIU\s+CHOROBOWEMU|"
            r"OBJĘT[YA]\s+(?:OBOWIĄZKOWYM\s+|DOBROWOLNYM\s+)?UBEZPIECZENIEM\s+CHOROBOWYM|"
            r"UBEZPIECZENIE\s+CHOROBOWE\s*:\s*TAK|"
            r"PRZYZNANO\s+ZASIŁEK|PRZYZNAĆ\s+PRAWO|ZASIŁEK\s+MACIERZYŃSKI\s+WYPŁACON",
            clean_upper,
        )
    )

    sickness_status: SicknessInsuranceStatus = "unknown"
    if ocr_required or (not detected and len(clean_text) < 25):
        verification_status = "needs_review"
        confidence = "low"
        insurance_verified = False
        sickness_status = "unknown"
        notes.append("Status wymaga weryfikacji przez użytkownika przed uruchomieniem symulacji.")
    elif has_explicit_denial:
        verification_status = "denied"
        confidence = "high"
        insurance_verified = False
        sickness_status = "denied"
        if has_debt:
            notes.append("W treści dokumentu wykryto odmowę / wstrzymanie prawa do zasiłku z powodu zadłużenia składek (art. 2a).")
        else:
            notes.append("W treści dokumentu wykryto decyzję odmowną lub adnotację o braku podlegania ubezpieczeniu chorobowemu.")
    elif has_explicit_confirmation:
        verification_status = "verified"
        confidence = "high"
        insurance_verified = True
        sickness_status = "confirmed"
        notes.append("W treści dokumentu potwierdzono podleganie ubezpieczeniu chorobowemu lub przyznanie świadczenia.")
    else:
        verification_status = "needs_review"
        confidence = "medium" if detected else "low"
        insurance_verified = False
        sickness_status = "unknown"
        if detected:
            notes.append(
                f"Rozpoznano formularz {', '.join(detected)} ({form_desc or 'druk ZUS'}). Potwierdź odczytane pola i uzupełnij brakujące przed przeliczeniem."
            )

    if form_fields:
        notes.append(f"Odczytano {len(form_fields)} wypełnionych pól formularza PDF (AcroForm/XFA).")

    # 12. Kwoty (wyłącznie z treści/pól — brak wymyślania 7000 zł!)
    params = parameter_store.get()
    rate = params.employee_social_security_rate
    parsed_amounts, amount_is_net_base = _extract_amounts_with_context(clean_text, field_entries, combined_text)

    suggested_salary: float | None = None
    suggested_custom_base: float | None = None
    if parsed_amounts:
        avg_amount = round(sum(parsed_amounts[:12]) / min(len(parsed_amounts), 12), 2)
        if amount_is_net_base:
            suggested_custom_base = avg_amount
            suggested_salary = round(avg_amount / (1.0 - rate), 2)
            notes.append(
                f"Wykryto podstawę wymiaru zasiłku (już po odliczeniu składek): {suggested_custom_base:.2f} zł."
            )
        else:
            suggested_salary = avg_amount
            suggested_custom_base = round(avg_amount * (1.0 - rate), 2)
            notes.append(
                f"Wykryto {len(parsed_amounts)} kwot brutto (śr. {avg_amount:.2f} zł) -> szacowana podstawa po -{rate*100:.2f}%: {suggested_custom_base:.2f} zł."
            )

    # 13. Klasyfikacja domeny dokumentu i docelowego kalkulatora
    document_domain: DocumentDomain = "unknown"
    recommended_calculator: RecommendedCalculator = "both"
    guidance_banner: str | None = None

    if primary_form in ("ZAS-36", "ZAS-38", "Z-15A", "Z-15B"):
        document_domain = "care_benefit"
        recommended_calculator = "info_only"
        guidance_banner = (
            f"Rozpoznano wniosek o zasiłek opiekuńczy ({primary_form}). Zasiłek opiekuńczy wynosi 80% podstawy wymiaru "
            "i przysługuje do 60 dni w roku (chore dziecko do 14 lat / zdrowe do 8 lat) lub 14 dni (inny członek rodziny)."
        )
    elif primary_form in ("ERU", "ERSU", "Z-12"):
        document_domain = "other_benefit"
        recommended_calculator = "info_only"
        guidance_banner = (
            f"Rozpoznano formularz {primary_form} ({form_desc}). To odrębne świadczenie pozachorobowe — sprawdź szczegóły w sekcji Wsparcie i Dokumenty."
        )
    elif primary_form in ("ZAM", "ZUR", "ZAO", "WNIOSEK URLOPOWY KP", "AKT URODZENIA USC") or (
        scenario in ("birth", "adoption", "foster") and primary_form not in ("E-ZLA", "ZAS-53", "ZAS-12", "ZNP-7", "Z-10")
    ):
        document_domain = "maternity_parental"
        recommended_calculator = "maternity_parental"
    elif primary_form in ("E-ZLA", "ZAS-53", "ZAS-12", "ZNP-7", "Z-10") or employment_terminated_special:
        if has_code_b is True or pregnancy_confirmed is True or termination_reason in ("bankruptcy_liquidation", "employer_death", "unlawful_termination_court_ruling"):
            document_domain = "sickness_pregnancy"
            recommended_calculator = "pregnancy_sickness"
        else:
            document_domain = "sickness_general"
            recommended_calculator = "pregnancy_sickness"
            guidance_banner = (
                "Rozpoznano dokument zwolnienia / zasiłku chorobowego bez adnotacji o ciąży (brak kodu literowego B). "
                "Nie ustawiono automatycznie ciąży ani wynagrodzenia — uzupełnij brakujące pola przed wyliczeniem."
            )
    elif primary_form in ("Z-3", "Z-3A", "Z-3B", "POŚWIADCZENIE UBEZPIECZENIA", "ZUS ZUA", "ZUS ZZA", "ZUS ZWUA", "US-7", "RD-3"):
        document_domain = "payer_or_insurance_certificate"
        recommended_calculator = "both"
    elif pregnancy_confirmed is True:
        document_domain = "sickness_pregnancy"
        recommended_calculator = "pregnancy_sickness"

    # 14. Jawna lista brakujących pól potrzebnych do kalkulatora
    missing_fields: list[str] = []
    if recommended_calculator in ("pregnancy_sickness", "maternity_parental", "both"):
        if suggested_title is None:
            missing_fields.append("Tytuł ubezpieczenia")
        if suggested_salary is None and suggested_custom_base is None and suggested_title != "none":
            missing_fields.append("Wynagrodzenie / podstawa wymiaru (zł)")
        if sickness_status == "unknown":
            missing_fields.append("Status ubezpieczenia chorobowego")
        if recommended_calculator == "maternity_parental":
            if scenario is None:
                missing_fields.append("Scenariusz (poród / adopcja / rodzina zastępcza)")
            if children_count is None:
                missing_fields.append("Liczba dzieci")
            if payment_variant is None:
                missing_fields.append("Wariant wypłaty (81,5% lub 100%/70%)")
        if suggested_title in ("uop", "zlecenie") and emp_count is None:
            missing_fields.append("Liczba ubezpieczonych u płatnika")

    # 15. Zwięzła lista kluczowych odczytanych pól (wyłącznie faktycznie odczytane!)
    key_fields: dict[str, str] = {}
    if form_desc:
        key_fields["Formularz"] = f"{primary_form} — {form_desc}"
    if applicant_name:
        key_fields["Wnioskodawca"] = applicant_name
    if pesel_masked:
        key_fields["PESEL"] = pesel_masked
    if zus_title_code:
        key_fields["Kod tytułu ZUS"] = zus_title_code
    if ezla_num:
        key_fields["Nr e-ZLA"] = ezla_num
    if incapacity_period:
        days_suffix = f" ({incapacity_days} dni)" if incapacity_days else ""
        key_fields["Okres niezdolności"] = f"{incapacity_period}{days_suffix}"
    if letter_codes:
        key_fields["Kody literowe"] = ", ".join(letter_codes)
    elif has_code_b is False:
        key_fields["Kod literowy B (ciąża)"] = "Brak (zwykłe zwolnienie)"
    if children_count is not None:
        key_fields["Liczba dzieci"] = str(children_count)
    if child_birth_date:
        key_fields["Data urodzenia dziecka"] = child_birth_date
    if fte_fraction is not None:
        key_fields["Wymiar etatu"] = str(fte_fraction)
    if has_za_zyciem:
        key_fields["Zaświadczenie „Za życiem”"] = "Tak"
    if premature:
        key_fields["Wcześniak / hospitalizacja"] = "Tak"
    if stillbirth:
        key_fields["Martwe urodzenie"] = "Tak"
    if has_debt:
        key_fields["Zadłużenie składek (art. 2a)"] = f"{debt_pln:.2f} zł" if debt_pln else "Wykryto w treści"
    for k, v in list(form_fields.items())[:6]:
        if "PESEL" in k.upper():
            continue
        if len(key_fields) < 12:
            key_fields[k] = v

    preview_source = fields_blob if (not text and fields_blob) else combined_text
    preview = preview_source[:800] if preview_source else "(Brak warstwy tekstowej ani pól AcroForm/XFA)"

    return PdfAnalysisResult(
        filename=filename,
        file_kind="image" if file_kind == "image" else "pdf",
        detected_forms=detected,
        document_domain=document_domain,
        recommended_calculator=recommended_calculator,
        extracted_text_preview=preview,
        verification_status=verification_status,
        sickness_insurance_status=sickness_status,
        confidence=confidence,
        insurance_verified=insurance_verified,
        suggested_insurance_title=suggested_title,
        suggested_gross_salary=suggested_salary,
        suggested_custom_benefit_base=suggested_custom_base,
        extracted_fields=ExtractedPdfFields(
            form_type=primary_form,
            form_description=form_desc,
            document_domain=document_domain,
            recommended_calculator=recommended_calculator,
            applicant_name=applicant_name,
            pesel_masked=pesel_masked,
            insurance_title=suggested_title,
            zus_title_code=zus_title_code,
            sickness_insurance_status=sickness_status,
            insurance_periods=periods,
            amount_is_net_base=amount_is_net_base,
            extracted_amounts=parsed_amounts[:12],
            fte_fraction=fte_fraction,
            employer_insured_count=emp_count,
            has_contribution_debt=has_debt,
            contribution_debt_pln=debt_pln,
            ezla_number=ezla_num,
            incapacity_period=incapacity_period,
            incapacity_days=incapacity_days,
            letter_codes=letter_codes,
            has_code_b=has_code_b,
            pregnancy_confirmed=pregnancy_confirmed,
            employment_terminated_special=employment_terminated_special,
            termination_reason=termination_reason,
            waiting_period_exemption_reason=waiting_exemption,
            scenario=scenario,
            children_count=children_count,
            child_birth_date=child_birth_date,
            payment_variant=payment_variant,
            has_za_zyciem=has_za_zyciem,
            stillbirth_or_early_death=stillbirth,
            premature_or_hospitalized=premature,
            gestation_week=gestation_week,
            birth_weight_grams=birth_weight,
            combine_parental_with_work=combine_work,
            father_takes_paternity_leave=father_paternity,
            mother_uninsured_father_claim=mother_uninsured,
            page_count=page_count,
            ocr_pages_processed=ocr_pages_processed,
            filled_form_fields_count=len(form_fields),
            key_extracted_fields=key_fields,
            ocr_required=ocr_required,
            ocr_used=ocr_used,
        ),
        missing_fields_for_calculation=missing_fields,
        guidance_banner=guidance_banner,
        notes=notes,
    )


def analyze_case_documents(files: list[tuple[str, bytes]]) -> CaseDocumentsAnalysisResult:
    """Analizuje zestaw 1..N dokumentów jednej sprawy, scala pola według wiarygodności źródła i wykrywa sprzeczności."""
    docs = [analyze_pdf_bytes(fn, data) for fn, data in files]
    if len(docs) == 1:
        return CaseDocumentsAnalysisResult(documents=docs, merged=docs[0], conflicts=[])

    conflicts: list[DocumentConflict] = []

    def _pick_first_and_check_conflict(
        field_key: str,
        field_label: str,
        extractor,
        priority_forms: tuple[str, ...] = (),
    ):
        found: list[tuple[str, object, int]] = []
        for d in docs:
            val = extractor(d)
            if val is not None and val != "" and val != "unknown":
                prio = 0 if d.extracted_fields.form_type in priority_forms else 1
                found.append((d.filename, val, prio))
        if not found:
            return None
        found.sort(key=lambda x: x[2])
        distinct = list(dict.fromkeys(str(v) for _, v, _ in found))
        if len(distinct) > 1:
            conflicts.append(
                DocumentConflict(
                    field=field_key,
                    field_label=field_label,
                    values=distinct,
                    documents=[fn for fn, _, _ in found],
                    message=f"Rozbieżne wartości pola „{field_label}” między dokumentami: {', '.join(distinct)}.",
                )
            )
        return found[0][1]

    merged_forms = list(dict.fromkeys(f for d in docs for f in d.detected_forms))
    merged_title = _pick_first_and_check_conflict(
        "insurance_title",
        "Tytuł ubezpieczenia",
        lambda d: d.suggested_insurance_title,
        priority_forms=("POŚWIADCZENIE UBEZPIECZENIA", "Z-3", "Z-3A", "Z-3B"),
    )
    merged_children = _pick_first_and_check_conflict(
        "children_count",
        "Liczba dzieci",
        lambda d: d.extracted_fields.children_count,
        priority_forms=("ZAM", "AKT URODZENIA USC", "ZUR"),
    )
    merged_scenario = _pick_first_and_check_conflict(
        "scenario",
        "Scenariusz",
        lambda d: d.extracted_fields.scenario,
        priority_forms=("ZAM", "WNIOSEK URLOPOWY KP", "ZUR", "ZAO"),
    )
    merged_variant = _pick_first_and_check_conflict(
        "payment_variant",
        "Wariant wypłaty",
        lambda d: d.extracted_fields.payment_variant,
        priority_forms=("ZAM", "WNIOSEK URLOPOWY KP"),
    )
    merged_has_code_b = _pick_first_and_check_conflict(
        "has_code_b",
        "Kod literowy B (ciąża)",
        lambda d: d.extracted_fields.has_code_b,
        priority_forms=("E-ZLA", "Z-3"),
    )

    # Zarobki: preferuj Z-3 / Z-3A / Z-3B / Poświadczenie
    income_docs = sorted(
        [d for d in docs if d.suggested_gross_salary is not None or d.suggested_custom_benefit_base is not None],
        key=lambda d: 0 if d.extracted_fields.form_type in ("Z-3", "Z-3A", "Z-3B", "POŚWIADCZENIE UBEZPIECZENIA") else 1,
    )
    merged_gross = income_docs[0].suggested_gross_salary if income_docs else None
    merged_base = income_docs[0].suggested_custom_benefit_base if income_docs else None
    merged_amounts = income_docs[0].extracted_fields.extracted_amounts if income_docs else []
    merged_is_net = income_docs[0].extracted_fields.amount_is_net_base if income_docs else False

    # Status ubezpieczenia: odmowa wygrywa nad brakiem danych; sprzeczność między verified a denied jest raportowana
    statuses = [(d.filename, d.sickness_insurance_status) for d in docs if d.sickness_insurance_status != "unknown"]
    if any(s == "denied" for _, s in statuses) and any(s == "confirmed" for _, s in statuses):
        conflicts.append(
            DocumentConflict(
                field="sickness_insurance_status",
                field_label="Status ubezpieczenia chorobowego",
                values=["confirmed", "denied"],
                documents=[fn for fn, _ in statuses],
                message="Jeden dokument potwierdza ubezpieczenie, a inny zawiera odmowę — zweryfikuj ręcznie.",
            )
        )
    if any(s == "denied" for _, s in statuses):
        merged_sickness_status: SicknessInsuranceStatus = "denied"
        merged_ver = "denied"
        merged_verified = False
    elif any(s == "confirmed" for _, s in statuses):
        merged_sickness_status = "confirmed"
        merged_ver = "verified"
        merged_verified = True
    else:
        merged_sickness_status = "unknown"
        merged_ver = "needs_review"
        merged_verified = False

    # Wybór domeny zestawu
    domains = [d.document_domain for d in docs]
    if "maternity_parental" in domains:
        merged_domain: DocumentDomain = "maternity_parental"
        merged_calc: RecommendedCalculator = "maternity_parental"
    elif "sickness_pregnancy" in domains:
        merged_domain = "sickness_pregnancy"
        merged_calc = "pregnancy_sickness"
    elif "sickness_general" in domains:
        merged_domain = "sickness_general"
        merged_calc = "pregnancy_sickness"
    elif "payer_or_insurance_certificate" in domains:
        merged_domain = "payer_or_insurance_certificate"
        merged_calc = "both"
    elif "care_benefit" in domains:
        merged_domain = "care_benefit"
        merged_calc = "info_only"
    elif "other_benefit" in domains:
        merged_domain = "other_benefit"
        merged_calc = "info_only"
    else:
        merged_domain = "unknown"
        merged_calc = "both"

    merged_emp_count = next((d.extracted_fields.employer_insured_count for d in docs if d.extracted_fields.employer_insured_count is not None), None)
    merged_key_fields: dict[str, str] = {}
    for d in docs:
        for k, v in d.extracted_fields.key_extracted_fields.items():
            if k not in merged_key_fields and len(merged_key_fields) < 14:
                merged_key_fields[k] = v

    merged_missing: list[str] = []
    if merged_calc in ("pregnancy_sickness", "maternity_parental", "both"):
        if merged_title is None:
            merged_missing.append("Tytuł ubezpieczenia")
        if merged_gross is None and merged_base is None and merged_title != "none":
            merged_missing.append("Wynagrodzenie / podstawa wymiaru (zł)")
        if merged_sickness_status == "unknown":
            merged_missing.append("Status ubezpieczenia chorobowego")
        if merged_calc == "maternity_parental":
            if merged_scenario is None:
                merged_missing.append("Scenariusz (poród / adopcja / rodzina zastępcza)")
            if merged_children is None:
                merged_missing.append("Liczba dzieci")
            if merged_variant is None:
                merged_missing.append("Wariant wypłaty (81,5% lub 100%/70%)")
        if merged_title in ("uop", "zlecenie") and merged_emp_count is None:
            merged_missing.append("Liczba ubezpieczonych u płatnika")

    merged = PdfAnalysisResult(
        filename=f"Zestaw sprawy ({len(docs)} dokumenty)",
        file_kind="pdf",
        detected_forms=merged_forms,
        document_domain=merged_domain,
        recommended_calculator=merged_calc,
        extracted_text_preview="\n\n".join(f"=== {d.filename} ===\n{d.extracted_text_preview[:260]}" for d in docs[:3]),
        verification_status=merged_ver,
        sickness_insurance_status=merged_sickness_status,
        confidence="high" if merged_ver in ("verified", "denied") else ("medium" if merged_forms else "low"),
        insurance_verified=merged_verified,
        suggested_insurance_title=merged_title,
        suggested_gross_salary=merged_gross,
        suggested_custom_benefit_base=merged_base,
        extracted_fields=ExtractedPdfFields(
            form_type=merged_forms[0] if merged_forms else "UNKNOWN",
            form_description=", ".join(merged_forms) if merged_forms else None,
            document_domain=merged_domain,
            recommended_calculator=merged_calc,
            applicant_name=next((d.extracted_fields.applicant_name for d in docs if d.extracted_fields.applicant_name), None),
            pesel_masked=next((d.extracted_fields.pesel_masked for d in docs if d.extracted_fields.pesel_masked), None),
            insurance_title=merged_title,
            zus_title_code=next((d.extracted_fields.zus_title_code for d in docs if d.extracted_fields.zus_title_code), None),
            sickness_insurance_status=merged_sickness_status,
            insurance_periods=list(dict.fromkeys(p for d in docs for p in d.extracted_fields.insurance_periods))[:12],
            amount_is_net_base=merged_is_net,
            extracted_amounts=merged_amounts,
            fte_fraction=next((d.extracted_fields.fte_fraction for d in docs if d.extracted_fields.fte_fraction is not None), None),
            employer_insured_count=merged_emp_count,
            has_contribution_debt=next((d.extracted_fields.has_contribution_debt for d in docs if d.extracted_fields.has_contribution_debt is not None), None),
            contribution_debt_pln=next((d.extracted_fields.contribution_debt_pln for d in docs if d.extracted_fields.contribution_debt_pln is not None), None),
            ezla_number=next((d.extracted_fields.ezla_number for d in docs if d.extracted_fields.ezla_number), None),
            incapacity_period=next((d.extracted_fields.incapacity_period for d in docs if d.extracted_fields.incapacity_period), None),
            incapacity_days=next((d.extracted_fields.incapacity_days for d in docs if d.extracted_fields.incapacity_days is not None), None),
            letter_codes=list(dict.fromkeys(c for d in docs for c in d.extracted_fields.letter_codes)),
            has_code_b=merged_has_code_b,
            pregnancy_confirmed=next((d.extracted_fields.pregnancy_confirmed for d in docs if d.extracted_fields.pregnancy_confirmed is not None), None),
            employment_terminated_special=next((d.extracted_fields.employment_terminated_special for d in docs if d.extracted_fields.employment_terminated_special is not None), None),
            termination_reason=next((d.extracted_fields.termination_reason for d in docs if d.extracted_fields.termination_reason), None),
            waiting_period_exemption_reason=next((d.extracted_fields.waiting_period_exemption_reason for d in docs if d.extracted_fields.waiting_period_exemption_reason), None),
            scenario=merged_scenario,
            children_count=merged_children,
            child_birth_date=next((d.extracted_fields.child_birth_date for d in docs if d.extracted_fields.child_birth_date), None),
            payment_variant=merged_variant,
            has_za_zyciem=next((d.extracted_fields.has_za_zyciem for d in docs if d.extracted_fields.has_za_zyciem), None),
            stillbirth_or_early_death=next((d.extracted_fields.stillbirth_or_early_death for d in docs if d.extracted_fields.stillbirth_or_early_death), None),
            premature_or_hospitalized=next((d.extracted_fields.premature_or_hospitalized for d in docs if d.extracted_fields.premature_or_hospitalized), None),
            gestation_week=next((d.extracted_fields.gestation_week for d in docs if d.extracted_fields.gestation_week is not None), None),
            birth_weight_grams=next((d.extracted_fields.birth_weight_grams for d in docs if d.extracted_fields.birth_weight_grams is not None), None),
            combine_parental_with_work=next((d.extracted_fields.combine_parental_with_work for d in docs if d.extracted_fields.combine_parental_with_work), None),
            father_takes_paternity_leave=next((d.extracted_fields.father_takes_paternity_leave for d in docs if d.extracted_fields.father_takes_paternity_leave), None),
            mother_uninsured_father_claim=next((d.extracted_fields.mother_uninsured_father_claim for d in docs if d.extracted_fields.mother_uninsured_father_claim), None),
            page_count=sum(d.extracted_fields.page_count for d in docs),
            ocr_pages_processed=sum(d.extracted_fields.ocr_pages_processed for d in docs),
            filled_form_fields_count=sum(d.extracted_fields.filled_form_fields_count for d in docs),
            key_extracted_fields=merged_key_fields,
            ocr_required=all(d.extracted_fields.ocr_required for d in docs),
            ocr_used=any(d.extracted_fields.ocr_used for d in docs),
        ),
        missing_fields_for_calculation=merged_missing,
        guidance_banner=next((d.guidance_banner for d in docs if d.guidance_banner), None),
        notes=list(dict.fromkeys(n for d in docs for n in d.notes))[:10],
    )

    return CaseDocumentsAnalysisResult(documents=docs, merged=merged, conflicts=conflicts)
