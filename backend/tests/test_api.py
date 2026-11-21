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
