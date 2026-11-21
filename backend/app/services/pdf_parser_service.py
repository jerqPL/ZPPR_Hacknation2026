import io
import re
from pypdf import PdfReader
from app.models.guidance import PdfAnalysisResult, SampleCase

SAMPLE_CASES: list[SampleCase] = [
    SampleCase(
        case_id="case_01_uop_full",
        title="Sprawa #1 (Zestaw ZUS — UoP + Z-3): Pracownica (>20 ubezp.), indywidualna podstawa z premią roczną",
        description=(
            "Zatrudnienie na umowę o pracę od 24 miesięcy: wynagrodzenie zasadnicze 7 500 zł brutto + nagroda roczna "
            "(trzynastka) 6 000 zł brutto (wliczana w 1/12 = 500 zł brutto/mies.). Łączna średnia z Z-3: 8 000 zł brutto."
        ),
        scenario="birth",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — indywidualna podstawa wymiaru 6 903,20 zł (z 8 000 zł brutto po odliczeniu 13,71%), stawka 81,5% wypłacana przez pracodawcę.",
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
        notes="Sprawa z zestawu ZUS prezentująca wyliczenie indywidualnej podstawy wymiaru zasiłku na podstawie formularza Z-3 z uwzględnieniem składnika rocznego (1/12).",
    ),
    SampleCase(
        case_id="case_02_jdg_twins",
        title="Sprawa #2 (Zestaw ZUS — JDG, bliźniaki): Działalność gospodarcza, 2 dzieci, wariant 100%/70%",
        description="Dobrowolne ubezpieczenie chorobowe opłacane terminowo > 12 miesięcy od podstawy 6 000 zł, urodzenie bliźniąt.",
        scenario="birth",
        insurance_title="jdg",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — zasiłek wypłacany przez ZUS: 31 tyg. macierzyńskiego (100%) + 43 tyg. urlopu rodzicielskiego (70%), indywidualna podstawa 5 177,40 zł.",
        gross_monthly_salary=6000.0,
        custom_benefit_base=5177.40,
        benefit_base_details="Art. 48 ust. 1 ustawy zasiłkowej: przeciętna podstawa z 12 mies. 6 000,00 zł × (1 - 13,71%) = 5 177,40 zł",
        children_count=2,
        payment_variant="100_70",
        has_za_zyciem=False,
        employer_insured_count=1,
        mother_maternity_weeks=31,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Zasiłek wypłaca ZUS na podstawie wniosku ZAM oraz poświadczenia ubezpieczenia chorobowego.",
    ),
    SampleCase(
        case_id="case_03_zlecenie_no_insurance",
        title="Sprawa #3 (Zestaw ZUS — Zlecenie, odmowa): Umowa zlecenie bez dobrowolnego ubezpieczenia chorobowego",
        description="Zleceniobiorca zgłoszony wyłącznie do ubezpieczeń emerytalnego, rentowego i zdrowotnego (brak chorobowego na dzień porodu w Z-3a).",
        scenario="birth",
        insurance_title="zlecenie",
        insured_on_event_date=False,
        expected_decision="ODMOWA — brak podlegania dobrowolnemu ubezpieczeniu chorobowemu w dniu porodu.",
        gross_monthly_salary=5400.0,
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=12,
        notes="Typowy przypadek sporny z zestawów ZUS: poświadczenie ubezpieczenia wykazuje brak zgłoszenia do dobrowolnego ubezpieczenia chorobowego.",
    ),
    SampleCase(
        case_id="case_04_za_zyciem",
        title="Sprawa #4 (Zestaw ZUS — Art. 43 + Za życiem): Mała firma (≤20 os.), zachowana podstawa po e-ZLA",
        description=(
            "Umowa o pracę w firmie 10-osobowej (płatnik ZUS, formularz Z-3/ZAS-12), bezpośrednie przejście z zasiłku "
            "chorobowego w ciąży na macierzyński (brak przerwy -> zachowana podstawa 5 608,85 zł wg art. 43), zaświadczenie 'Za życiem'."
        ),
        scenario="birth",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — wydłużony urlop rodzicielski 65 tygodni (w tym 9 tyg. dla ojca), indywidualna podstawa z art. 43: 5 608,85 zł, wypłaca ZUS.",
        gross_monthly_salary=6200.0,
        custom_benefit_base=5608.85,
        benefit_base_details="Art. 43 ustawy zasiłkowej: zachowana podstawa wymiaru z poprzedniego zasiłku chorobowego w ciąży (przerwa < 1 miesiąc kalendarzowy) = 5 608,85 zł",
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=True,
        employer_insured_count=10,
        mother_maternity_weeks=20,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Wymaga dołączenia zaświadczenia lekarskiego wydanego na podstawie art. 4 ust. 3 ustawy 'Za życiem'.",
    ),
    SampleCase(
        case_id="case_05_adoption_both_parents",
        title="Sprawa #5 (Zestaw ZUS — Adopcja, pkt e/j/f): Przysposobienie dziecka (5 lat), podział między rodziców",
        description=(
            "Przyjęcie na wychowanie dziecka w wieku 5 lat i wystąpienie do sądu opiekuńczego o przysposobienie. "
            "Indywidualna podstawa wymiaru Rodzica 1 z Z-3: 7 248,36 zł (z uwzględnieniem premii kwartalnych), Rodzica 2: 6 385,46 zł."
        ),
        scenario="adoption",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — 20 tyg. urlopu na warunkach macierzyńskiego (podział 14 + 6 tyg.) + 41 tyg. rodzicielskiego (32 + 9 tyg.) + 2 tyg. ojcowskiego.",
        gross_monthly_salary=8000.0,
        custom_benefit_base=7248.36,
        benefit_base_details="Art. 36 i art. 42 ust. 2 ustawy zasiłkowej: średnia z 12 mies. + 1/12 premii z 4 kwartałów po odliczeniu 13,71% = 7 248,36 zł",
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
        notes="Sprawa demonstruje uprawnienia rodziców adopcyjnych (limit wieku dziecka do 14 lat, art. 183 § 1¹ i § 4¹ KP) wraz z indywidualną podstawą wymiaru.",
    ),
    SampleCase(
        case_id="case_06_foster_non_prof_9_weeks",
        title="Sprawa #6 (Zestaw ZUS — Rodzina zastępcza niezawodowa, pkt e/j): Dziecko 6,9 r.ż. (reguła min. 9 tyg.)",
        description=(
            "Przyjęcie dziecka w wieku 6 lat i 11 miesięcy (6,9 r.ż.) do rodziny zastępczej niezawodowej. "
            "Do ukończenia 7 r.ż. pozostało mniej niż 9 tygodni — zastosowanie gwarancji 9 tyg. urlopu na warunkach macierzyńskiego i 38 tyg. rodzicielskiego (art. 183 § 3 i § 4 pkt 3 KP)."
        ),
        scenario="foster",
        insurance_title="uop",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — 9 tyg. urlopu na warunkach urlopu macierzyńskiego + 38 tyg. urlopu rodzicielskiego (art. 183 § 3 i § 4 pkt 3 KP), indywidualna podstawa 5 867,72 zł.",
        gross_monthly_salary=6800.0,
        custom_benefit_base=5867.72,
        benefit_base_details="Art. 36 ustawy zasiłkowej: przeciętne wynagrodzenie z 12 miesięcy z formularza Z-3 (6 800,00 zł - 13,71%) = 5 867,72 zł",
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
        notes="Sprawa weryfikująca minimalny 9-tygodniowy wymiar urlopu na warunkach macierzyńskiego oraz 38-tygodniowy urlop rodzicielski dla rodziny zastępczej niezawodowej.",
    ),
    SampleCase(
        case_id="case_07_jdg_art48a_individual_base",
        title="Sprawa #7 (Zestaw ZUS — JDG Art. 48a, pkt f): Krótki okres wysokiej składki na JDG (3 miesiące)",
        description=(
            "Ubezpieczona na JDG podlegała dobrowolnemu ubezpieczeniu chorobowemu przez 3 pełne miesiące przed porodem "
            "z maksymalną deklarowaną podstawą 23 550,00 zł brutto (najniższa podstawa standardowa: 5 652,00 zł brutto)."
        ),
        scenario="birth",
        insurance_title="jdg",
        insured_on_event_date=True,
        expected_decision="PRZYZNANO — indywidualna podstawa wymiaru wyliczona wg art. 48a ust. 1 ustawy zasiłkowej: 8 738,16 zł (zamiast pełnych 20 321,30 zł).",
        gross_monthly_salary=23550.0,
        custom_benefit_base=8738.16,
        benefit_base_details="Art. 48a ust. 1 ustawy zasiłkowej: najniższa podstawa 4 877,11 zł + 3/12 nadwyżki (20 321,30 - 4 877,11) = 8 738,16 zł",
        children_count=1,
        payment_variant="81_5",
        has_za_zyciem=False,
        employer_insured_count=1,
        mother_maternity_weeks=20,
        father_takes_parental_weeks=9,
        father_takes_paternity_leave=False,
        notes="Kluczowa sprawa z zestawów ZUS ilustrująca mechanizm proporcjonalnego ustalania podstawy wymiaru zasiłku na JDG przy ubezpieczeniu krótszym niż 12 miesięcy (art. 48a).",
    ),
]


def list_sample_cases() -> list[SampleCase]:
    return SAMPLE_CASES


def analyze_pdf_bytes(filename: str, content: bytes) -> PdfAnalysisResult:
    """Parser PDF wyciągający tekst, rozpoznający formularze ZUS (ZAM, Z-3, Z-3a, ZAS-53, e-ZLA) oraz indywidualną podstawę wymiaru."""
    text = ""
    notes: list[str] = []
    try:
        reader = PdfReader(io.BytesIO(content))
        pages_text = []
        for page in reader.pages[:8]:
            pages_text.append(page.extract_text() or "")
        text = "\n".join(pages_text).strip()
    except Exception as exc:
        notes.append(f"Nie udało się odczytać warstwy tekstowej PDF (możliwy skan/obraz — wymaga OCR/AI): {exc}")

    upper = text.upper()
    detected: list[str] = []
    for code in ["ZAM", "Z-3A", "Z-3", "ZAS-53", "ZAS-12", "E-ZLA", "POŚWIADCZENIE UBEZPIECZENIA", "ZUR", "ZAO"]:
        if code in upper:
            detected.append(code)

    if not detected:
        notes.append("Nie rozpoznano jednoznacznie kodu formularza ZUS w warstwie tekstowej.")

    # Heurystyka tytułu ubezpieczenia
    suggested_title = "uop"
    if "Z-3A" in detected or "ZLECENI" in upper:
        suggested_title = "zlecenie"
    elif "DZIAŁALNOŚC" in upper or "ZAS-53" in detected or "POZAROLNICZ" in upper:
        suggested_title = "jdg"

    # Heurystyka weryfikacji ubezpieczenia
    insurance_verified = "NIE PODLEGA" not in upper and ("UBEZPIECZENI" in upper or len(detected) > 0)

    # Próba wykrycia kwot wynagrodzenia / podstawy wymiaru z tabeli Z-3 / Z-3a / poświadczenia
    matches = re.findall(r"(\d[\d\s]{2,6}[,\.]\d{2})\s*(?:PLN|ZŁ)?", upper)
    parsed_amounts: list[float] = []
    for raw_m in matches:
        cleaned = raw_m.replace(" ", "").replace("\xa0", "").replace(",", ".")
        try:
            val = float(cleaned)
            if 1000.0 <= val <= 50000.0:
                parsed_amounts.append(val)
        except ValueError:
            continue

    suggested_salary = None
    suggested_custom_base = None
    if parsed_amounts:
        avg_amount = round(sum(parsed_amounts[:12]) / min(len(parsed_amounts), 12), 2)
        suggested_salary = avg_amount
        suggested_custom_base = round(avg_amount * (1.0 - 0.1371), 2)
        notes.append(
            f"Wykryto {len(parsed_amounts)} pozycji kwotowych w dokumencie — wyliczono średnią podstawę po odliczeniu 13,71%: {suggested_custom_base:.2f} zł."
        )

    preview = text[:600] if text else "(Brak warstwy tekstowej — dokument może wymagać modułu OCR/AI)"

    return PdfAnalysisResult(
        filename=filename,
        detected_forms=detected,
        extracted_text_preview=preview,
        insurance_verified=insurance_verified,
        suggested_insurance_title=suggested_title,
        suggested_gross_salary=suggested_salary,
        suggested_custom_benefit_base=suggested_custom_base,
        notes=notes,
    )
