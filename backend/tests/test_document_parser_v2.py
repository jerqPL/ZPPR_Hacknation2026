import io
from pathlib import Path
from fastapi.testclient import TestClient
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
from app.main import app
from app.services.pdf_parser_service import analyze_case_documents, analyze_pdf_bytes

client = TestClient(app)
FONT_PATH = str(Path(__file__).resolve().parent.parent / "app" / "assets" / "fonts" / "DejaVuSans.ttf")


def _make_text_pdf(lines: list[str]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.add_font("DejaVu", "", FONT_PATH)
    pdf.set_font("DejaVu", "", 10)
    for line in lines:
        pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _make_scanned_pdf_image(lines: list[str]) -> bytes:
    """Tworzy obraz PNG z polskim tekstem, a następnie osadza go w PDF bez warstwy tekstowej (prawdziwy skan)."""
    img = Image.new("RGB", (1400, 900), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 30)
    y = 50
    for line in lines:
        draw.text((60, y), line, fill="black", font=font)
        y += 52

    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.image(img_buf, x=10, y=10, w=190)
    return bytes(pdf.output())


def test_regular_ezla_does_not_fabricate_pregnancy_or_salary():
    """Zwykłe zwolnienie chorobowe e-ZLA (bez kodu B): NIE może ustawiać ciąży, 7000 zł ani porodu!"""
    pdf = _make_text_pdf(
        [
            "Elektroniczne zaświadczenie lekarskie e-ZLA",
            "Numer: EZLA/2026/11/554433",
            "Pacjent: Jan Kowalski",
            "PESEL: 90010112345",
            "Okres niezdolności do pracy: od 2026-11-01 do 2026-11-14",
            "Kod literowy: brak",
        ]
    )
    res = analyze_pdf_bytes("zwolnienie_l4.pdf", pdf)
    ef = res.extracted_fields

    assert "E-ZLA" in res.detected_forms
    assert res.document_domain == "sickness_general"
    assert res.recommended_calculator == "pregnancy_sickness"
    assert ef.has_code_b is False
    assert ef.pregnancy_confirmed is False
    assert res.suggested_gross_salary is None
    assert res.suggested_custom_benefit_base is None
    assert res.suggested_insurance_title is None
    assert ef.children_count is None
    assert ef.scenario is None
    assert ef.employer_insured_count is None
    assert ef.incapacity_days == 14


def test_pregnancy_ezla_with_code_b_sets_code_b_without_fabricating_salary():
    """e-ZLA z kodem B ustawia has_code_b=True i domenę ciążową, ale nadal nie wymyśla zarobków ani liczby dzieci."""
    pdf = _make_text_pdf(
        [
            "Zaświadczenie lekarskie e-ZLA",
            "Numer: EZLA/2026/10/998877",
            "Okres niezdolności do pracy: od 2026-10-01 do 2026-10-30",
            "Kod literowy: B",
        ]
    )
    res = analyze_pdf_bytes("ezla_ciaza.pdf", pdf)
    ef = res.extracted_fields

    assert res.document_domain == "sickness_pregnancy"
    assert ef.has_code_b is True
    assert ef.pregnancy_confirmed is True
    assert "B" in ef.letter_codes
    assert res.suggested_gross_salary is None
    assert ef.children_count is None
    assert ef.scenario is None


def test_zas53_without_title_or_salary_leaves_them_empty():
    """ZAS-53 bez jawnego tytułu ubezpieczenia nie wymusza JDG, ciąży ani 7000 zł."""
    pdf = _make_text_pdf(
        [
            "WNIOSEK O ZASIŁEK CHOROBOWY ZAS-53",
            "Instrukcja wypełniania",
            "Wypełnij ten wniosek, jeśli prowadzisz pozarolniczą działalność.",
            "Twoje dane",
            "Imię i nazwisko: Marek Nowak",
        ]
    )
    res = analyze_pdf_bytes("zas53.pdf", pdf)
    assert "ZAS-53" in res.detected_forms
    assert res.suggested_insurance_title is None
    assert res.suggested_gross_salary is None
    assert res.extracted_fields.has_code_b is None
    assert res.document_domain == "sickness_general"


def test_scanned_pdf_uses_local_polish_ocr_and_extracts_decision():
    """Prawdziwy skan PDF (obraz bez warstwy tekstowej) jest automatycznie czytany lokalnym OCR PL."""
    scan_pdf = _make_scanned_pdf_image(
        [
            "DECYZJA ZUS",
            "Wniosek o zasilek macierzynski ZAM",
            "Umowa zlecenia - brak zgloszenia do ubezpieczenia chorobowego.",
            "Zaklad Ubezpieczen Spolecznych postanawia:",
            "odmowic prawa do zasilku macierzynskiego.",
        ]
    )
    res = analyze_pdf_bytes("skan_decyzja.pdf", scan_pdf)
    assert res.extracted_fields.ocr_used is True
    assert res.extracted_fields.ocr_required is False
    assert res.verification_status == "denied"
    assert res.sickness_insurance_status == "denied"
    assert res.suggested_insurance_title == "zlecenie"
    assert res.suggested_gross_salary is None


def test_multi_document_case_merge_and_conflict_detection():
    """Zestaw wielodokumentowy: ZAM (scenariusz + 81,5% + 2 dzieci) + Z-3 (UoP + zarobki + 45 ubezp.)."""
    zam_pdf = _make_text_pdf(
        [
            "WNIOSEK O ZASIŁEK MACIERZYŃSKI ZUS ZAM",
            "Urodzenie bliźniąt — liczba dzieci: 2",
            "Wariant wypłaty: 81,5%",
        ]
    )
    z3_pdf = _make_text_pdf(
        [
            "Zaświadczenie płatnika składek Z-3",
            "Ubezpieczenie chorobowe: TAK",
            "Liczba ubezpieczonych: 45",
            "Styczeń: 8 000,00 zł",
            "Luty: 8 000,00 zł",
        ]
    )
    case_res = analyze_case_documents([("ZAM.pdf", zam_pdf), ("Z-3.pdf", z3_pdf)])
    m = case_res.merged
    assert len(case_res.documents) == 2
    assert case_res.conflicts == []
    assert m.document_domain == "maternity_parental"
    assert m.suggested_insurance_title == "uop"
    assert m.verification_status == "verified"
    assert m.suggested_gross_salary == 8000.0
    assert m.extracted_fields.children_count == 2
    assert m.extracted_fields.payment_variant == "81_5"
    assert m.extracted_fields.employer_insured_count == 45

    # Endpoint HTTP /api/v1/documents/analyze-case
    r = client.post(
        "/api/v1/documents/analyze-case",
        files=[
            ("files", ("ZAM.pdf", zam_pdf, "application/pdf")),
            ("files", ("Z-3.pdf", z3_pdf, "application/pdf")),
        ],
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"]["suggested_gross_salary"] == 8000.0
    assert body["merged"]["extracted_fields"]["children_count"] == 2


def test_poswiadczenie_debt_nie_vs_tak():
    """Poświadczenie ZUS z zapisem '...figuruje zadłużenie ...: NIE' musi ustawiać has_contribution_debt=False."""
    pdf_no_debt = _make_text_pdf(
        [
            "Poświadczenie ubezpieczenia chorobowego",
            "8. Na koncie płatnika składek figuruje zadłużenie z tytułu składek na ubezpieczenia",
            "społeczne na datę badania, tj 2024-01-05: NIE",
        ]
    )
    res_no = analyze_pdf_bytes("posw_no_debt.pdf", pdf_no_debt)
    assert res_no.extracted_fields.has_contribution_debt is False
    assert res_no.extracted_fields.contribution_debt_pln == 0.0
    assert "Zadłużenie składek (art. 2a)" not in res_no.extracted_fields.key_extracted_fields

    pdf_with_debt = _make_text_pdf(
        [
            "Poświadczenie ubezpieczenia chorobowego",
            "8. Na koncie płatnika składek figuruje zadłużenie z tytułu składek na ubezpieczenia",
            "społeczne na datę badania, tj 2024-01-05: TAK",
        ]
    )
    res_yes = analyze_pdf_bytes("posw_with_debt.pdf", pdf_with_debt)
    assert res_yes.extracted_fields.has_contribution_debt is True

