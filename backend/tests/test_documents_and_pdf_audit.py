import io
from pathlib import Path
import zlib
from unittest.mock import patch
from fastapi.testclient import TestClient
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)
from app.config import settings
from app.main import app
from app.models.simulation import ApplicationSubmissionRequest, ApplicationType
from app.services import document_service
from app.services.pdf_parser_service import analyze_pdf_bytes

client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-Key": settings.admin_api_key}
FONT_PATH = str(Path(__file__).resolve().parent.parent / "app" / "assets" / "fonts" / "DejaVuSans.ttf")


def _make_text_pdf(lines: list[str]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.add_font("DejaVu", "", FONT_PATH)
    pdf.set_font("DejaVu", "", 10)
    for line in lines:
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _make_xfa_pdf(xml_payload: str, *, compressed: bool = True, single_stream: bool = False) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    xml_bytes = xml_payload.encode("utf-8")

    stream = DecodedStreamObject()
    if compressed:
        stream._data = zlib.compress(xml_bytes)
        stream[NameObject("/Filter")] = NameObject("/FlateDecode")
    else:
        stream.set_data(xml_bytes)
    stream_ref = writer._add_object(stream)

    if single_stream:
        xfa_entry = stream_ref
    else:
        xfa_entry = ArrayObject([TextStringObject("datasets"), stream_ref])

    acro = DictionaryObject(
        {
            NameObject("/Fields"): ArrayObject(),
            NameObject("/XFA"): xfa_entry,
        }
    )
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(acro)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_acroform_pdf(fields: dict[str, str], body_lines: list[str]) -> bytes:
    base_bytes = _make_text_pdf(body_lines)
    reader = PdfReader(io.BytesIO(base_bytes))
    writer = PdfWriter()
    writer.append(reader)
    page = writer.pages[0]

    field_refs = ArrayObject()
    for idx, (fname, fval) in enumerate(fields.items()):
        widget = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Widget"),
                NameObject("/FT"): NameObject("/Tx"),
                NameObject("/T"): TextStringObject(fname),
                NameObject("/V"): TextStringObject(fval),
                NameObject("/Rect"): ArrayObject(
                    [NumberObject(10), NumberObject(10 + idx * 15), NumberObject(200), NumberObject(22 + idx * 15)]
                ),
            }
        )
        ref = writer._add_object(widget)
        field_refs.append(ref)

    page[NameObject("/Annots")] = field_refs
    acro = DictionaryObject({NameObject("/Fields"): field_refs})
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(acro)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# =============================================================================
# 1. REGRESJE KALKULATORA I PARAMETRÓW ADMINA
# =============================================================================


def test_adoption_near_age_14_preserves_remaining_parental_and_caps_work_extension():
    # Dziecko 13.5 r.ż. (~26 tyg. do 14. urodzin): 20 tyg. na warunkach macierzyńskiego + 6 tyg. rodzicielskiego (NIE 0!)
    r1 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.5,
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "father_takes_parental_weeks": 0,
        },
    ).json()
    assert r1["maternity_weeks"] == 20
    assert r1["parental_weeks_total"] == 6.0
    assert r1["equalization_to_100_pln"] == 0.0

    # Dziecko 13.3 r.ż. (~36 tyg. do 14. urodzin) przy father=0 -> matka dostaje pełne pozostałe 16 tyg.
    r2 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.3,
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "father_takes_parental_weeks": 0,
        },
    ).json()
    assert r2["maternity_weeks"] == 20
    assert r2["parental_weeks_total"] == 16.0

    # Nieubezpieczona matka + ubezpieczony ojciec, adopcja 13.7 r.ż. (floor(15.64) = 15 tyg. do 14. r.ż.) -> ojciec dostaje 15 tyg.
    r3 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.7,
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_gross_salary": 7000.0,
        },
    ).json()
    assert r3["eligible"] is True
    assert r3["parental_weeks_total"] == 15.0

    # Adopcja 13.0 r.ż. (52 tyg. do 14. r.ż.) + łączenie z pracą NIE przekracza 52 tyg. (14. r.ż.)!
    r4 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.0,
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "combine_parental_with_work": True,
            "work_fte_fraction": 0.5,
            "combined_work_weeks": 20,
            "work_during_extended_part": True,
        },
    ).json()
    assert r4["total_weeks"] <= 52.0


def test_parent2_jdg_debt_suspends_only_when_parent2_claims_leave():
    # Rodzic 2 ma dług JDG 500 zł, ale bierze 0 tyg. urlopu -> brak wstrzymania dla matki na UoP
    r_zero = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "second_parent_insurance_title": "jdg",
            "second_parent_contribution_debt_pln": 500.0,
            "father_takes_parental_weeks": 0,
            "father_takes_paternity_leave": False,
        },
    ).json()
    assert r_zero["payout_suspended_due_to_debt"] is False

    # Gdy Rodzic 2 bierze 9 tyg. rodzicielskiego -> wstrzymanie jest sygnalizowane
    r_claim = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "second_parent_insurance_title": "jdg",
            "second_parent_contribution_debt_pln": 500.0,
            "father_takes_parental_weeks": 9,
        },
    ).json()
    assert r_claim["payout_suspended_due_to_debt"] is True


def test_benefit_base_uses_last_12_months_and_pregnancy_art30_uses_maternity_rate():
    # Ostatnie 12 mies. z [5000]*12 + [10000]*3 to 9*5000 + 3*10000 -> śr. 6250 -> 5393.13 zł
    r_base = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "uop",
            "mode": "uop_12m",
            "monthly_gross_salaries": [5000.0] * 12 + [10000.0] * 3,
        },
    ).json()
    assert abs(r_base["computed_base_monthly"] - round(6250.0 * 0.8629, 2)) < 0.02

    # Niespełniony okres wyczekiwania -> rehabilitation_* zerowe
    r_wait = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "uop", "insurance_days": 10, "gross_monthly_salary": 7000.0},
    ).json()
    assert r_wait["eligible_sickness_benefit"] is False
    assert r_wait["rehabilitation_monthly_gross"] == 0.0
    assert r_wait["rehabilitation_max_days"] == 0

    # Admin: ujemne tygodnie w maternity_weeks_by_children -> HTTP 422
    params = client.get("/api/v1/admin/parameters").json()
    bad_params = {**params, "maternity_weeks_by_children": {**params["maternity_weeks_by_children"], "1": -5}}
    assert client.put("/api/v1/admin/parameters", json=bad_params, headers=ADMIN_HEADERS).status_code == 422

    # Art. 30 ust. 3: stawka dzienna zgodna z params.maternity_rate_standard
    try:
        mod = {**params, "maternity_rate_standard": 0.9}
        assert client.put("/api/v1/admin/parameters", json=mod, headers=ADMIN_HEADERS).status_code == 200
        r_art30 = client.post(
            "/api/v1/calculator/pregnancy",
            json={
                "insurance_title": "uop",
                "gross_monthly_salary": 10000.0,
                "employment_terminated_special": True,
                "termination_reason": "bankruptcy_liquidation",
            },
        ).json()
        assert abs(r_art30["monthly_benefit_gross"] - round(8629.0 * 0.9, 2)) < 0.02
        assert abs(r_art30["daily_benefit_gross"] - round(r_art30["monthly_benefit_gross"] / 30.0, 2)) < 0.02
    finally:
        client.post("/api/v1/admin/parameters/reset", headers=ADMIN_HEADERS)


# =============================================================================
# 2. GENEROWANIE DOKUMENTÓW I EKSPORT PDF
# =============================================================================


def test_all_10_document_templates_and_legal_citations():
    all_types = [t.value for t in ApplicationType]
    assert len(all_types) == 10

    for app_type in all_types:
        payload = {
            "application_type": app_type,
            "applicant_name": "Żaneta Źdźbło-Ćwiklińska",
            "pesel_masked": "920514*****",
            "child_birth_date": "2026-11-20",
            "leave_start_date": "2026-11-20",
            "leave_end_date": "2027-05-20",
            "maternity_end_date": "2027-04-08",
            "hospitalization_from": "2026-11-20",
            "hospitalization_to": "2026-12-20",
            "work_fte_fraction": 0.5,
            "work_during_extended_part": False,
            "usc_copy_type": "zupelny",
            "recipient": "Pracodawca / ZUS / USC",
            "notes": "WNIOSEK FAŁSZYWY NAGŁÓWEK\n....podpis",
        }
        r_sub = client.post("/api/v1/documents/submit", json=payload)
        assert r_sub.status_code == 200, f"submit failed for {app_type}: {r_sub.text}"
        data = r_sub.json()

        # Ten sam numer referencyjny przekazany do /pdf
        payload["reference_number"] = data["reference_number"]
        r_pdf = client.post("/api/v1/documents/pdf", json=payload)
        assert r_pdf.status_code == 200
        assert r_pdf.content.startswith(b"%PDF-")
        assert data["reference_number"] in r_pdf.headers["content-disposition"]

        extracted_pdf_text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r_pdf.content)).pages)
        assert data["reference_number"] in extracted_pdf_text
        assert "Żaneta" in extracted_pdf_text

        if app_type == "leave_work_combination":
            assert "§ 16" in data["generated_document_text"]
            assert "§ 19" not in data["generated_document_text"]
            assert "§ 16 pkt 4" in data["generated_document_text"]
        elif app_type == "leave_supplementary":
            assert "2027-04-08" in data["generated_document_text"]
            assert "§ 14" in data["generated_document_text"]
        elif app_type == "usc_birth_certificate":
            assert "ODPISU ZUPEŁNEGO" in data["generated_document_text"]
            assert "e-Doręczeń" in data["generated_document_text"]
        elif app_type == "zam_zus":
            assert "§ 13 ust. 2" in data["generated_document_text"]


def test_document_guidance_none_and_validation_and_admin_sync_and_font_fallback():
    # insurance_title=none NIE może wpadać w gałąź JDG!
    g_none = client.get("/api/v1/documents/guidance", params={"insurance_title": "none"}).json()
    codes = [d["form_code"] for d in g_none["documents"]]
    assert any("SR-7" in c for c in codes)
    assert "ZAS-53" not in codes

    # Płatnik ZUS -> informacja o § 13 ust. 2 (bez składania odpisu aktu urodzenia)
    g_jdg = client.get("/api/v1/documents/guidance", params={"insurance_title": "jdg"}).json()
    assert any("§ 13 ust. 2" in d["form_code"] or "§ 13 ust. 2" in d["notes"] for d in g_jdg["documents"])

    # Walidacja wejścia: same spacje, nieistniejąca data, odwrócony zakres, notatka >2000 znaków
    base_req = {
        "application_type": "leave_employer",
        "applicant_name": "Anna Kowalska",
        "pesel_masked": "920514*****",
        "recipient": "Pracodawca",
    }
    assert client.post("/api/v1/documents/submit", json={**base_req, "applicant_name": "   "}).status_code == 422
    assert client.post("/api/v1/documents/submit", json={**base_req, "child_birth_date": "2026-02-30"}).status_code == 422
    assert (
        client.post(
            "/api/v1/documents/submit",
            json={**base_req, "leave_start_date": "2026-12-01", "leave_end_date": "2026-11-01"},
        ).status_code
        == 422
    )
    assert client.post("/api/v1/documents/submit", json={**base_req, "notes": "A" * 2500}).status_code == 422

    # Synchronizacja tekstu wniosku ze zmianą parametrów w /admin
    params = client.get("/api/v1/admin/parameters").json()
    try:
        mod = {**params, "combined_application_deadline_days": 30, "combined_21_days_rate": 0.85}
        assert client.put("/api/v1/admin/parameters", json=mod, headers=ADMIN_HEADERS).status_code == 200
        sub = client.post(
            "/api/v1/documents/submit",
            json={**base_req, "child_birth_date": "2026-11-20", "payment_variant": "81_5"},
        ).json()
        assert sub["deadline_21_days"] == "2026-12-20"
        assert "30 dni" in sub["generated_document_text"]
        assert "85,0%" in sub["generated_document_text"]
        assert "Termin 21 dni" not in sub["generated_document_text"]
    finally:
        client.post("/api/v1/admin/parameters/reset", headers=ADMIN_HEADERS)

    # Awaryjny fallback Helvetica (gdy brak plików DejaVuSans.ttf) nie rzuca FPDFUnicodeEncodingException
    req_obj = ApplicationSubmissionRequest(**base_req)
    with patch("pathlib.Path.exists", return_value=False):
        ref, pdf_bytes = document_service.generate_application_pdf(req_obj)
        assert ref.startswith("URLOP-")
        assert pdf_bytes.startswith(b"%PDF-")


# =============================================================================
# 3. ZASYSANIE I PARSOWANIE PDF (ROUND-TRIP, XFA, ACROFORM, EDGE CASE'Y)
# =============================================================================


def test_pdf_parser_zam_roundtrip_and_acroform_and_xfa_variants():
    # Round-trip własnego wygenerowanego ZAM_ZUS -> primary_form musi być ZAM (nie Z-3A!) i tytuł != zlecenie
    zam_pdf = client.post(
        "/api/v1/documents/pdf",
        json={
            "application_type": "zam_zus",
            "applicant_name": "Żaneta Źdźbło-Ćwiklińska",
            "pesel_masked": "920514*****",
            "child_birth_date": "2026-11-20",
            "leave_start_date": "2026-11-20",
            "leave_end_date": "2027-11-18",
            "recipient": "Zakład Ubezpieczeń Społecznych (PUE/eZUS)",
        },
    ).content
    rt = analyze_pdf_bytes("ZUS-ZAM.pdf", zam_pdf)
    assert rt.extracted_fields.form_type == "ZAM"
    assert rt.suggested_insurance_title == "uop"
    assert rt.extracted_fields.applicant_name == "Żaneta Źdźbło-Ćwiklińska"
    assert rt.extracted_fields.pesel_masked == "920514*****"

    # AcroForm z kropką po 'zł.' ("7 500,00 zł.") + 2 kolejne kwoty
    acro_pdf = _make_acroform_pdf(
        {
            "Imie": "Janina",
            "Nazwisko": "Nowak",
            "PESEL": "91041212345",
            "Kwota_1": "7 500,00 zł.",
            "Kwota_2": "7800,00",
            "Kwota_3": "8000,00",
        },
        ["Zaświadczenie płatnika składek Z-3", "Ubezpieczenie chorobowe: TAK", "Liczba ubezpieczonych: 45"],
    )
    res_acro = analyze_pdf_bytes("Z-3.pdf", acro_pdf)
    assert res_acro.extracted_fields.form_type == "Z-3"
    assert res_acro.extracted_fields.extracted_amounts == [7500.0, 7800.0, 8000.0]
    assert res_acro.verification_status == "verified"

    # XFA z powtarzalnymi tagami <Kwota> i wcześniejszym PESEL płatnika — test dla FlateDecode, nieskompresowanego i single-stream
    xfa_xml = (
        "<xfa:datasets xmlns:xfa='http://www.xfa.org/schema/xfa-data/1.0/'>"
        "<xfa:data><Z3>"
        "<DanePlatnika><PESEL>70010199999</PESEL></DanePlatnika>"
        "<DaneUbezpieczonego><Imie>Katarzyna</Imie><Nazwisko>Wiśniewska</Nazwisko><PESEL>93071512345</PESEL></DaneUbezpieczonego>"
        "<Tabela>"
        "<Wiersz><Kwota>6000,00</Kwota></Wiersz>"
        "<Wiersz><Kwota>7000,00</Kwota></Wiersz>"
        "<Wiersz><Kwota>8000,00</Kwota></Wiersz>"
        "</Tabela>"
        "</Z3></xfa:data></xfa:datasets>"
    )
    for compressed, single in [(True, False), (False, False), (False, True)]:
        xfa_pdf = _make_xfa_pdf(xfa_xml, compressed=compressed, single_stream=single)
        res_xfa = analyze_pdf_bytes("Z-3_xfa.pdf", xfa_pdf)
        assert res_xfa.extracted_fields.extracted_amounts == [6000.0, 7000.0, 8000.0]
        assert res_xfa.suggested_gross_salary == 7000.0
        assert res_xfa.extracted_fields.pesel_masked == "930715*****"
        assert res_xfa.extracted_fields.applicant_name == "Katarzyna Wiśniewska"


def test_pdf_parser_regex_sum_row_integer_amounts_and_eru_handoff():
    # False positive "ADRES ZAM." NIE może wykrywać ZAM
    fp_pdf = _make_text_pdf(["DOKUMENT INFORMACYJNY", "ADRES ZAM. UL. KWIATOWA 12, WARSZAWA"])
    assert "ZAM" not in analyze_pdf_bytes("pismo.pdf", fp_pdf).detected_forms

    # Z3b bez myślnika -> Z-3B
    z3b_pdf = _make_text_pdf(["Formularz Z3b archiwalny sprzed 24.10.2026"])
    assert "Z-3B" in analyze_pdf_bytes("doc.pdf", z3b_pdf).detected_forms

    # "Ubezpieczenie chorobowe: NIE" -> denied
    den_pdf = _make_text_pdf(["Zaświadczenie Z-3a", "Ubezpieczenie chorobowe: NIE"])
    assert analyze_pdf_bytes("z3a.pdf", den_pdf).verification_status == "denied"

    # Kwoty całkowite bez groszy ("7 500 zł", "8000 zł")
    int_pdf = _make_text_pdf(["Zaświadczenie Z-3", "Styczeń: 7 500 zł", "Luty: 8000 zł"])
    res_int = analyze_pdf_bytes("z3.pdf", int_pdf)
    assert res_int.extracted_fields.extracted_amounts == [7500.0, 8000.0]
    assert res_int.suggested_gross_salary == 7750.0

    # Wiersz podsumowania "Razem: 36 000,00" nie zawyża średniej z 6 × 6 000,00
    sum_pdf = _make_text_pdf(
        ["Zaświadczenie Z-3"]
        + [f"Miesiąc {i}: 6 000,00" for i in range(1, 7)]
        + ["Razem: 36 000,00"]
    )
    res_sum = analyze_pdf_bytes("z3_sum.pdf", sum_pdf)
    assert res_sum.suggested_gross_salary == 6000.0

    # ZAS-53 z jawną "Umowa o pracę" -> tytuł 'uop', nie 'jdg'
    zas53_pdf = _make_text_pdf(["Wniosek ZAS-53 o zasiłek chorobowy", "Tytuł: Umowa o pracę"])
    assert analyze_pdf_bytes("zas53.pdf", zas53_pdf).suggested_insurance_title == "uop"

    # ERU z 10 dziećmi -> płynne przekazanie do /calculator/integrated bez HTTP 422
    eru_pdf = _make_text_pdf(["Oświadczenie ERU", "Urodziłam 10 dzieci"])
    res_eru = analyze_pdf_bytes("ERU.pdf", eru_pdf)
    assert res_eru.extracted_fields.children_count == 10
    calc_res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": res_eru.suggested_insurance_title,
            "has_sickness_insurance_on_birth_date": False,
            "children_count": res_eru.extracted_fields.children_count,
        },
    )
    assert calc_res.status_code == 200


def test_guidance_includes_all_statutory_risks_and_kp_protections():
    risks = client.get("/api/v1/guidance/risks").json()
    ids = {r["id"] for r in risks}
    for expected in (
        "wykorzystywanie_ezla_art17",
        "zmiana_etatu_lub_pracodawcy_art40",
        "wyrejestrowanie_dobrowolne_zua",
        "przedawnienie_i_ojcowski",
        "ochrona_trwalosci_art177_kp",
    ):
        assert expected in ids
