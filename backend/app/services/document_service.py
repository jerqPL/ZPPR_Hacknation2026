from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
import uuid
from app.models.calculator import InsuranceTitle, PaymentVariant
from app.models.guidance import DocumentGuidanceResponse, DocumentRequirement
from app.models.parameters import LegalParameters
from app.models.simulation import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResponse,
    ApplicationType,
)

_POLISH_ASCII_MAP = str.maketrans(
    {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ź": "Z", "Ż": "Z",
        "¹": "1", "²": "2", "³": "3", "ᵃ": "a", "ᵈ": "d", "ᵉ": "e", "ᶠ": "f",
        "§": "par.", "—": "-", "–": "-", "„": '"', "”": '"', "’": "'", "…": "...",
    }
)


def _sanitize_for_unicode_font(text: str) -> str:
    """Usuwa znaki spoza BMP (np. emoji), których nie zawiera czcionka DejaVuSans."""
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF)


def _to_latin1_safe(text: str) -> str:
    """Awaryjna konwersja dla czcionki Helvetica, gdy brak plików TTF DejaVuSans."""
    return _sanitize_for_unicode_font(text).translate(_POLISH_ASCII_MAP).encode("latin-1", "replace").decode("latin-1")


def get_document_guidance(
    insurance_title: InsuranceTitle,
    employer_insured_count: int,
    params: LegalParameters,
) -> DocumentGuidanceResponse:
    deadline_days = params.combined_application_deadline_days
    combined_rate_str = f"{params.combined_21_days_rate * 100:.1f}".replace(".", ",")

    if insurance_title == InsuranceTitle.NONE:
        payer = "Brak uprawnień z ubezpieczenia chorobowego (ZUS)"
        payer_explanation = (
            "Osoba niepodlegająca ubezpieczeniu chorobowemu nie nabywa prawa do zasiłku macierzyńskiego ani chorobowego "
            "z ZUS. Przysługuje natomiast świadczenie rodzicielskie (tzw. Kosiniakowe — "
            f"{params.parental_benefit_minimum_monthly:.0f} zł/mies.) z gminy/MOPS, a ubezpieczony drugi rodzic może "
            "skorzystać z urlopu rodzicielskiego i ojcowskiego (art. 31 ust. 3h ustawy zasiłkowej)."
        )
        docs = [
            DocumentRequirement(
                form_code="SR-7 (Kosiniakowe)",
                title=f"Wniosek o ustalenie prawa do świadczenia rodzicielskiego ({params.parental_benefit_minimum_monthly:.0f} zł/mies.)",
                submitted_by="Matka / opiekun dziecka",
                submitted_to="Urząd Gminy / MOPS / portal Emp@tia",
                deadline="W ciągu 3 miesięcy od dnia porodu (wyrównanie od dnia porodu)",
                notes="Przysługuje przez 52 tygodnie (1 dziecko) do 71 tygodni (5+ dzieci) osobom bez prawa do zasiłku macierzyńskiego (m.in. bezrobotni, studenci, umowa o dzieło).",
            ),
            DocumentRequirement(
                form_code="ZAM / Wniosek o urlop (art. 31 ust. 3h)",
                title="Wniosek ubezpieczonego ojca o urlop/zasiłek rodzicielski (70%) i ojcowski (2 tyg., 100%)",
                submitted_by="Ubezpieczony ojciec dziecka",
                submitted_to="Pracodawca ojca lub ZUS (PUE/eZUS)",
                deadline="Min. 21 dni przed urlopem rodzicielskim / 7 dni przed ojcowskim (lub przed rozpoczęciem na ZAM)",
                notes="Wymagane oświadczenie ojca, że matka dziecka nie posiada tytułu do ubezpieczenia chorobowego (§ 32 ust. 1 pkt 4 rozporządzenia).",
            ),
            DocumentRequirement(
                form_code="Akt urodzenia (USC)",
                title="Odpis skrócony lub zupełny aktu urodzenia dziecka",
                submitted_by="Rodzic",
                submitted_to="Urząd Gminy / pracodawca ojca (przy płatniku ZUS wystarczą dane dziecka — § 13 ust. 2)",
                deadline="Po rejestracji urodzenia w Urzędzie Stanu Cywilnego",
                notes="Od 1 stycznia 2026 r. elektroniczny wniosek o odpis aktu stanu cywilnego na gov.pl realizowany jest przez e-Doręczenia (bezpłatnie w sprawach ZUS/świadczeń).",
            ),
        ]
    else:
        employer_pays = (
            insurance_title in (InsuranceTitle.UOP, InsuranceTitle.ZLECENIE)
            and employer_insured_count > params.payer_employee_threshold
        )

        if employer_pays:
            payer = "Płatnik składek (pracodawca / zleceniodawca)"
            payer_explanation = (
                f"Płatnik zgłasza do ubezpieczenia chorobowego powyżej {params.payer_employee_threshold} osób "
                "(stan na 30 listopada poprzedniego roku), dlatego to on ustala prawo i wypłaca zasiłek."
            )
        else:
            payer = "Zakład Ubezpieczeń Społecznych (ZUS)"
            payer_explanation = (
                f"Dla osób na JDG, po ustaniu zatrudnienia lub u płatników zgłaszających do {params.payer_employee_threshold} osób "
                "prawo do zasiłku ustala i wypłaca go bezpośrednio ZUS."
            )

        docs = []

        if insurance_title == InsuranceTitle.UOP:
            docs.append(
                DocumentRequirement(
                    form_code="Wniosek o urlop (KP)",
                    title=f"Wniosek o udzielenie urlopu macierzyńskiego i rodzicielskiego (lub pisemna deklaracja {combined_rate_str}%)",
                    submitted_by="Pracownik (matka/ojciec)",
                    submitted_to="Pracodawca",
                    deadline=f"Do {deadline_days} dni po porodzie (dla stawki {combined_rate_str}%)",
                    notes=f"Alternatywnie można złożyć sam wniosek/deklarację o wypłatę {combined_rate_str}% za pełny wymiar (art. 30a ustawy zasiłkowej).",
                )
            )
            if not employer_pays:
                docs.append(
                    DocumentRequirement(
                        form_code="Z-3",
                        title="Zaświadczenie płatnika składek (dla pracownika)",
                        submitted_by="Pracodawca",
                        submitted_to="ZUS (PUE/eZUS)",
                        deadline="Niezwłocznie, nie później niż w terminie 7 dni od dnia otrzymania wniosku (art. 61b ust. 5 ustawy zasiłkowej)",
                        notes="Na dalszy okres zasiłku chorobowego pracodawca może złożyć ZAS-12.",
                    )
                )
        elif insurance_title == InsuranceTitle.ZLECENIE:
            docs.append(
                DocumentRequirement(
                    form_code="ZAM",
                    title="Wniosek o zasiłek macierzyński",
                    submitted_by="Ubezpieczony (zleceniobiorca)",
                    submitted_to="Płatnik składek lub ZUS",
                    deadline=f"Do {deadline_days} dni po porodzie (dla stawki {combined_rate_str}%)",
                    notes="Zleceniobiorca nie ma urlopu z Kodeksu pracy, ale ma prawo do zasiłku za okres odpowiadający urlopowi. Po zakończeniu zasiłku wymagane jest ponowne zgłoszenie ZUS ZUA do dobrowolnego chorobowego.",
                )
            )
            if not employer_pays:
                docs.append(
                    DocumentRequirement(
                        form_code="Z-3a",
                        title="Zaświadczenie płatnika składek (dla zleceniobiorcy)",
                        submitted_by="Zleceniodawca",
                        submitted_to="ZUS (PUE/eZUS)",
                        deadline="Niezwłocznie, nie później niż w terminie 7 dni od dnia otrzymania wniosku (art. 61b ust. 5 ustawy zasiłkowej)",
                        notes="Zawiera okresy ubezpieczenia i podstawę wymiaru składek.",
                    )
                )
        else:
            docs.append(
                DocumentRequirement(
                    form_code="ZAM",
                    title="Wniosek o zasiłek macierzyński",
                    submitted_by="Osoba prowadząca JDG / ubezpieczony",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline=f"Do {deadline_days} dni po porodzie (dla stawki {combined_rate_str}%)",
                    notes="Rozpoczęcie zasiłku macierzyńskiego na JDG powoduje automatyczne ustanie dobrowolnego ubezpieczenia chorobowego — po zakończeniu zasiłku wymagane jest ponowne zgłoszenie ZUS ZUA.",
                )
            )
            docs.append(
                DocumentRequirement(
                    form_code="ZAS-53",
                    title="Wniosek o zasiłek chorobowy (okres ciąży)",
                    submitted_by="Osoba prowadząca JDG",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Po wystawieniu e-ZLA przez lekarza",
                    notes="Samo e-ZLA nie uruchamia wypłaty na JDG — potrzebny jest wniosek ZAS-53.",
                )
            )

        if employer_pays:
            docs.append(
                DocumentRequirement(
                    form_code="Akt urodzenia (USC)",
                    title="Odpis skrócony (lub zupełny) aktu urodzenia dziecka",
                    submitted_by="Rodzic",
                    submitted_to="Pracodawca / płatnik składek (załącznik do wniosku)",
                    deadline="Po rejestracji urodzenia w Urzędzie Stanu Cywilnego",
                    notes="Od 1 stycznia 2026 r. elektroniczny odpis z Rejestru Stanu Cywilnego (gov.pl) uzyskasz przez e-Doręczenia (bezpłatnie w sprawach ZUS).",
                )
            )
        else:
            docs.append(
                DocumentRequirement(
                    form_code="Dane dziecka (§ 13 ust. 2–3)",
                    title="Dane identyfikacyjne dziecka zamiast odpisu aktu urodzenia (płatnik ZUS)",
                    submitted_by="Rodzic (we wniosku ZAM / oświadczeniu)",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Przy składaniu wniosku o zasiłek macierzyński",
                    notes="Zgodnie z § 13 ust. 2 Rozporządzenia MRPiPS z 27.09.2026 r. (Dz.U. poz. 1316) odpisu skróconego aktu urodzenia nie przedstawia się, jeżeli płatnikiem zasiłku jest ZUS — ZUS pobiera go z USC na podstawie danych dziecka (imię, nazwisko, PESEL, data i miejsce urodzenia). W przypadku martwego urodzenia bez sporządzenia aktu wystarcza zaświadczenie lekarza ginekologa lub położnej (§ 13 ust. 1 pkt 2).",
                )
            )

    notes_2026 = [
        "Od 24 października 2026 r. formularze ZUR (rodzicielski) oraz ZAO (ojcowski) zostały połączone z formularzem ZAM i zlikwidowane; zlikwidowano również Z-3b.",
        "Zgodnie z § 13 ust. 2 Rozporządzenia z 27.09.2026 r. (Dz.U. poz. 1316), gdy płatnikiem zasiłku jest ZUS, nie trzeba dołączać odpisu skróconego aktu urodzenia — wystarczą dane identyfikacyjne dziecka.",
        f"Roszczenie o wypłatę zasiłku przedawnia się po upływie {params.claim_limitation_months} miesięcy od ostatniego dnia okresu, za który zasiłek przysługuje (art. 67 ustawy zasiłkowej).",
        f"W przypadku urodzenia martwego dziecka (bez względu na czas trwania ciąży) rodzinie przysługuje również zasiłek pogrzebowy w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12 — przy braku aktu urodzenia wystarcza karta zgonu lub zaświadczenie lekarza ginekologa albo położnej).".replace(",", " "),
        f"Dla stawki {combined_rate_str}% można złożyć jeden wniosek o oba urlopy albo odrębną pisemną deklarację w terminie {deadline_days} dni od porodu (art. 30a ustawy zasiłkowej).",
        "Wzory aktualnych formularzy ZUS dostępne są na stronie www.zus.pl (zakładka Wzory formularzy -> Zasiłki).",
    ]

    return DocumentGuidanceResponse(
        payer=payer,
        payer_explanation=payer_explanation,
        documents=docs,
        important_notes_2026=notes_2026,
    )


def _build_application_sections(
    req: ApplicationSubmissionRequest,
    p: LegalParameters,
) -> tuple[str, str, str, list[str], str | None, str]:
    """Buduje strukturalne elementy wniosku (ref, title, body, attachments, deadline_21, today_str)."""
    today_str = date.today().isoformat()
    prefix_map = {
        ApplicationType.LEAVE_EMPLOYER: "URLOP",
        ApplicationType.LEAVE_SUPPLEMENTARY: "URLOP-UZUP",
        ApplicationType.LEAVE_RESIGNATION: "REZYGNACJA",
        ApplicationType.LEAVE_WORK_COMBINATION: "LACZENIE-PRACY",
        ApplicationType.LEAVE_PATERNITY: "URLOP-OJCOWSKI",
        ApplicationType.LEAVE_ADOPTION_FOSTER: "URLOP-ADOPCJA",
        ApplicationType.LEAVE_PRE_BIRTH: "URLOP-PRZED-PORODEM",
        ApplicationType.LEAVE_FATHER_TAKEOVER: "PRZEJECIE-OJCIEC",
        ApplicationType.ZAM_ZUS: "ZUS-ZAM",
        ApplicationType.USC_BIRTH_CERTIFICATE: "USC-AKT",
    }
    if req.reference_number:
        sanitized_ref = re.sub(r"[^A-Za-z0-9_-]", "", req.reference_number)[:64]
        ref = sanitized_ref or f"{prefix_map.get(req.application_type, 'WNIOSEK')}-{uuid.uuid4().hex[:8].upper()}"
    else:
        ref = f"{prefix_map.get(req.application_type, 'WNIOSEK')}-{uuid.uuid4().hex[:8].upper()}"

    deadline_21: str | None = None
    if req.child_birth_date:
        try:
            birth = date.fromisoformat(req.child_birth_date)
            deadline_21 = (birth + timedelta(days=p.combined_application_deadline_days)).isoformat()
        except ValueError:
            deadline_21 = None

    combined_rate_str = f"{p.combined_21_days_rate * 100:.1f}".replace(".", ",")
    variant_desc = (
        f"{combined_rate_str}% podstawy wymiaru przez cały okres (art. 30a i art. 31 ust. 3 ustawy zasiłkowej)"
        if req.payment_variant == PaymentVariant.COMBINED_81_5
        else f"{p.maternity_rate_standard * 100:.0f}% za urlop macierzyński oraz {p.parental_rate_standard * 100:.0f}% za urlop rodzicielski (art. 31 ust. 1–2 ustawy zasiłkowej)"
    )

    period_txt = f"od dnia {req.leave_start_date or '............'} do dnia {req.leave_end_date or '............'}"
    birth_txt = req.child_birth_date or "............"

    if req.application_type == ApplicationType.LEAVE_EMPLOYER:
        title = "WNIOSEK O UDZIELENIE URLOPU MACIERZYŃSKIEGO I URLOPU RODZICIELSKIEGO"
        legal_basis = "art. 180 § 1, art. 182¹ᵃ oraz art. 182¹ᵈ Kodeksu pracy; § 15 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi urlopu macierzyńskiego oraz bezpośrednio po nim urlopu rodzicielskiego "
            f"z tytułu urodzenia dziecka w dniu {birth_txt}, w okresie {period_txt} "
            f"(planowana liczba części urlopu rodzicielskiego: {req.leave_parts_count or 1}, maksymalnie {p.parental_max_parts}).\n\n"
            "Wskazanie dotychczas wykorzystanego urlopu rodzicielskiego / zasiłku za okres tego urlopu (§ 15 ust. 1 pkt 2): "
            "okres: ............ (dotychczas wykorzystana liczba części / złożonych wniosków: ............).\n\n"
            f"Jednocześnie wnioskuję o wypłacanie zasiłku macierzyńskiego w wariancie: {variant_desc}."
        )
        attachments = [
            "1. Odpis skrócony aktu urodzenia dziecka lub jego kopia (§ 15 ust. 2 pkt 1).",
            "2. Oświadczenie o braku zamiaru korzystania przez drugiego z rodziców z urlopu rodzicielskiego (albo o okresie korzystania) w okresie objętym wnioskiem (§ 15 ust. 2 pkt 2).",
            "3. Kopia zaświadczenia „Za życiem” (art. 4 ust. 3 ustawy „Za życiem”) — jeżeli dotyczy wydłużonego wymiaru urlopu rodzicielskiego (§ 15 ust. 2 pkt 3).",
        ]
    elif req.application_type == ApplicationType.LEAVE_SUPPLEMENTARY:
        title = "WNIOSEK O UDZIELENIE UZUPEŁNIAJĄCEGO URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 180² Kodeksu pracy; § 14 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        mat_end_txt = req.maternity_end_date or "............"
        body = (
            f"Na podstawie {legal_basis} wnoszę o udzielenie uzupełniającego urlopu macierzyńskiego bezpośrednio po zakończeniu urlopu macierzyńskiego "
            f"(termin zakończenia urlopu macierzyńskiego: {mat_end_txt}), "
            f"w okresie {period_txt}, w związku z pobytem dziecka (ur. {birth_txt}) w szpitalu "
            f"w okresie od {req.hospitalization_from or '............'} do {req.hospitalization_to or '............'}.\n\n"
            f"Urlop jest udzielany jednorazowo (wniosek składany min. 21 dni przed końcem urlopu macierzyńskiego) i płatny w wysokości {p.supplementary_maternity_rate * 100:.0f}% podstawy wymiaru zasiłku."
        )
        attachments = [
            "1. Zaświadczenie wydane przez szpital zawierające informacje o tygodniu ciąży, masie urodzeniowej oraz okresie pobytu dziecka w szpitalu (§ 14 ust. 2 pkt 1).",
            "2. Oświadczenie o braku zamiaru korzystania z uzupełniającego urlopu macierzyńskiego przez drugiego rodzica (§ 14 ust. 2 pkt 2).",
        ]
    elif req.application_type == ApplicationType.LEAVE_WORK_COMBINATION:
        title = "WNIOSEK O ŁĄCZENIE URLOPU RODZICIELSKIEGO Z WYKONYWANIEM PRACY"
        legal_basis = "art. 182¹ᵉ oraz art. 182¹ᶠ Kodeksu pracy; § 16 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        fte_val = req.work_fte_fraction or 0.5
        if req.work_during_extended_part is True:
            ext_decl = (
                f"Oświadczam (zgodnie z § 16 pkt 4 rozporządzenia), że zamierzam łączyć również wydłużoną część urlopu rodzicielskiego "
                f"z wykonywaniem pracy w wymiarze {fte_val} etatu (art. 182¹ᶠ § 7 Kodeksu pracy)."
            )
        elif req.work_during_extended_part is False:
            ext_decl = (
                "Oświadczam (zgodnie z § 16 pkt 4 rozporządzenia), że nie zamierzam łączyć wydłużonej części urlopu rodzicielskiego "
                "z wykonywaniem pracy (art. 182¹ᶠ § 2 Kodeksu pracy)."
            )
        else:
            ext_decl = (
                "Oświadczenie (§ 16 pkt 4 rozporządzenia): zamierzam / nie zamierzam* łączyć wydłużoną część urlopu rodzicielskiego "
                f"z wykonywaniem pracy w wymiarze {fte_val} etatu (*niepotrzebne skreślić)."
            )
        body = (
            f"Na podstawie {legal_basis} wnoszę o umożliwienie łączenia korzystania z urlopu rodzicielskiego (na dziecko ur. {birth_txt}) "
            f"z wykonywaniem pracy u pracodawcy udzielającego urlopu w wymiarze {fte_val} etatu (nie wyższym niż {p.parental_work_max_fte} pełnego wymiaru czasu pracy), "
            f"w okresie {period_txt}.\n\n"
            f"{ext_decl}\n\n"
            "Wnoszę o proporcjonalne wydłużenie wymiaru urlopu rodzicielskiego zgodnie z art. 182¹ᶠ Kodeksu pracy oraz odpowiednie ustalenie wysokości zasiłku macierzyńskiego."
        )
        attachments = [
            "1. Propozycja harmonogramu czasu pracy w okresie łączenia urlopu z pracą (opcjonalnie).",
        ]
    elif req.application_type == ApplicationType.LEAVE_RESIGNATION:
        title = "WNIOSEK W SPRAWIE REZYGNACJI Z POZOSTAŁEJ CZĘŚCI URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 180 § 4 Kodeksu pracy; § 3 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} informuję o rezygnacji z pozostałej części urlopu macierzyńskiego (po wykorzystaniu po porodzie co najmniej {p.maternity_min_mother_weeks} tygodni) "
            f"i deklaruję powrót do pracy z dniem {req.resignation_date or '............'}.\n\n"
            "Pozostałą część urlopu macierzyńskiego przejmie ojciec wychowujący dziecko bezpośrednio po zakończeniu mojego urlopu."
        )
        attachments = [
            "1. Kopia wniosku pracownika – ojca wychowującego dziecko o udzielenie pozostałej części urlopu macierzyńskiego (albo kopia oświadczenia ubezpieczonego ojca o przerwaniu działalności zarobkowej).",
        ]
    elif req.application_type == ApplicationType.LEAVE_PATERNITY:
        title = "WNIOSEK O UDZIELENIE URLOPU OJCOWSKIEGO"
        legal_basis = "art. 182³ Kodeksu pracy; § 17 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi urlopu ojcowskiego (albo jego części) "
            f"z tytułu urodzenia / przysposobienia dziecka w dniu {birth_txt}, w okresie {period_txt} "
            f"(maksymalny łączny wymiar: {p.paternity_weeks} tygodnie, nie więcej niż w 2 częściach po min. 7 dni, do ukończenia 12. miesiąca życia dziecka "
            f"albo w ciągu 12 miesięcy od uprawomocnienia się postanowienia o przysposobieniu, nie później niż do ukończenia 14. roku życia — art. 182³ § 1 KP).\n\n"
            f"Za okres urlopu ojcowskiego przysługuje zasiłek macierzyński w wysokości {p.paternity_rate * 100:.0f}% podstawy wymiaru."
        )
        attachments = [
            "1. Odpis skrócony aktu urodzenia dziecka (lub prawomocne postanowienie sądu o przysposobieniu dziecka).",
            "2. Oświadczenie pracownika – ojca, czy korzystał wcześniej z urlopu ojcowskiego albo jego części (§ 17 ust. 2 pkt 3).",
        ]
    elif req.application_type == ApplicationType.LEAVE_ADOPTION_FOSTER:
        title = "WNIOSEK O UDZIELENIE URLOPU NA WARUNKACH URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 183 Kodeksu pracy; § 18 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi urlopu na warunkach urlopu macierzyńskiego "
            f"z tytułu przyjęcia na wychowanie dziecka: imię i nazwisko ............ (ur. {birth_txt}), "
            f"w ramach rodziny zastępczej niezawodowej albo wystąpienia do sądu opiekuńczego o przysposobienie, "
            f"w okresie {period_txt} (wniosek składany w terminie 7 dni od dnia przyjęcia dziecka na wychowanie — art. 183 § 6 KP).\n\n"
            f"Wybrany wariant wypłaty zasiłku macierzyńskiego: {variant_desc}."
        )
        attachments = [
            "1. Oświadczenie pracownika o dacie przyjęcia dziecka na wychowanie oraz kopia wniosku o wszczęcie postępowania o przysposobienie z poświadczeniem sądu albo zaświadczenie sądu opiekuńczego, albo kopia prawomocnego orzeczenia sądu o umieszczeniu dziecka w rodzinie zastępczej niezawodowej, albo kopia umowy cywilnoprawnej zawartej pomiędzy rodziną zastępczą a starostą (§ 18 ust. 2 pkt 1).",
            "2. Kopia prawomocnej decyzji o odroczeniu obowiązku szkolnego (jeżeli dotyczy dziecka w wieku 7–10 lat w rodzinie zastępczej — § 18 ust. 2 pkt 2).",
        ]
    elif req.application_type == ApplicationType.LEAVE_PRE_BIRTH:
        title = "WNIOSEK O UDZIELENIE CZĘŚCI URLOPU MACIERZYŃSKIEGO PRZED PRZEWIDYWANĄ DATĄ PORODU"
        legal_basis = "art. 180 § 2 Kodeksu pracy; § 2 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi części urlopu macierzyńskiego przed przewidywaną datą porodu "
            f"(przewidywana data porodu: {birth_txt}), w okresie {period_txt} "
            f"(maksymalnie do {p.maternity_pre_birth_max_weeks} tygodni przed przewidywaną datą porodu).\n\n"
            "Po porodzie przysługuje pozostała, niewykorzystana część urlopu macierzyńskiego."
        )
        attachments = [
            "1. Kopia zaświadczenia lekarskiego wystawionego na zwykłym druku, określającego przewidywaną datę porodu (§ 2 ust. 2).",
        ]
    elif req.application_type == ApplicationType.LEAVE_FATHER_TAKEOVER:
        title = "WNIOSEK PRACOWNIKA – OJCA O UDZIELENIE POZOSTAŁEJ CZĘŚCI URLOPU MACIERZYŃSKIEGO"
        legal_basis = "art. 180 § 4 i § 9 Kodeksu pracy; § 5 Rozporządzenia MRPiPS z dnia 11 marca 2025 r. (Dz.U. z 2025 r. poz. 322)"
        body = (
            f"Na podstawie {legal_basis} zwracam się z wnioskiem o udzielenie mi pozostałej części urlopu macierzyńskiego "
            f"na dziecko: imię i nazwisko ............ (ur. {birth_txt}), w okresie {period_txt}, bezpośrednio po rezygnacji matki dziecka z korzystania z pozostałej części urlopu macierzyńskiego "
            f"(po wykorzystaniu przez matkę co najmniej {p.maternity_min_mother_weeks} tygodni po porodzie).\n\n"
            "Oświadczenie pracownika (§ 5 ust. 1 pkt 3): okres urlopu macierzyńskiego (albo pobierania zasiłku macierzyńskiego za okres odpowiadający części urlopu macierzyńskiego) wykorzystany przed porodem wynosi: ............ ."
        )
        attachments = [
            "1. Skrócony odpis aktu urodzenia dziecka lub jego kopia (§ 5 ust. 2 pkt 1).",
            "2. Oświadczenie pracownicy – matki dziecka o zamiarze rezygnacji z pozostałej części urlopu macierzyńskiego (albo oświadczenie ubezpieczonej matki o zamiarze rezygnacji z pobierania zasiłku macierzyńskiego — § 5 ust. 2 pkt 2).",
        ]
    elif req.application_type == ApplicationType.ZAM_ZUS:
        title = "WNIOSEK O ZASIŁEK MACIERZYŃSKI — FORMULARZ ZUS ZAM"
        legal_basis = "art. 29–31 ustawy z dnia 25 czerwca 1999 r. o świadczeniach pieniężnych z ubezpieczenia społecznego w razie choroby i macierzyństwa (Dz.U. z 2026 r. poz. 854)"
        body = (
            f"Na podstawie {legal_basis} wnoszę o ustalenie prawa i wypłatę zasiłku macierzyńskiego za okres {period_txt} "
            f"z tytułu urodzenia dziecka w dniu {birth_txt}.\n\n"
            f"Wybrany wariant wypłaty: {variant_desc}.\n"
            "Uwaga: Od 24 października 2026 r. formularz ZAM zastępuje dotychczasowe formularze ZUR i ZAO i jest składany elektronicznie przez PUE/eZUS lub w placówce ZUS."
        )
        attachments = [
            "1. Dane identyfikacyjne dziecka (imię, nazwisko, PESEL, data i miejsce urodzenia) — zgodnie z § 13 ust. 2–3 Rozp. z 27.09.2026 r. (Dz.U. poz. 1316) przy płatniku ZUS nie dołącza się odpisu aktu urodzenia (ZUS pobiera go z USC); w razie martwego urodzenia bez aktu: zaświadczenie lekarza ginekologa lub położnej.",
            "2. Zaświadczenie płatnika składek Z-3 (pracownik) lub Z-3a (zleceniobiorca) — jeśli płatnik nie jest uprawniony do wypłaty zasiłków.",
            "3. Oświadczenie o posiadaniu zaświadczenia 'Za życiem' (art. 61b ust. 4a) lub zaświadczenie szpitalne — jeśli dotyczy.",
        ]
    else:
        copy_label = "odpisu zupełnego" if req.usc_copy_type == "zupelny" else "odpisu skróconego"
        copy_header = "ODPISU ZUPEŁNEGO" if req.usc_copy_type == "zupelny" else "ODPISU SKRÓCONEGO"
        title = f"WNIOSEK O WYDANIE {copy_header} AKTU URODZENIA (REJESTR STANU CYWILNEGO)"
        legal_basis = "art. 44–45 ustawy z dnia 28 listopada 2014 r. – Prawo o aktach stanu cywilnego"
        body = (
            f"Na podstawie {legal_basis} wnoszę o wydanie {copy_label} aktu urodzenia dziecka urodzonego w dniu {birth_txt}, "
            "niezbędnego do przedłożenia pracodawcy / organowi w celu ustalenia prawa do uprawnień rodzicielskich i świadczeń z ubezpieczeń społecznych.\n\n"
            "Wniosek o odpis w sprawach ubezpieczeń społecznych oraz zatrudnienia jest zwolniony z opłaty skarbowej (art. 2 ust. 1 pkt 1 lit. b i f ustawy o opłacie skarbowej). "
            "Uwaga: od 1 stycznia 2026 r. elektroniczna obsługa wniosku przez gov.pl realizowana jest za pośrednictwem e-Doręczeń."
        )
        attachments = [
            "1. Dokument tożsamości (lub podpis Profilem Zaufanym / e-Dowodem przez gov.pl oraz skrzynka do e-Doręczeń).",
        ]

    return ref, title, body, attachments, deadline_21, today_str


def simulate_application_submission(
    req: ApplicationSubmissionRequest,
    params: LegalParameters | None = None,
) -> ApplicationSubmissionResponse:
    from app.services.parameter_store import parameter_store

    p = params or parameter_store.get()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ref, title, body, attachments, deadline_21, today_str = _build_application_sections(req, p)
    combined_rate_str = f"{p.combined_21_days_rate * 100:.1f}".replace(".", ",")

    lines = [
        f"                                                  Miejscowość, dnia {today_str}",
        "",
        "WNIOSKODAWCA:",
        f"  {req.applicant_name}",
        f"  PESEL: {req.pesel_masked}",
        "",
        "ADRESAT:",
        f"  {req.recipient}",
        "",
        title,
        "",
        body,
    ]
    if deadline_21 and req.application_type in (
        ApplicationType.LEAVE_EMPLOYER,
        ApplicationType.LEAVE_ADOPTION_FOSTER,
        ApplicationType.ZAM_ZUS,
    ):
        lines.extend(
            [
                "",
                f"Termin {p.combined_application_deadline_days} dni po porodzie/przyjęciu dziecka na wniosek/deklarację o {combined_rate_str}%: {deadline_21}.",
            ]
        )
    if req.notes:
        lines.extend(["", f"Informacje dodatkowe: {req.notes}"])
    lines.extend(
        [
            "",
            "ZAŁĄCZNIKI:",
            *[f"  {a}" for a in attachments],
            "",
            f"Nr roboczy dokumentu: {ref}",
            "",
            "                                                  ................................................",
            "                                                     (czytelny podpis wnioskodawcy)",
        ]
    )

    return ApplicationSubmissionResponse(
        reference_number=ref,
        application_type=req.application_type,
        recipient=req.recipient,
        submitted_at=now_iso,
        deadline_21_days=deadline_21,
        status="Wygenerowano wzór dokumentu zgodny z przepisami 2025/2026",
        summary=f"Przygotowano {title} dla {req.applicant_name} (adresat: {req.recipient}).",
        generated_document_text="\n".join(lines),
    )


def generate_application_pdf(
    req: ApplicationSubmissionRequest,
    params: LegalParameters | None = None,
) -> tuple[str, bytes]:
    """Generuje gotowy do druku plik PDF (A4) z pełną obsługą polskich znaków (DejaVuSans)."""
    from fpdf import FPDF
    from app.services.parameter_store import parameter_store

    p = params or parameter_store.get()
    ref, title, body, attachments, deadline_21, today_str = _build_application_sections(req, p)
    combined_rate_str = f"{p.combined_21_days_rate * 100:.1f}".replace(".", ",")

    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    bundled_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    system_dir = Path("/usr/share/fonts/truetype/dejavu")
    regular_font = bundled_dir / "DejaVuSans.ttf"
    bold_font = bundled_dir / "DejaVuSans-Bold.ttf"
    if not (regular_font.exists() and bold_font.exists()):
        regular_font = system_dir / "DejaVuSans.ttf"
        bold_font = system_dir / "DejaVuSans-Bold.ttf"

    use_unicode = regular_font.exists() and bold_font.exists()
    if use_unicode:
        pdf.add_font("DejaVu", "", str(regular_font))
        pdf.add_font("DejaVu", "B", str(bold_font))
        font_family = "DejaVu"
    else:
        font_family = "Helvetica"

    def _prep(txt: str) -> str:
        return _sanitize_for_unicode_font(txt) if use_unicode else _to_latin1_safe(txt)

    def _write_line(txt: str, style: str = "", size: float = 10, height: float = 5.8, align: str = "L") -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font(font_family, style, size)
        pdf.multi_cell(pdf.epw, height, _prep(txt), align=align, new_x="LMARGIN", new_y="NEXT")

    # Strukturalne renderowanie sekcji — odporne na wstrzykiwanie formatowania w polu notes
    _write_line(f"Miejscowość, dnia {today_str}", size=10, height=6, align="R")
    pdf.ln(3)

    _write_line("WNIOSKODAWCA:", style="B", size=10, height=6)
    _write_line(req.applicant_name)
    _write_line(f"PESEL: {req.pesel_masked}")
    pdf.ln(3)

    _write_line("ADRESAT:", style="B", size=10, height=6)
    _write_line(req.recipient)
    pdf.ln(5)

    _write_line(title, style="B", size=12, height=7, align="C")
    pdf.ln(4)

    for para in body.split("\n\n"):
        _write_line(para.strip())
        pdf.ln(2.5)

    if deadline_21 and req.application_type in (
        ApplicationType.LEAVE_EMPLOYER,
        ApplicationType.LEAVE_ADOPTION_FOSTER,
        ApplicationType.ZAM_ZUS,
    ):
        _write_line(
            f"Termin {p.combined_application_deadline_days} dni po porodzie/przyjęciu dziecka na wniosek/deklarację o {combined_rate_str}%: {deadline_21}."
        )
        pdf.ln(2.5)

    if req.notes:
        _write_line(f"Informacje dodatkowe: {req.notes}")
        pdf.ln(2.5)

    pdf.ln(2)
    _write_line("ZAŁĄCZNIKI:", style="B", size=10, height=6)
    for att in attachments:
        _write_line(att)

    pdf.ln(4)
    _write_line(f"Nr roboczy dokumentu: {ref}", size=9.5, height=5.5)
    pdf.ln(6)
    _write_line("................................................", size=9, height=5.5, align="R")
    _write_line("(czytelny podpis wnioskodawcy)", size=9, height=5.5, align="R")

    return ref, bytes(pdf.output())
