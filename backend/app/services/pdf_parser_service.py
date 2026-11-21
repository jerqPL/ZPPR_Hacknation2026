import io
import re
from pypdf import PdfReader
from app.models.guidance import ExtractedPdfFields, PdfAnalysisResult, SampleCase
from app.services.parameter_store import parameter_store

# Uczciwie oznaczone jako przykłady demonstracyjne (weryfikowane testami automatycznymi z silnikiem)
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


_FORM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Z-3A", re.compile(r"\bZ-3A\b", re.IGNORECASE)),
    ("Z-3", re.compile(r"\bZ-3\b", re.IGNORECASE)),
    ("ZAM", re.compile(r"\bZAM\b")),  # wielkie litery, aby nie trafiać w zwykłe słowa
    ("ZAS-53", re.compile(r"\bZAS-53\b", re.IGNORECASE)),
    ("ZAS-12", re.compile(r"\bZAS-12\b", re.IGNORECASE)),
    ("E-ZLA", re.compile(r"\bE-ZLA\b", re.IGNORECASE)),
    ("ZUR", re.compile(r"\bZUR\b")),
    ("ZAO", re.compile(r"\bZAO\b")),
    ("POŚWIADCZENIE UBEZPIECZENIA", re.compile(r"POŚWIADCZENI[EU]\s+UBEZPIECZENI", re.IGNORECASE)),
]


def _extract_amounts_with_context(text: str) -> tuple[list[float], bool]:
    """Wyciąga kwoty wynagrodzenia/podstawy z wykrywaniem czy kwota jest już po odliczeniu składek (netto podstawy)."""
    upper = text.upper()
    is_net_base = bool(
        re.search(r"PODSTAWA\s+WYMIARU\s+ZASIŁKU|PO\s+ODLICZENIU\s+13[,\.]71|PODSTAWA\s+NETTO", upper)
    )
    # Szukamy kwot z oznaczeniem waluty lub w wierszach z miesiącami (YYYY-MM / MM.YYYY)
    matches = re.findall(r"(?<!\d)(\d{1,2}[\s\xa0]?\d{3}[,\.]\d{2})(?!\d)", text)
    amounts: list[float] = []
    for raw in matches:
        cleaned = raw.replace(" ", "").replace("\xa0", "").replace(",", ".")
        try:
            val = float(cleaned)
            if 500.0 <= val <= 50000.0:
                amounts.append(val)
        except ValueError:
            continue
    return amounts, is_net_base


def analyze_pdf_bytes(filename: str, content: bytes) -> PdfAnalysisResult:
    """Strukturalny parser PDF per formularz (Z-3, Z-3a, ZAM, Poświadczenie ubezpieczenia) z ostrożną weryfikacją."""
    text = ""
    notes: list[str] = []
    ocr_required = False

    try:
        reader = PdfReader(io.BytesIO(content))
        pages_text = [(page.extract_text() or "") for page in reader.pages[:8]]
        text = "\n".join(pages_text).strip()
    except Exception as exc:
        ocr_required = True
        notes.append(f"Nie udało się odczytać warstwy tekstowej pliku PDF (możliwy skan): {exc}")

    if len(text) < 20:
        ocr_required = True
        notes.append(
            "Dokument nie zawiera warstwy tekstowej (prawdopodobnie skan obrazu). Wymaga ręcznego potwierdzenia lub modułu OCR."
        )

    upper = text.upper()
    detected = [code for code, pattern in _FORM_PATTERNS if pattern.search(text)]
    primary_form = detected[0] if detected else "UNKNOWN"

    # Tytuł ubezpieczenia
    suggested_title = "uop"
    if "Z-3A" in detected or re.search(r"\bZLECENI[AE]|UMOW[AY]\s+ZLECEN", upper):
        suggested_title = "zlecenie"
    elif "ZAS-53" in detected or re.search(r"DZIAŁALNOŚC[IĄ]\s+GOSPODARCZ|POZAROLNICZ", upper):
        suggested_title = "jdg"

    # Okresy ubezpieczenia / daty
    periods = re.findall(r"\b\d{2}[.\-/]\d{2}[.\-/]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b", text)[:8]

    # Liczba ubezpieczonych u płatnika (jeśli występuje w Z-3/Z-3a)
    emp_count: int | None = None
    emp_match = re.search(r"LICZB[AĘ]\s+UBEZPIECZONYCH[^\d]{0,30}(\d{1,5})", upper)
    if emp_match:
        emp_count = int(emp_match.group(1))

    # Ostrożna weryfikacja statusu ubezpieczenia — nigdy nie zwracamy "verified" w ciemno!
    has_explicit_denial = bool(
        re.search(r"NIE\s+PODLEGA|BRAK\s+UBEZPIECZENIA\s+CHOROBOWEGO|ODMOWA\s+PRAWA|WYŁĄCZON[YA]\s+Z\s+UBEZPIECZENIA", upper)
    )
    has_explicit_confirmation = bool(
        re.search(
            r"PODLEGA\s+(?:OBOWIĄZKOWEMU\s+|DOBROWOLNEMU\s+)?UBEZPIECZENIU\s+CHOROBOWEMU|UBEZPIECZENIE\s+CHOROBOWE\s*:\s*TAK",
            upper,
        )
    )

    if ocr_required or not detected:
        verification_status = "needs_review"
        confidence = "low"
        insurance_verified = False
        notes.append("Status wymaga weryfikacji przez użytkownika przed uruchomieniem symulacji.")
    elif has_explicit_denial:
        verification_status = "denied"
        confidence = "high"
        insurance_verified = False
        notes.append("W treści dokumentu wykryto adnotację o braku podlegania ubezpieczeniu chorobowemu lub odmowie.")
    elif has_explicit_confirmation:
        verification_status = "verified"
        confidence = "high"
        insurance_verified = True
        notes.append("W treści dokumentu potwierdzono podleganie ubezpieczeniu chorobowemu.")
    else:
        verification_status = "needs_review"
        confidence = "medium"
        insurance_verified = False
        notes.append(
            f"Rozpoznano formularz {', '.join(detected)}, ale brak jednoznacznego potwierdzenia statusu ubezpieczenia chorobowego — potwierdź pola ręcznie."
        )

    # Kwoty — używamy stopy z ParameterStore (bez zahardkodowanego 0.1371) i nie odliczamy drugi raz przy podstawie netto
    params = parameter_store.get()
    rate = params.employee_social_security_rate
    parsed_amounts, amount_is_net_base = _extract_amounts_with_context(text)

    suggested_salary: float | None = None
    suggested_custom_base: float | None = None
    if parsed_amounts:
        avg_amount = round(sum(parsed_amounts[:12]) / min(len(parsed_amounts), 12), 2)
        if amount_is_net_base:
            suggested_custom_base = avg_amount
            suggested_salary = round(avg_amount / (1.0 - rate), 2)
            notes.append(
                f"Wykryto podstawę wymiaru zasiłku (już po odliczeniu składek): {suggested_custom_base:.2f} zł — nie odliczono ponownie {rate*100:.2f}%."
            )
        else:
            suggested_salary = avg_amount
            suggested_custom_base = round(avg_amount * (1.0 - rate), 2)
            notes.append(
                f"Wykryto {len(parsed_amounts)} kwot brutto (śr. {avg_amount:.2f} zł) -> szacowana podstawa po -{rate*100:.2f}%: {suggested_custom_base:.2f} zł. Potwierdź kwotę przed obliczeniem."
            )

    preview = text[:600] if text else "(Brak warstwy tekstowej — dokument wymaga weryfikacji ręcznej lub OCR)"

    return PdfAnalysisResult(
        filename=filename,
        detected_forms=detected,
        extracted_text_preview=preview,
        verification_status=verification_status,
        confidence=confidence,
        insurance_verified=insurance_verified,
        suggested_insurance_title=suggested_title,
        suggested_gross_salary=suggested_salary,
        suggested_custom_benefit_base=suggested_custom_base,
        extracted_fields=ExtractedPdfFields(
            form_type=primary_form,
            insurance_title=suggested_title,
            insurance_periods=periods,
            amount_is_net_base=amount_is_net_base,
            extracted_amounts=parsed_amounts[:12],
            employer_insured_count=emp_count,
            children_count=1,
            ocr_required=ocr_required,
        ),
        notes=notes,
    )
