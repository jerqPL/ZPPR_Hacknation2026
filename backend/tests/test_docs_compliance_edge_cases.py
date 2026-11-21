import io
from pathlib import Path
from fastapi.testclient import TestClient
from fpdf import FPDF
from app.config import settings
from app.main import app
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


# =============================================================================
# 1. ŁĄCZENIE URLOPU RODZICIELSKIEGO Z PRACĄ (ART. 182^1e, 182^1f KP, ART. 31 UST. 4a)
# =============================================================================


def test_work_combination_with_zero_extension_days_still_reduces_benefit():
    # Przypadek A: 1 tydzień na 0,1 etatu bez pracy w wydłużeniu -> 1 * 7 * 0,1 = 0,7 dnia -> floor = 0 dni (art. 182^1f § 4 KP),
    # ale zasiłek za ten 1 tydzień MUSI zostać proporcjonalnie pomniejszony o 10% (art. 31 ust. 4a ustawy zasiłkowej)!
    r = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "gross_monthly_salary": 10000.0,
            "payment_variant": "100_70",
            "father_takes_parental_weeks": 9,
            "father_takes_paternity_leave": False,
            "combine_parental_with_work": True,
            "work_fte_fraction": 0.1,
            "combined_work_weeks": 1,
            "work_during_extended_part": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["parental_weeks_extended_by_work"] == 0.0
    assert data["parental_weeks_total"] == 41.0
    combined_items = [b for b in data["breakdown"] if "łączony z pracą" in b["label"]]
    assert len(combined_items) == 1
    assert combined_items[0]["days"] == 7
    assert combined_items[0]["rate_percent"] == 63.0  # 70% * (1 - 0.1)
    assert not any("Wydłużona część" in b["label"] for b in data["breakdown"])

    # Przypadek B: Adopcja w wieku 13.0 r.ż. (52 tyg. do 14. r.ż., 20 mat + 32 rodz = 52 -> 0 dni dostępnego wydłużenia)
    # Mimo 0 dni wydłużenia, 10 tyg. łączonych z pracą na 0,5 etatu nadal ma pomniejszony zasiłek o 50%!
    r_ad = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.0,
            "insurance_title": "uop",
            "gross_monthly_salary": 10000.0,
            "payment_variant": "100_70",
            "father_takes_parental_weeks": 0,
            "father_takes_paternity_leave": False,
            "combine_parental_with_work": True,
            "work_fte_fraction": 0.5,
            "combined_work_weeks": 10,
            "work_during_extended_part": True,
        },
    )
    assert r_ad.status_code == 200
    d_ad = r_ad.json()
    assert d_ad["total_weeks"] == 52.0
    assert d_ad["parental_weeks_extended_by_work"] == 0.0
    ad_combined = [b for b in d_ad["breakdown"] if "łączony z pracą" in b["label"]]
    assert len(ad_combined) == 1
    assert ad_combined[0]["days"] == 70
    assert ad_combined[0]["rate_percent"] == 35.0  # 70% * (1 - 0.5)


def test_work_combination_rejected_for_non_uop_titles():
    for title in ("jdg", "zlecenie"):
        r = client.post(
            "/api/v1/calculator/integrated",
            json={
                "scenario": "birth",
                "insurance_title": title,
                "gross_monthly_salary": 8000.0,
                "combine_parental_with_work": True,
                "work_fte_fraction": 0.5,
                "combined_work_weeks": 10,
                "work_during_extended_part": True,
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["parental_weeks_extended_by_work"] == 0.0
        assert not any("łączony z pracą" in b["label"] for b in d["breakdown"])
        assert any("182¹ᵉ" in w for w in d["warnings"])


def test_work_combination_statutory_max_caps_art182_1f():
    # Art. 182^1f § 1 i § 1^1 KP: maks. 82 (1 dz.), 86 (2+ dz.), 130 (1 dz. Za życiem), 134 (2+ dz. Za życiem)
    cases = [
        (1, False, 32, 9, 82.0),
        (2, False, 34, 9, 86.0),
        (1, True, 56, 9, 130.0),
        (2, True, 58, 9, 134.0),
    ]
    for kids, za_zyciem, m_par, f_par, expected_total_parental in cases:
        r = client.post(
            "/api/v1/calculator/integrated",
            json={
                "scenario": "birth",
                "children_count": kids,
                "has_za_zyciem_certificate": za_zyciem,
                "insurance_title": "uop",
                "second_parent_insurance_title": "uop",
                "gross_monthly_salary": 7500.0,
                "mother_takes_parental_weeks": m_par,
                "father_takes_parental_weeks": f_par,
                "father_takes_paternity_leave": False,
                "combine_parental_with_work": True,
                "work_fte_fraction": 0.5,
                "combined_work_weeks": m_par,
                "work_during_extended_part": True,
                "father_combine_parental_with_work": True,
                "father_work_fte_fraction": 0.5,
                "father_combined_work_weeks": f_par,
                "father_work_during_extended_part": True,
            },
        )
        assert r.status_code == 200
        d = r.json()
        assert d["parental_weeks_total"] == expected_total_parental


# =============================================================================
# 2. ADOPCJA I RODZINA ZASTĘPCZA — GRANICE WIEKU, 9 TYG., PODZIAŁ, UZUPEŁNIAJĄCY, OJCOWSKI
# =============================================================================


def test_foster_age_boundaries_with_and_without_school_deferral():
    # 6.99 bez odroczenia -> 9 + 38
    r_699 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 6.99,
            "foster_deferred_school": False,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_699["eligible"] is True
    assert r_699["maternity_weeks"] == 9
    assert r_699["parental_weeks_total"] == 38.0

    # 7.0 bez odroczenia -> odmowa
    r_70 = client.post(
        "/api/v1/calculator/integrated",
        json={"scenario": "foster", "child_age_years": 7.0, "foster_deferred_school": False},
    ).json()
    assert r_70["eligible"] is False

    # 7.0 z odroczeniem -> uprawniona (limit 10 lat: 20 + 41)
    r_70_def = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 7.0,
            "foster_deferred_school": True,
            "father_takes_parental_weeks": 9,
        },
    ).json()
    assert r_70_def["eligible"] is True
    assert r_70_def["maternity_weeks"] == 20
    assert r_70_def["parental_weeks_total"] == 41.0

    # 9.9 z odroczeniem -> 9 + 38
    r_99_def = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 9.9,
            "foster_deferred_school": True,
            "father_takes_parental_weeks": 9,
        },
    ).json()
    assert r_99_def["eligible"] is True
    assert r_99_def["maternity_weeks"] == 9
    assert r_99_def["parental_weeks_total"] == 38.0

    # 10.0 z odroczeniem -> odmowa
    r_10_def = client.post(
        "/api/v1/calculator/integrated",
        json={"scenario": "foster", "child_age_years": 10.0, "foster_deferred_school": True},
    ).json()
    assert r_10_def["eligible"] is False


def test_exact_9_weeks_boundary_vs_under_9_weeks_and_za_zyciem():
    # Przy dokładnie 9 pełnych tyg. do 7. urodzin (floor((7 - 6.8178) * 52.14) == 9):
    # przysługuje 9 tyg. z art. 183 § 1 KP i PEŁNE 41 tyg. rodzicielskiego z art. 183 § 4 pkt 1 KP (NIE 38!).
    r_exact_9 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 6.8178,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_exact_9["maternity_weeks"] == 9
    assert r_exact_9["parental_weeks_total"] == 41.0

    # Przy 8 tyg. do 7. urodzin (floor((7 - 6.8370) * 52.14) == 8 < 9):
    # wchodzi tryb minimalny art. 183 § 3 KP -> 9 tyg. + 38 tyg. rodzicielskiego (a z Za życiem -> 9 + 62 tyg.)
    r_8 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 6.837,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_8["maternity_weeks"] == 9
    assert r_8["parental_weeks_total"] == 38.0

    r_8_zz = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.837,
            "has_za_zyciem_certificate": True,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_8_zz["maternity_weeks"] == 9
    assert r_8_zz["parental_weeks_total"] == 62.0

    # Sprawdzenie tej samej granicy 9 tyg. w gałęzi nieubezpieczonej matki (art. 31 ust. 3h)
    r_u9 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 6.8178,
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_gross_salary": 7000.0,
        },
    ).json()
    assert r_u9["parental_weeks_total"] == 32.0  # 41 - 9

    r_u8 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 6.837,
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_gross_salary": 7000.0,
        },
    ).json()
    assert r_u8["parental_weeks_total"] == 29.0  # 38 - 9


def test_adoption_foster_maternity_split_enforces_min_14_weeks_except_zero():
    # mother_maternity_weeks=0 -> Rodzic 2 przejmuje całość od 1. dnia (dozwolone przy adopcji/pieczy)
    r_zero = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 2.0,
            "mother_maternity_weeks": 0,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    mat_items_zero = [b for b in r_zero["breakdown"] if "warunkach" in b["label"]]
    assert len(mat_items_zero) == 1
    assert mat_items_zero[0]["parent"] == "Rodzic adopcyjny 2"
    assert mat_items_zero[0]["weeks"] == 20.0

    # mother_maternity_weeks=5 z 20 -> korekta do 14 + 6 (art. 183 § 2 w zw. z art. 180 § 4 KP)
    r_five = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 2.0,
            "mother_maternity_weeks": 5,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    mat_items_five = [b for b in r_five["breakdown"] if "warunkach" in b["label"]]
    assert [(m["parent"], m["weeks"]) for m in mat_items_five] == [
        ("Rodzic adopcyjny 1", 14.0),
        ("Rodzic adopcyjny 2", 6.0),
    ]
    assert any("183 § 2" in w for w in r_five["warnings"])

    # mother_maternity_weeks=14 -> dozwolone bez korekty
    r_14 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 2.0,
            "mother_maternity_weeks": 14,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    mat_items_14 = [b for b in r_14["breakdown"] if "warunkach" in b["label"]]
    assert [(m["parent"], m["weeks"]) for m in mat_items_14] == [
        ("Rodzic zastępczy 1 (niezawodowy)", 14.0),
        ("Rodzic zastępczy 2 (niezawodowy)", 6.0),
    ]
    assert not any("Skorygowano wymiar Rodzica 1" in w for w in r_14["warnings"])


def test_supplementary_leave_for_adoption_foster_respects_post_birth_window_art183_3_1():
    # Dziecko 3-letnie przyjęte do adopcji -> hospitalizacja po przyjęciu nie mieści się w 8./15. tyg. po porodzie -> 0 tyg.
    r_old = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 3.0,
            "premature_or_hospitalized": True,
            "gestation_week": 26,
            "birth_weight_grams": 900,
            "hospitalization_weeks": 10,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_old["supplementary_maternity_weeks"] == 0
    assert any("183 § 3¹" in w and "15. tygodnia po porodzie" in w for w in r_old["warnings"])

    # Noworodek przyjęty w wieku 0.05 roku (~2,6 tyg.), limit 8 tyg. -> maksymalnie ceil(8 - 2.607) = 6 tyg.
    r_newborn = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 0.05,
            "premature_or_hospitalized": True,
            "gestation_week": 32,
            "birth_weight_grams": 1800,
            "hospitalization_weeks": 8,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_newborn["supplementary_maternity_weeks"] == 6


def test_paternity_for_foster_and_adoption_age_14_boundary():
    # Rodzina zastępcza -> urlop ojcowski 0 + ostrzeżenie
    r_foster = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "child_age_years": 2.0,
            "father_takes_paternity_leave": True,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_foster["paternity_weeks"] == 0
    assert any("rodziny zastępczej" in w for w in r_foster["warnings"])

    # Adopcja 13.99 r.ż. -> ojcowski ograniczony do 1 tyg. (granica 14 r.ż.)
    r_ad_1399 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 13.99,
            "father_takes_paternity_leave": True,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_ad_1399["eligible"] is True
    assert r_ad_1399["paternity_weeks"] == 1

    # Adopcja 14.0 r.ż. -> odmowa
    r_ad_14 = client.post(
        "/api/v1/calculator/integrated",
        json={"scenario": "adoption", "child_age_years": 14.0, "gross_monthly_salary": 7000.0},
    ).json()
    assert r_ad_14["eligible"] is False


# =============================================================================
# 3. UZUPEŁNIAJĄCY URLOP MACIERZYŃSKI — GRANICE ART. 180^2 KP
# =============================================================================


def test_supplementary_maternity_statutory_boundaries_and_100_percent_rate():
    # 27 tydz. (>1000 g) -> maks. 15 tyg. i stawka 100% nawet w wariancie 81_5
    r27 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "payment_variant": "81_5",
            "premature_or_hospitalized": True,
            "gestation_week": 27,
            "birth_weight_grams": 1400,
            "hospitalization_weeks": 20,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r27["supplementary_maternity_weeks"] == 15
    supp_row = [b for b in r27["breakdown"] if "Uzupełniający" in b["label"]][0]
    assert supp_row["rate_percent"] == 100.0

    # 28 tydz. (>1000 g) -> maks. 8 tyg.
    r28 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 28,
            "birth_weight_grams": 1400,
            "hospitalization_weeks": 20,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r28["supplementary_maternity_weeks"] == 8

    # 38 tydz. ale masa dokładnie 1000 g -> maks. 15 tyg. (warunek z pkt 1, nie pkt 3!)
    r_1000g = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 38,
            "birth_weight_grams": 1000,
            "hospitalization_weeks": 15,
            "full_term_hospitalization_condition_met": False,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_1000g["supplementary_maternity_weeks"] == 15

    # 36 tydz. (>1000 g) z full_term_hospitalization_condition_met=False -> nadal do 8 tyg. (pkt 2 nie wymaga 5.–28. dnia!)
    r36 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 36,
            "birth_weight_grams": 2400,
            "hospitalization_weeks": 8,
            "full_term_hospitalization_condition_met": False,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r36["supplementary_maternity_weeks"] == 8


# =============================================================================
# 4. MARTWE URODZENIE, PORÓD MNOGI, URLOP PRZED PORODEM I PRZEJĘCIE PO 8 TYG.
# =============================================================================


def test_stillbirth_with_pre_birth_triplets_loss_and_early_transfer_8w():
    # Martwe urodzenie 1 dziecka z 4 tyg. przed porodem -> nadal gwarantowane 8 tyg. po porodzie, 0 rodz./ojc./uzup.
    r_sb = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "children_count": 1,
            "stillbirth_or_early_death": True,
            "pre_birth_maternity_weeks": 4,
            "premature_or_hospitalized": True,
            "hospitalization_weeks": 5,
            "father_takes_parental_weeks": 9,
            "father_takes_paternity_leave": True,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_sb["maternity_weeks"] == 8
    assert r_sb["parental_weeks_total"] == 0.0
    assert r_sb["supplementary_maternity_weeks"] == 0
    assert r_sb["paternity_weeks"] == 0
    assert any("4 tyg." in w for w in r_sb["warnings"])

    # Trojaczki z 1 zgonem -> wymiar dla 2 żywych (31 tyg. macierzyńskiego + 43 tyg. rodzicielskiego)
    r_trip = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "children_count": 3,
            "stillbirth_or_early_death": True,
            "father_takes_parental_weeks": 9,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_trip["maternity_weeks"] == 31
    assert r_trip["parental_weeks_total"] == 43.0

    # Wcześniejsze przejęcie po 8 tyg. + 2 tyg. przed porodem -> matka min. 10 tyg., ojciec maks. 10 tyg.
    r_early = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "children_count": 1,
            "mother_early_transfer_8_weeks": True,
            "pre_birth_maternity_weeks": 2,
            "mother_maternity_weeks": 8,
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    mat_rows = [b for b in r_early["breakdown"] if "macierzyńskiego" in b["label"] or b["label"] == "Urlop macierzyński"]
    assert [(m["parent"], m["weeks"]) for m in mat_rows] == [("Matka", 10.0), ("Ojciec", 10.0)]


# =============================================================================
# 5. PROGI FINANSOWE, PŁATNIK, CIĄŻA I KREATOR PODSTAWY WYMIARU
# =============================================================================


def test_payer_boundary_and_pregnancy_special_cases():
    # Granica płatnika art. 61 ust. 1: 20 -> ZUS, 21 -> Płatnik składek, JDG zawsze ZUS
    p20 = client.post(
        "/api/v1/calculator/integrated",
        json={"insurance_title": "uop", "employer_insured_count": 20, "gross_monthly_salary": 7000.0},
    ).json()
    p21 = client.post(
        "/api/v1/calculator/integrated",
        json={"insurance_title": "uop", "employer_insured_count": 21, "gross_monthly_salary": 7000.0},
    ).json()
    p_jdg = client.post(
        "/api/v1/calculator/integrated",
        json={"insurance_title": "jdg", "employer_insured_count": 100, "gross_monthly_salary": 7000.0},
    ).json()
    assert "ZUS" in p20["payer"]
    assert "Płatnik" in p21["payer"]
    assert "ZUS" in p_jdg["payer"]

    # PregnancyBenefitRequest: employment_terminated_special=True bez termination_reason -> HTTP 422
    r_missing = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "uop", "employment_terminated_special": True, "gross_monthly_salary": 7000.0},
    )
    assert r_missing.status_code == 422

    # Śmierć pracodawcy na UoP -> zasiłek w wysokości macierzyńskiego do dnia porodu (art. 30 ust. 3)
    r_death = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "employment_terminated_special": True,
            "termination_reason": "employer_death",
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_death["eligible_maternity_equivalent"] is True
    assert r_death["benefit_rate_percent"] == 100.0

    # Wyrok sądu dot. nielegalnego wypowiedzenia na zleceniu -> odmowa (dotyczy tylko pracownic UoP)
    r_zlec = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "zlecenie",
            "employment_terminated_special": True,
            "termination_reason": "unlawful_termination_court_ruling",
            "gross_monthly_salary": 7000.0,
        },
    ).json()
    assert r_zlec["eligible_sickness_benefit"] is False
    assert r_zlec["eligible_maternity_equivalent"] is False
    assert r_zlec["eligible_post_birth_maternity_art30"] is False

    # post_employment_art7 na JDG z zadłużeniem > 48,06 zł -> payout_suspended_due_to_debt=True
    r_art7_debt = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "insurance_days": 120,
            "employment_terminated_special": True,
            "termination_reason": "post_employment_art7",
            "gross_monthly_salary": 8000.0,
            "contribution_debt_pln": 120.0,
        },
    ).json()
    assert r_art7_debt["eligible_sickness_benefit"] is True
    assert r_art7_debt["payout_suspended_due_to_debt"] is True


def test_individual_benefit_base_edge_cases_and_art31_3a_with_work():
    # insurance_title=none -> HTTP 422
    assert (
        client.post(
            "/api/v1/calculator/benefit-base",
            json={"insurance_title": "none", "mode": "uop_12m", "monthly_gross_salaries": [5000.0]},
        ).status_code
        == 422
    )

    # nieznany mode -> HTTP 422
    assert (
        client.post(
            "/api/v1/calculator/benefit-base",
            json={"insurance_title": "uop", "mode": "unknown_mode", "monthly_gross_salaries": [5000.0]},
        ).status_code
        == 422
    )

    # jdg_art48a z 12 mies. i deklaracją 0 -> fallback do min_net (floor_applied=True)
    r_jdg0 = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "jdg",
            "mode": "jdg_art48a",
            "jdg_insured_months": 12,
            "jdg_declared_monthly_gross": 0.0,
        },
    ).json()
    assert r_jdg0["floor_applied"] is True
    assert abs(r_jdg0["computed_base_monthly"] - round(5652.0 * 0.8629, 2)) < 0.02

    # uop_12m z uncompleted_months_excluded >= len(salaries) -> art. 38 ust. 3 zachowuje wszystkie miesiące
    r_all_excl = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "uop",
            "mode": "uop_12m",
            "monthly_gross_salaries": [6000.0, 6000.0],
            "uncompleted_months_excluded": 2,
        },
    ).json()
    assert abs(r_all_excl["computed_base_monthly"] - round(6000.0 * 0.8629, 2)) < 0.02
    assert any("art. 38 ust. 3" in s for s in r_all_excl["explanation_steps"])

    # Limit 250% przeciętnego wynagrodzenia dla zlecenia (23 550 -> 20 321,30 zł)
    r_cap = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "zlecenie",
            "mode": "uop_12m",
            "monthly_gross_salaries": [30000.0] * 12,
        },
    ).json()
    assert r_cap["cap_applied"] is True
    assert abs(r_cap["computed_base_monthly"] - round(23550.0 * (1.0 - 0.1371), 2)) < 0.02

    # Niepełny etat 0,25 na UoP -> proporcjonalne minimum z art. 45 ustawy zasiłkowej
    r_fte = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "uop",
            "mode": "uop_12m",
            "monthly_gross_salaries": [1000.0] * 12,
            "fte_fraction": 0.25,
        },
    ).json()
    assert r_fte["floor_applied"] is True
    assert abs(r_fte["computed_base_monthly"] - round(4806.0 * 0.25 * 0.8629, 2)) < 0.02

    # Art. 31 ust. 3a + łączenie z pracą na 0,5 etatu -> proporcjonalny próg 500 zł/mies.
    r_topup = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "fte_fraction": 0.1,
            "custom_benefit_base": 500.0,
            "payment_variant": "100_70",
            "father_takes_parental_weeks": 0,
            "father_takes_paternity_leave": False,
            "combine_parental_with_work": True,
            "work_fte_fraction": 0.5,
            "combined_work_weeks": 10,
            "work_during_extended_part": True,
        },
    ).json()
    assert r_topup["minimum_benefit_top_up_applied"] is True
    work_row = [b for b in r_topup["breakdown"] if "łączony z pracą" in b["label"]][0]
    assert work_row["monthly_gross_pln"] == 500.0


# =============================================================================
# 6. DOKUMENTY, RYZYKA ART. 17 (2026), SYMULACJE ZUS/PUE I PARSER PDF
# =============================================================================


def test_updated_document_citations_and_7_day_z3_deadline():
    # Termin 7 dni dla Z-3 i Z-3a u małego płatnika (art. 61b ust. 5 ustawy zasiłkowej)
    g_uop = client.get("/api/v1/documents/guidance", params={"insurance_title": "uop", "employer_insured_count": 10}).json()
    z3 = [d for d in g_uop["documents"] if d["form_code"] == "Z-3"][0]
    assert "7 dni" in z3["deadline"] and "61b ust. 5" in z3["deadline"]

    g_zlec = client.get("/api/v1/documents/guidance", params={"insurance_title": "zlecenie", "employer_insured_count": 10}).json()
    z3a = [d for d in g_zlec["documents"] if d["form_code"] == "Z-3a"][0]
    assert "7 dni" in z3a["deadline"] and "61b ust. 5" in z3a["deadline"]

    # Weryfikacja poprawionych cytatów i obowiązkowych elementów rozporządzenia Dz.U. 2025 poz. 322
    base = {
        "applicant_name": "Anna Kowalska",
        "pesel_masked": "920514*****",
        "child_birth_date": "2026-11-20",
        "leave_start_date": "2026-11-20",
        "leave_end_date": "2027-05-20",
        "recipient": "Pracodawca",
    }
    pre = client.post("/api/v1/documents/submit", json={**base, "application_type": "leave_pre_birth"}).json()
    assert "§ 2 ust. 2" in pre["generated_document_text"]
    assert "§ 2 pkt 1" not in pre["generated_document_text"]

    emp = client.post("/api/v1/documents/submit", json={**base, "application_type": "leave_employer"}).json()
    assert "§ 15 ust. 1 pkt 2" in emp["generated_document_text"]
    assert "§ 15 ust. 2 pkt 3" in emp["generated_document_text"]

    ft = client.post("/api/v1/documents/submit", json={**base, "application_type": "leave_father_takeover"}).json()
    assert "imię i nazwisko" in ft["generated_document_text"]
    assert "§ 5 ust. 1 pkt 3" in ft["generated_document_text"]

    ad = client.post("/api/v1/documents/submit", json={**base, "application_type": "leave_adoption_foster"}).json()
    assert "imię i nazwisko" in ad["generated_document_text"]
    assert "art. 183 § 6 KP" in ad["generated_document_text"]
    assert "starostą" in ad["generated_document_text"]

    pat = client.post("/api/v1/documents/submit", json={**base, "application_type": "leave_paternity"}).json()
    assert "14. roku życia" in pat["generated_document_text"]
    assert "182³ § 1 KP" in pat["generated_document_text"]


def test_guidance_art17_2026_charitable_only_and_required_official_links():
    risks = client.get("/api/v1/guidance/risks").json()
    art17 = [r for r in risks if r["id"] == "wykorzystywanie_ezla_art17"][0]
    assert "17 ust. 1a" in art17["description"]
    assert "incydentalne" in art17["description"]
    assert "polecenie pracodawcy" in art17["description"]

    orgs = client.get("/api/v1/guidance/support-organizations").json()
    assert len(orgs) >= 3
    assert all(o["charitable_only"] is True for o in orgs)

    links = client.get("/api/v1/guidance/official-links").json()
    urls = [l["url"] for l in links]
    for required_host in (
        "zus.pl",
        "gov.pl/web/rodzina/urlop-rodzicielski",
        "pip.gov.pl/dla-pracodawcow/porady-prawne/rodzicielstwo",
        "gov.pl/web/cyfryzacja/rejestr-stanu-cywilnego",
    ):
        assert any(required_host in u for u in urls), f"Brak wymaganego linku: {required_host}"


def test_simulation_endpoints_personas_ezla_debt_admin_sync_and_pue_inquiry():
    personas = client.get("/api/v1/auth/personas").json()
    assert len(personas) >= 4
    login = client.post("/api/v1/auth/mobywatel/login", json={"persona_id": "uop_standard"}).json()
    assert login["authenticated"] is True
    assert login["profile"]["id"] == "uop_standard"

    ezla = client.get("/api/v1/zus/ezla/uop_standard").json()
    assert len(ezla) >= 1 and ezla[0]["letter_code"] == "B"

    # Reakcja statusu zadłużenia na zmianę płacy minimalnej w panelu administracyjnym
    params = client.get("/api/v1/admin/parameters").json()
    try:
        mod = {**params, "minimum_wage_gross": 200000.0}  # próg 1% = 2000 zł > 1842.50 zł
        assert client.put("/api/v1/admin/parameters", json=mod, headers=ADMIN_HEADERS).status_code == 200
        debt_under = client.get("/api/v1/zus/debt/jdg_with_debt").json()
        assert "nie przekracza progu" in debt_under["impact_warning"]
    finally:
        client.post("/api/v1/admin/parameters/reset", headers=ADMIN_HEADERS)

    debt_over = client.get("/api/v1/zus/debt/jdg_with_debt").json()
    assert debt_over["has_debt"] is True
    assert "wstrzymuje to wypłatę" in debt_over["impact_warning"]

    # PUE/eZUS inquiry: 200, 422 (walidacja), 404 (nieznana persona)
    ok_inq = client.post(
        "/api/v1/zus/pue/inquiry",
        json={
            "persona_id": "uop_standard",
            "category": "zasiłek macierzyński",
            "subject": "Pytanie o termin 21 dni",
            "message": "Proszę o potwierdzenie terminu złożenia wniosku.",
        },
    )
    assert ok_inq.status_code == 200
    assert ok_inq.json()["ticket_id"].startswith("PUE-")

    assert (
        client.post(
            "/api/v1/zus/pue/inquiry",
            json={"persona_id": "uop_standard", "subject": "a", "message": "ok"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/zus/pue/inquiry",
            json={
                "persona_id": "nieistniejaca",
                "subject": "Pytanie testowe",
                "message": "Treść pytania testowego do ZUS.",
            },
        ).status_code
        == 404
    )


def test_pdf_parser_dates_dot_thousands_3digit_z3b_phrases_and_upload_limits():
    # Data 2026.11.20 NIE może być odczytana jako wynagrodzenie 2026.11, natomiast 7.500,50 i 950,00 muszą być odczytane!
    pdf_amounts = _make_text_pdf(
        [
            "Zaświadczenie Z-3 wystawione dnia 2026.11.20",
            "Styczeń: 7.500,50 zł",
            "Luty: 950,00 zł",
        ]
    )
    res_amt = analyze_pdf_bytes("z3_dates.pdf", pdf_amounts)
    assert res_amt.extracted_fields.extracted_amounts == [7500.5, 950.0]

    # Archiwalny formularz Z-3B -> suggested_insurance_title == "jdg"
    pdf_z3b = _make_text_pdf(["Zaświadczenie płatnika składek Z-3b", "Przychód: 6 200,00 zł"])
    res_z3b = analyze_pdf_bytes("Z-3b.pdf", pdf_z3b)
    assert res_z3b.extracted_fields.form_type == "Z-3B"
    assert res_z3b.suggested_insurance_title == "jdg"

    # Poświadczenia: "Objęta ubezpieczeniem chorobowym" -> verified, "Nie jest objęta ubezpieczeniem chorobowym" -> denied
    pdf_ver = _make_text_pdf(["Zaświadczenie Z-3a", "Ubezpieczona jest objęta dobrowolnym ubezpieczeniem chorobowym."])
    assert analyze_pdf_bytes("posw_ok.pdf", pdf_ver).verification_status == "verified"

    pdf_den = _make_text_pdf(["Zaświadczenie Z-3a", "Osoba nie jest objęta ubezpieczeniem chorobowym."])
    assert analyze_pdf_bytes("posw_no.pdf", pdf_den).verification_status == "denied"

    # Walidacja uploadu HTTP: nie-PDF -> 400, >10 MB -> 400
    r_txt = client.post(
        "/api/v1/documents/analyze-pdf",
        files={"file": ("notatka.txt", b"hello", "text/plain")},
    )
    assert r_txt.status_code == 400

    r_big = client.post(
        "/api/v1/documents/analyze-pdf",
        files={"file": ("big.pdf", b"%PDF-1.4\n" + b"0" * (10 * 1024 * 1024 + 16), "application/pdf")},
    )
    assert r_big.status_code == 400
