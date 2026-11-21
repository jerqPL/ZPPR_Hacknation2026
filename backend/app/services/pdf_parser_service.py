import io
import re
from pypdf import PdfReader
from app.models.guidance import PdfAnalysisResult, SampleCase

SAMPLE_CASES: list[SampleCase] = [
    SampleCase(
        case_id="case_01_uop_full",
        title="Sprawa #1: Pracownica (UoP, >20 ubezpieczonych), 1 dziecko, wniosek w 21 dni",
        description="Ciągłe zatrudnienie na umowę o pracę od 24 miesięcy, wynagrodzenie 7 500 zł brutto, złożony wniosek ZAM/urlop w ciągu 21 dni.",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — zasiłek macierzyński 81,5% przez pracodawcę (20 + 32 tyg.) oraz 9 tyg. (70%) dla ojca.",
        gross_monthly_salary=7500.0,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=120,
        notes="Przykładowy zestaw testowy gotowy do porównania z zanonimizowanymi sprawami ZUS.",
    ),
    SampleCase(
        case_id="case_02_jdg_twins",
        title="Sprawa #2: Działalność gospodarcza (JDG), bliźniaki, wariant 100%/70%",
        description="Dobrowolne ubezpieczenie chorobowe opłacane terminowo > 90 dni, urodzenie dwojga dzieci przy jednym porodzie.",
        insurance_title="jdg",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — zasiłek wypłacany przez ZUS: 31 tyg. (100%) + 43 tyg. urlopu rodzicielskiego (70%).",
        gross_monthly_salary=6000.0,
        children_count=2,
        payment_variant="100_70",
        has_za_zyciem=False,
        employer_insured_count=1,
        notes="Zasiłek wypłaca ZUS na podstawie wniosku ZAM.",
    ),
    SampleCase(
        case_id="case_03_zlecenie_no_insurance",
        title="Sprawa #3: Umowa zlecenie bez dobrowolnego ubezpieczenia chorobowego",
        description="Zleceniobiorca zgłoszony wyłącznie do ubezpieczeń emerytalnego, rentowego i zdrowotnego (brak chorobowego na dzień porodu).",
        insurance_title="zlecenie",
        insured_on_event_date=False,
        expected_decision="ODMOWA — brak podlegania ubezpieczeniu chorobowemu w dniu porodu.",
        gross_monthly_salary=5400.0,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=12,
        notes="Typowy przypadek sporny: konieczność wczesnej informacji o dobrowolnym ubezpieczeniu chorobowym.",
    ),
    SampleCase(
        case_id="case_04_za_zyciem",
        title="Sprawa #4: Pracownica (mała firma ≤20 os.), zaświadczenie 'Za życiem'",
        description="Umowa o pracę w firmie 10-osobowej (płatnik ZUS, formularz Z-3), 1 dziecko z zaświadczeniem 'Za życiem'.",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — wydłużony urlop rodzicielski 65 tygodni (w tym 9 tyg. nieprzenoszalne), wypłaca ZUS.",
        gross_monthly_salary=6200.0,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=True,
        employer_insured_count=10,
        notes="Wymaga dołączenia zaświadczenia lekarskiego wydanego na podstawie ustawy 'Za życiem'.",
    ),
]


def list_sample_cases() -> list[SampleCase]:
    return SAMPLE_CASES


def analyze_pdf_bytes(filename: str, content: bytes) -> PdfAnalysisResult:
    """Podstawowy parser PDF wyciągający tekst i rozpoznający formularze ZUS (ZAM, Z-3, Z-3a, ZAS-53, e-ZLA)."""
    text = ""
    notes: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(content))
        pages_text = []
        for page in reader.pages[:5]:
            pages_text.append(page.extract_text() or "")
        text = "\n".join(pages_text).strip()
    except Exception as exc:
        notes.append(f"Nie udało się odczytać warstwy tekstowej PDF (możliwy skan/obraz — wymaga OCR/AI): {exc}")

    upper = text.upper()
    detected: list[str] = []
    for code in ["ZAM", "Z-3A", "Z-3", "ZAS-53", "ZAS-12", "E-ZLA", "POŚWIADCZENIE UBEZPIECZENIA"]:
        if code in upper:
            detected.append(code)

    if not detected:
        notes.append("Nie rozpoznano jednoznacznie kodu formularza ZUS w warstwie tekstowej.")

    # Heurystyka tytułu ubezpieczenia
    suggested_title = "uop"
    if "Z-3A" in detected or "ZLECENI" in upper:
        suggested_title = "zlecenie"
    elif "DZIAŁALNOŚC" in upper or "ZAS-53" in detected:
        suggested_title = "jdg"

    # Heurystyka weryfikacji ubezpieczenia
    insurance_verified = "NIE PODLEGA" not in upper and ("UBEZPIECZENI" in upper or len(detected) > 0)

    # Prosta próba wykrycia kwoty wynagrodzenia
    suggested_salary = None
    match = re.search(r"(\d[\d\s]{2,6}[,\.]\d{2})\s*(?:PLN|ZŁ)", upper)
    if match:
        raw = match.group(1).replace(" ", "").replace(",", ".")
        try:
            suggested_salary = float(raw)
        except ValueError:
            suggested_salary = None

    preview = text[:600] if text else "(Brak warstwy tekstowej — dokument może wymagać modułu OCR/AI)"

    return PdfAnalysisResult(
        filename=filename,
        detected_forms=detected,
        extracted_text_preview=preview,
        insurance_verified=insurance_verified,
        suggested_insurance_title=suggested_title,
        suggested_gross_salary=suggested_salary,
        notes=notes,
    )
