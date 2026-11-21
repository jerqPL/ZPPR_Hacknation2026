from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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


def test_integrated_calculator_combined_81_5():
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "gross_monthly_salary": 7500.0,
            "payment_variant": "81_5",
            "father_takes_parental_weeks": 9,
            "father_takes_paternity_leave": True,
            "employer_insured_count": 50,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["eligible"] is True
    assert data["maternity_weeks"] == 20
    assert data["parental_weeks_total"] == 41.0
    assert data["paternity_weeks"] == 2
    assert data["total_estimated_gross_pln"] > 0


def test_integrated_calculator_premature_supplementary():
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "premature_or_hospitalized": True,
            "gestation_week": 27,
            "birth_weight_grams": 950,
            "hospitalization_weeks": 10,
            "gross_monthly_salary": 6500.0,
            "payment_variant": "100_70",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["supplementary_maternity_weeks"] == 10


def test_admin_parameters_get_and_reset():
    res = client.get("/api/v1/admin/parameters")
    assert res.status_code == 200
    params = res.json()
    assert params["year"] == 2026
    assert params["combined_21_days_rate"] == 0.815

    res_reset = client.post("/api/v1/admin/parameters/reset")
    assert res_reset.status_code == 200


def test_mobywatel_simulation_and_debt():
    login = client.post("/api/v1/auth/mobywatel/login", json={"persona_id": "jdg_with_debt"})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True

    debt = client.get("/api/v1/zus/debt/jdg_with_debt")
    assert debt.status_code == 200
    assert debt.json()["has_debt"] is True


def test_adoption_and_foster_family_rules_e_and_j():
    # 1. Rodzina zastępcza zawodowa -> wyłączona ustawowo (art. 183 § 1 KP)
    res_prof = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "foster_family_type": "professional",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "child_age_years": 4.0,
            "gross_monthly_salary": 7000.0,
        },
    )
    assert res_prof.status_code == 200
    assert res_prof.json()["eligible"] is False

    # 2. Rodzina zastępcza niezawodowa, dziecko 6,9 r.ż. -> reguła min. 9 tyg. + 38 tyg. rodzicielskiego (art. 183 § 3 i § 4 pkt 3 KP)
    res_foster_9 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "foster_family_type": "non_professional",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "child_age_years": 6.9,
            "gross_monthly_salary": 6800.0,
            "payment_variant": "81_5",
            "father_takes_parental_weeks": 9,
            "father_takes_paternity_leave": True,
        },
    )
    assert res_foster_9.status_code == 200
    data_f9 = res_foster_9.json()
    assert data_f9["eligible"] is True
    assert data_f9["maternity_weeks"] == 9
    assert data_f9["parental_weeks_total"] == 38.0
    # Urlop ojcowski nie przysługuje w rodzinie zastępczej
    assert data_f9["paternity_weeks"] == 0

    # 3. Adopcja dziecka powyżej 14 lat -> odmowa
    res_adopt_old = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "child_age_years": 14.5,
            "gross_monthly_salary": 7500.0,
        },
    )
    assert res_adopt_old.status_code == 200
    assert res_adopt_old.json()["eligible"] is False


def test_individual_benefit_base_calculator_f():
    # 1. Wyliczenie podstawy na JDG przy krótkim okresie ubezpieczenia (3 mies.) wg art. 48a ustawy zasiłkowej
    res_base = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "jdg",
            "mode": "jdg_art48a",
            "jdg_insured_months": 3,
            "jdg_declared_monthly_gross": 23550.0,
            "jdg_min_monthly_gross": 5652.0,
        },
    )
    assert res_base.status_code == 200
    base_data = res_base.json()
    assert base_data["computed_base_monthly"] == 8738.16

    # 2. Zastosowanie indywidualnej podstawy wymiaru w zintegrowanym kalkulatorze
    res_calc = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "has_sickness_insurance_on_birth_date": True,
            "children_count": 1,
            "gross_monthly_salary": 7500.0,
            "custom_benefit_base": 6903.20,
            "second_parent_gross_salary": 8200.0,
            "second_parent_custom_base": 7075.78,
            "payment_variant": "81_5",
        },
    )
    assert res_calc.status_code == 200
    calc_data = res_calc.json()
    assert calc_data["benefit_base_parent1"] == 6903.20
    assert calc_data["benefit_base_parent2"] == 7075.78
    assert "indywidualną podstawę" in calc_data["benefit_base_explanation"]

