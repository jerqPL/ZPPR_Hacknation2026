from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.services.pdf_parser_service import SAMPLE_CASES, analyze_pdf_bytes

client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-Key": settings.admin_api_key}


def test_healthcheck():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_pregnancy_benefit_uop_code_b():
    res = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "insurance_days": 180,
            "gross_monthly_salary": 7000.0,
            "has_code_b": True,
            "employer_insured_count": 30,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["eligible_sickness_benefit"] is True
    assert data["benefit_rate_percent"] == 100.0
    assert data["max_benefit_days"] == 270
    assert "Płatnik składek" in data["payer"]


def test_pregnancy_post_employment_art7_and_art46_cap():
    res = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "gross_monthly_salary": 18000.0,
            "has_code_b": True,
            "employment_terminated_special": True,
            "termination_reason": "post_employment_art7",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["eligible_sickness_benefit"] is True
    assert data["payer"] == "Zakład Ubezpieczeń Społecznych (ZUS)"
    # Cap: 9420 * (1 - 0.1371) = 8128.52
    assert abs(data["benefit_base_monthly"] - 8128.52) < 0.05


def test_waiting_period_10y_exemption_only_for_mandatory():
    res = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 20,
            "waiting_period_exempt": True,
            "gross_monthly_salary": 6000.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["waiting_period_met"] is False
    assert data["eligible_sickness_benefit"] is False


def test_individual_base_uncompleted_months_and_empty_error():
    # Empty list -> 422 instead of silent 7000
    empty_res = client.post(
        "/api/v1/calculator/benefit-base",
        json={"insurance_title": "uop", "mode": "uop_12m", "monthly_gross_salaries": []},
    )
    assert empty_res.status_code == 422

    # Exclude 1 lowest uncompleted month (2000) from [8000, 8000, 2000] -> avg 8000 -> 6903.20
    res = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "uop",
            "mode": "uop_12m",
            "monthly_gross_salaries": [8000.0, 8000.0, 2000.0],
            "uncompleted_months_excluded": 1,
        },
    )
    assert res.status_code == 200
    assert abs(res.json()["computed_base_monthly"] - 6903.20) < 0.02


def test_all_demo_cases_match_calculator_engine():
    for case in SAMPLE_CASES:
        res = client.post(
            "/api/v1/calculator/integrated",
            json={
                "scenario": case.scenario,
                "insurance_title": case.insurance_title,
                "has_sickness_insurance_on_birth_date": case.insured_on_event_date,
                "children_count": case.children_count,
                "child_age_years": case.child_age_years,
                "foster_family_type": case.foster_family_type,
                "foster_deferred_school": case.foster_deferred_school,
                "has_za_zyciem_certificate": case.has_za_zyciem,
                "gross_monthly_salary": case.gross_monthly_salary,
                "custom_benefit_base": case.custom_benefit_base,
                "second_parent_gross_salary": case.second_parent_gross_salary,
                "second_parent_custom_base": case.second_parent_custom_base,
                "payment_variant": case.payment_variant,
                "mother_maternity_weeks": case.mother_maternity_weeks,
                "father_takes_parental_weeks": case.father_takes_parental_weeks,
                "father_takes_paternity_leave": case.father_takes_paternity_leave,
                "employer_insured_count": case.employer_insured_count,
            },
        )
        assert res.status_code == 200, f"Case {case.case_id} failed HTTP"
        data = res.json()
        assert data["eligible"] is case.expected_eligible, f"Case {case.case_id} eligibility mismatch"
        if case.expected_base_parent1 is not None:
            assert abs(data["benefit_base_parent1"] - case.expected_base_parent1) < 0.05


def test_single_parent_father_work_combination_and_art31_equalization():
    # Single parent with 81.5% and 0 parental weeks -> equalization to 100% calculated
    res_eq = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "single_parent_or_no_second_parent": True,
            "gross_monthly_salary": 7500.0,
            "payment_variant": "81_5",
            "mother_takes_parental_weeks": 0,
            "father_takes_parental_weeks": 0,
        },
    )
    assert res_eq.status_code == 200
    d_eq = res_eq.json()
    assert d_eq["equalization_to_100_pln"] > 0
    assert d_eq["benefit_base_parent2"] == 0.0

    # Second parent combines parental leave with work (0.5 FTE for 4 weeks)
    res_f = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
            "gross_monthly_salary": 7000.0,
            "second_parent_gross_salary": 9000.0,
            "father_takes_parental_weeks": 9,
            "father_combine_parental_with_work": True,
            "father_work_fte_fraction": 0.5,
            "father_combined_work_weeks": 4,
            "father_work_during_extended_part": False,
        },
    )
    assert res_f.status_code == 200
    d_f = res_f.json()
    assert d_f["parental_weeks_extended_by_work"] == 2.0


def test_pdf_parser_word_boundaries_and_needs_review():
    # Invalid/empty PDF bytes -> needs_review, never falsely verified
    res_scan = analyze_pdf_bytes("scan.pdf", b"not-a-pdf-scan")
    assert res_scan.verification_status == "needs_review"
    assert res_scan.insurance_verified is False
    assert res_scan.extracted_fields.ocr_required is True

    # ERU filename fallback recognizes ERU form cleanly
    res_eru = analyze_pdf_bytes("ERU_do wydruku.pdf", b"not-a-pdf")
    assert "ERU" in res_eru.detected_forms
    assert res_eru.extracted_fields.form_type == "ERU"
    assert res_eru.suggested_insurance_title == "none"

    # Verify word-boundary pattern doesn't match "zamówienie" as ZAM, while matching real ZUS codes
    from app.services.pdf_parser_service import _FORM_PATTERNS

    sample = "Dokument zamówienia ubezpieczenia społecznego"
    matched = [code for code, pat in _FORM_PATTERNS if pat.search(sample)]
    assert "ZAM" not in matched

    for code_text, expected in [
        ("Formularz ZUS ZAM wniosek o zasiłek", "ZAM"),
        ("Zaświadczenie Z-3a dla zleceniobiorcy", "Z-3A"),
        ("Oświadczenie ERU Mama 4+", "ERU"),
        ("Wniosek ZNP-7 o świadczenie rehabilitacyjne", "ZNP-7"),
        ("Wniosek Z-15A zasiłek opiekuńczy", "Z-15A"),
    ]:
        hits = [c for c, pat in _FORM_PATTERNS if pat.search(code_text)]
        assert expected in hits, f"Expected {expected} in {hits}"


def test_admin_auth_and_reset():
    # Unauthorized without X-Admin-Key
    unauth = client.post("/api/v1/admin/parameters/reset")
    assert unauth.status_code == 401

    # Authorized with X-Admin-Key
    get_res = client.get("/api/v1/admin/parameters")
    assert get_res.status_code == 200
    params = get_res.json()
    params["combined_21_days_rate"] = 0.85

    put_res = client.put("/api/v1/admin/parameters", json=params, headers=ADMIN_HEADERS)
    assert put_res.status_code == 200
    assert put_res.json()["combined_21_days_rate"] == 0.85

    reset_res = client.post("/api/v1/admin/parameters/reset", headers=ADMIN_HEADERS)
    assert reset_res.status_code == 200
    assert reset_res.json()["combined_21_days_rate"] == 0.815


def test_persona_404_and_application_deadline():
    not_found = client.get("/api/v1/zus/profile/nonexistent_user")
    assert not_found.status_code == 404

    sub = client.post(
        "/api/v1/documents/submit",
        json={
            "application_type": "leave_employer",
            "applicant_name": "Anna Kowalska",
            "pesel_masked": "920514*****",
            "child_birth_date": "2026-11-01",
            "leave_start_date": "2026-11-01",
            "payment_variant": "81_5",
            "recipient": "Pracodawca",
        },
    )
    assert sub.status_code == 200
    data = sub.json()
    assert data["deadline_21_days"] == "2026-11-22"
    assert "WNIOSEK O UDZIELENIE URLOPU" in data["generated_document_text"]

    pdf_res = client.post(
        "/api/v1/documents/pdf",
        json={
            "application_type": "leave_employer",
            "applicant_name": "Anna Kowalska",
            "pesel_masked": "920514*****",
            "child_birth_date": "2026-11-01",
            "leave_start_date": "2026-11-01",
            "payment_variant": "81_5",
            "recipient": "Pracodawca",
        },
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")
