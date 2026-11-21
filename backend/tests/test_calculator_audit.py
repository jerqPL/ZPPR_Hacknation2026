from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =============================================================================
# 1. ZAKŁADKA CIĄŻA (/api/v1/calculator/pregnancy)
# =============================================================================


def test_pregnancy_uop_part_time_min_base_art45_and_over50():
    # 0.5 etatu, 2000 zł brutto -> 2000 * 0.8629 = 1725.80 < min dla 0.5 etatu (4806 * 0.5 * 0.8629 = 2073.55)
    res = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "insurance_days": 60,
            "gross_monthly_salary": 2000.0,
            "fte_fraction": 0.5,
            "has_code_b": True,
            "age_over_50": True,
            "employer_insured_count": 25,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["eligible_sickness_benefit"] is True
    assert abs(d["benefit_base_monthly"] - 2073.55) < 0.02
    assert d["employer_pay_days"] == 14
    assert any("art. 92 § 5" in w for w in d["warnings"])


def test_pregnancy_without_code_b_pays_80_and_warns_equalization():
    res = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "insurance_days": 40,
            "gross_monthly_salary": 6000.0,
            "has_code_b": False,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert d["benefit_rate_percent"] == 80.0
    assert abs(d["monthly_benefit_gross"] - round(6000 * 0.8629 * 0.8, 2)) < 0.02
    assert any("wyrównanie do 100%" in w for w in d["warnings"])


def test_pregnancy_waiting_period_boundaries_and_art4_ust3_exemptions():
    # UoP 29 dni -> brak; 30 dni -> jest
    r29 = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "uop", "insurance_days": 29, "gross_monthly_salary": 6000.0},
    ).json()
    assert r29["waiting_period_met"] is False
    assert r29["eligible_sickness_benefit"] is False

    r30 = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "uop", "insurance_days": 30, "gross_monthly_salary": 6000.0},
    ).json()
    assert r30["waiting_period_met"] is True
    assert r30["eligible_sickness_benefit"] is True

    # JDG 89 dni -> brak; 90 dni -> jest
    rj89 = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 89,
            "gross_monthly_salary": 5652.0,
        },
    ).json()
    assert rj89["waiting_period_met"] is False

    rj90 = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 90,
            "gross_monthly_salary": 5652.0,
        },
    ).json()
    assert rj90["waiting_period_met"] is True

    # Art. 4 ust. 3 pkt 1 (absolwent) i pkt 2 (wypadek w drodze) działają TAKŻE dla JDG / Zlecenie!
    r_grad = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "zlecenie",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 5,
            "waiting_period_exemption_reason": "graduate_90_days",
            "gross_monthly_salary": 5000.0,
        },
    ).json()
    assert r_grad["waiting_period_met"] is True
    assert r_grad["eligible_sickness_benefit"] is True

    r_acc = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 1,
            "waiting_period_exemption_reason": "commute_accident",
            "gross_monthly_salary": 5652.0,
        },
    ).json()
    assert r_acc["waiting_period_met"] is True
    assert r_acc["eligible_sickness_benefit"] is True


def test_pregnancy_jdg_debt_threshold_art2a_exact_boundary():
    # 1% z 4806 zł = 48.06 zł -> <= 48.06 NIE wstrzymuje; 48.07 WSTRZYMUJE
    r_ok = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 400,
            "gross_monthly_salary": 5652.0,
            "contribution_debt_pln": 48.06,
        },
    ).json()
    assert r_ok["payout_suspended_due_to_debt"] is False

    r_blocked = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 400,
            "gross_monthly_salary": 5652.0,
            "contribution_debt_pln": 48.07,
        },
    ).json()
    assert r_blocked["payout_suspended_due_to_debt"] is True
    assert any("art. 2a" in w for w in r_blocked["warnings"])


def test_pregnancy_post_employment_art7_edge_cases():
    # Brak tytułu ubezpieczenia (none) -> odmowa (nie zamienia po cichu na UoP!)
    r_none = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "none",
            "gross_monthly_salary": 7000.0,
            "employment_terminated_special": True,
            "termination_reason": "post_employment_art7",
        },
    ).json()
    assert r_none["eligible_sickness_benefit"] is False

    # Niespełniony okres wyczekiwania -> odmowa wg art. 13 ust. 1 pkt 3
    r_wait = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "insurance_days": 10,
            "gross_monthly_salary": 7000.0,
            "employment_terminated_special": True,
            "termination_reason": "post_employment_art7",
        },
    ).json()
    assert r_wait["eligible_sickness_benefit"] is False
    assert r_wait["waiting_period_met"] is False
    assert any("art. 13 ust. 1 pkt 3" in w for w in r_wait["warnings"])

    # Bez kodu B po ustaniu -> wstępnie 91 dni (art. 8 ust. 2) i 80%
    r_no_b = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "insurance_days": 120,
            "gross_monthly_salary": 15000.0,
            "has_code_b": False,
            "employment_terminated_special": True,
            "termination_reason": "post_employment_art7",
        },
    ).json()
    assert r_no_b["eligible_sickness_benefit"] is True
    assert abs(r_no_b["benefit_base_monthly"] - 9420.00) < 0.02
    assert r_no_b["max_benefit_days"] == 91
    assert r_no_b["benefit_rate_percent"] == 80.0


def test_pregnancy_art30_strict_statutory_interpretation():
    # Art. 30 ust. 3 — upadłość pracodawcy dla UoP: brak limitu 270 dni, brak rehabilitacyjnego, do dnia porodu
    r_bank = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "employment_terminated_special": True,
            "termination_reason": "bankruptcy_liquidation",
        },
    ).json()
    assert r_bank["eligible_maternity_equivalent"] is True
    assert r_bank["eligible_post_birth_maternity_art30"] is True
    assert r_bank["max_benefit_days"] == 0
    assert r_bank["rehabilitation_max_days"] == 0
    assert r_bank["rehabilitation_monthly_gross"] == 0.0
    assert "Do dnia porodu" in r_bank["benefit_duration_label"]

    # Art. 30 ust. 3 dla JDG -> ODMOWA (dotyczy wyłącznie pracownicy UoP!)
    r_jdg = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "jdg",
            "gross_monthly_salary": 7000.0,
            "employment_terminated_special": True,
            "termination_reason": "bankruptcy_liquidation",
        },
    ).json()
    assert r_jdg["eligible_maternity_equivalent"] is False
    assert r_jdg["eligible_post_birth_maternity_art30"] is False

    # Ścisła wykładnia dla wyroku sądu (art. 30 ust. 1 pkt 2 vs ust. 3):
    # Brak zasiłku w wys. macierzyńskiego przed porodem, ALE potwierdzone prawo do zasiłku macierzyńskiego PO porodzie
    r_court = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "employment_terminated_special": True,
            "termination_reason": "unlawful_termination_court_ruling",
        },
    ).json()
    assert r_court["eligible_sickness_benefit"] is False
    assert r_court["eligible_maternity_equivalent"] is False
    assert r_court["eligible_post_birth_maternity_art30"] is True
    assert abs(r_court["benefit_base_monthly"] - round(7000 * 0.8629, 2)) < 0.02
    assert r_court["rehabilitation_max_days"] == 0


# =============================================================================
# 2. KREATOR INDYWIDUALNEJ PODSTAWY (/api/v1/calculator/benefit-base)
# =============================================================================


def test_individual_base_edge_cases():
    # previous_benefit z 0 -> 422 (zamiast spadania do uop_12m)
    r_zero = client.post(
        "/api/v1/calculator/benefit-base",
        json={"insurance_title": "uop", "mode": "previous_benefit", "previous_benefit_base": 0},
    )
    assert r_zero.status_code == 422

    # previous_benefit poniżej minimum 2026 dla UoP -> podniesienie do 4147.10 (art. 45)
    r_prev_floor = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "uop",
            "mode": "previous_benefit",
            "previous_benefit_base": 3800.0,
            "fte_fraction": 1.0,
        },
    )
    assert r_prev_floor.status_code == 200
    assert r_prev_floor.json()["floor_applied"] is True
    assert abs(r_prev_floor.json()["computed_base_monthly"] - 4147.10) < 0.02

    # JDG 0 pełnych miesięcy (art. 49 ust. 1 pkt 1) -> wyłącznie najniższa podstawa po -13.71%
    r_jdg0 = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "jdg",
            "mode": "jdg_art48a",
            "jdg_insured_months": 0,
            "jdg_declared_monthly_gross": 23550.0,
            "jdg_preferential_zus": False,
        },
    )
    assert r_jdg0.status_code == 200
    d0 = r_jdg0.json()
    assert abs(d0["computed_base_monthly"] - 4877.11) < 0.02
    assert "Art. 49 ust. 1 pkt 1" in d0["legal_basis"]

    # JDG 3 miesiące preferencyjny ZUS z wysoką deklaracją -> 1441.80 * 0.8629 = 1244.13 + 3/12 * (20321.30 - 1244.13)
    r_jdg_pref = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "jdg",
            "mode": "jdg_art48a",
            "jdg_insured_months": 3,
            "jdg_declared_monthly_gross": 23550.0,
            "jdg_preferential_zus": True,
        },
    )
    assert r_jdg_pref.status_code == 200
    expected_min = round(1441.80 * 0.8629, 2)  # 1244.13
    expected_decl = round(23550.0 * 0.8629, 2)  # 20321.30
    expected_base = round(expected_min + round((expected_decl - expected_min) / 12.0 * 3, 2), 2)
    assert abs(r_jdg_pref.json()["computed_base_monthly"] - expected_base) < 0.02

    # JDG w trybie uop_12m nie dolicza premii pracowniczych i cytuje art. 48-52
    r_jdg_list = client.post(
        "/api/v1/calculator/benefit-base",
        json={
            "insurance_title": "jdg",
            "mode": "uop_12m",
            "monthly_gross_salaries": [6000.0, 6000.0],
            "annual_bonus_total": 12000.0,
        },
    )
    assert r_jdg_list.status_code == 200
    dl = r_jdg_list.json()
    assert "Art. 48–52" in dl["legal_basis"]
    assert abs(dl["computed_base_monthly"] - round(6000.0 * 0.8629, 2)) < 0.02


# =============================================================================
# 3. KALKULATOR ZINTEGROWANY (/api/v1/calculator/integrated)
# =============================================================================


def test_integrated_work_combination_day_flooring_art182_1f_para4():
    # 10 tyg. na 0.4 etatu z pracą w części wydłużonej (§ 7):
    # 10 * 7 * 0.4 / 0.6 = 46.666... dni -> art. 182^1f § 4 pomija niepełny dzień => 46 dni (6.57 tyg.)!
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "payment_variant": "100_70",
            "combine_parental_with_work": True,
            "work_fte_fraction": 0.4,
            "combined_work_weeks": 10,
            "work_during_extended_part": True,
        },
    )
    assert res.status_code == 200
    d = res.json()
    assert abs(d["parental_weeks_extended_by_work"] - round(46 / 7.0, 2)) < 0.005
    comb_rows = [row for row in d["breakdown"] if "łączony z pracą" in row["label"]]
    assert len(comb_rows) == 1
    assert comb_rows[0]["days"] == 10 * 7 + 46  # 116 dni


def test_integrated_father_81_5_split_with_work_combination():
    # Ojciec bierze 20 tyg. w wariancie 81.5% (11 tyg. wspólnej @ 81.5% + 9 tyg. nieprzenoszalnej @ 70%)
    # i łączy 14 tyg. z pracą (0.5 etatu, bez pracy w wydłużeniu -> 11 tyg. wspólnej + 3 tyg. nieprzenoszalnej)
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
            "gross_monthly_salary": 7000.0,
            "second_parent_gross_salary": 8000.0,
            "payment_variant": "81_5",
            "father_takes_parental_weeks": 20,
            "father_combine_parental_with_work": True,
            "father_work_fte_fraction": 0.5,
            "father_combined_work_weeks": 14,
            "father_work_during_extended_part": False,
        },
    )
    assert res.status_code == 200
    d = res.json()
    # Część wspólna ojca musi mieć stawkę bazową 81.5% (po 0.5 etatu = 40.75%), a nieprzenoszalna 70% (po 0.5 = 35%)!
    father_rows = [r for r in d["breakdown"] if r["parent"] == "Ojciec"]
    rates = {r["rate_percent"] for r in father_rows}
    assert 40.75 in rates  # 11 tyg. wspólnej z pracą @ 81.5% * 0.5
    assert 81.5 in rates  # wydłużenie z puli wspólnej bez pracy @ 81.5%
    assert 35.0 in rates  # 3 tyg. nieprzenoszalne z pracą @ 70% * 0.5
    assert 70.0 in rates  # 6 tyg. pełnych + wydłużenie z puli nieprzenoszalnej @ 70%
    assert d["parental_weeks_extended_by_work"] == 7.0  # (11*0.5 + 3*0.5) = 7.0 tyg.


def test_integrated_equalization_art31_ust4_with_father_9w_and_topup_guard():
    # Przypadek 1: Matka 0 tyg. rodzicielskiego, ojciec bierze TYLKO swoje 9 tyg. nieprzenoszalne (@ 70%)
    # oraz 6 tyg. przejętego macierzyńskiego -> 0 dni w stawce 81.5% => wyrównanie dla OBOJGA rodziców!
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
            "gross_monthly_salary": 7000.0,
            "second_parent_gross_salary": 8000.0,
            "payment_variant": "81_5",
            "mother_maternity_weeks": 14,
            "mother_takes_parental_weeks": 0,
            "father_takes_parental_weeks": 9,
        },
    )
    assert res.status_code == 200
    d = res.json()
    base1 = round(7000 * 0.8629, 2)
    base2 = round(8000 * 0.8629, 2)
    exp_eq1 = round(round(base1 / 30.0, 2) * 98 - round(round(base1 * 0.815, 2) / 30.0, 2) * 98, 2)
    exp_eq2 = round(round(base2 / 30.0, 2) * 42 - round(round(base2 * 0.815, 2) / 30.0, 2) * 42, 2)
    assert abs(d["equalization_to_100_pln"] - round(exp_eq1 + exp_eq2, 2)) < 0.05

    # Przypadek 2: Niska podstawa (zlecenie 1000 zł -> base 862.90), już podwyższona do 1000 zł/mies. (art. 31 ust. 3a)
    # -> wyrównanie do 100% musi wynieść 0.00 zł (brak podwójnej dopłaty!)
    res_low = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "zlecenie",
            "single_parent_or_no_second_parent": True,
            "gross_monthly_salary": 1000.0,
            "payment_variant": "81_5",
            "mother_takes_parental_weeks": 0,
            "father_takes_parental_weeks": 0,
        },
    )
    assert res_low.status_code == 200
    d_low = res_low.json()
    assert d_low["minimum_benefit_top_up_applied"] is True
    assert d_low["equalization_to_100_pln"] == 0.0


def test_integrated_pre_birth_maternity_enforces_14_weeks_after_birth():
    # 1 dziecko (20 tyg.), 6 tyg. przed porodem -> matka musi mieć min. 6 + 14 = 20 tyg. (ojciec 0 tyg. macierzyńskiego)
    res = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "uop",
            "gross_monthly_salary": 7000.0,
            "pre_birth_maternity_weeks": 6,
            "mother_maternity_weeks": 14,
        },
    )
    assert res.status_code == 200
    d = res.json()
    mat_mother = [r for r in d["breakdown"] if r["label"] == "Urlop macierzyński" and r["parent"] == "Matka"]
    mat_father = [r for r in d["breakdown"] if "Przejęta część" in r["label"]]
    assert mat_mother[0]["weeks"] == 20.0
    assert len(mat_father) == 0


def test_integrated_adoption_age_cap_and_foster_deduction_art183():
    # Adopcja dziecka w wieku 13.3 lat (floor(0.7 * 52.1429) = 36 tyg. do 14. r.ż.):
    # 20 tyg. na warunkach macierzyńskiego + 16 tyg. rodzicielskiego (7 tyg. Rodzic 1 + 9 tyg. Rodzic 2, art. 183 § 4^1 KP)!
    r_age = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "insurance_title": "uop",
            "child_age_years": 13.3,
            "gross_monthly_salary": 7000.0,
            "father_takes_parental_weeks": 9,
        },
    )
    assert r_age.status_code == 200
    da = r_age.json()
    assert da["maternity_weeks"] == 20
    assert da["parental_weeks_total"] == 16.0  # 36 - 20 = 16 tyg. (7 tyg. Rodzic 1 + 9 tyg. Rodzic 2)

    # Adopcja po wcześniejszym wykorzystaniu 35 z 41 tyg. rodzicielskiego w rodzinie zastępczej (art. 183 § 8):
    # Pozostałe 6 tyg. NIE może zniknąć przez odejmowanie 9 tyg. od pozostałej puli!
    r_ded = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "insurance_title": "uop",
            "child_age_years": 5.0,
            "gross_monthly_salary": 7000.0,
            "previously_used_foster_maternity_weeks": 20,
            "previously_used_foster_parental_weeks": 35,
            "father_takes_parental_weeks": 0,
        },
    )
    assert r_ded.status_code == 200
    dd = r_ded.json()
    assert dd["maternity_weeks"] == 0
    assert dd["parental_weeks_total"] == 6.0


def test_integrated_uninsured_mother_cannot_bypass_exclusions_and_supports_work():
    # Rodzina zastępcza ZAWODOWA z nieubezpieczonym Rodzicem 1 + second_parent_insured_claim=True -> ODMOWA!
    r_prof = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "foster",
            "foster_family_type": "professional",
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
        },
    )
    assert r_prof.status_code == 200
    assert r_prof.json()["eligible"] is False

    # Dziecko 16 lat przy adopcji z nieubezpieczonym Rodzicem 1 -> ODMOWA!
    r_old = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "adoption",
            "child_age_years": 16.0,
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
        },
    )
    assert r_old.status_code == 200
    assert r_old.json()["eligible"] is False

    # Martwe urodzenie (1 dziecko) z nieubezpieczoną matką -> brak rodzicielskiego/ojcowskiego dla ojca!
    r_sb = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "stillbirth_or_early_death": True,
            "children_count": 1,
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "father_takes_paternity_leave": True,
        },
    )
    assert r_sb.status_code == 200
    assert r_sb.json()["eligible"] is False

    # Normalny poród, matka nieubezpieczona, ojciec na UoP łączy 10 tyg. rodzicielskiego z pracą na 0.5 etatu
    r_work = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
            "second_parent_gross_salary": 8000.0,
            "father_takes_parental_weeks": 32,
            "father_combine_parental_with_work": True,
            "father_work_fte_fraction": 0.5,
            "father_combined_work_weeks": 10,
            "father_work_during_extended_part": True,
            "father_takes_paternity_leave": True,
        },
    )
    assert r_work.status_code == 200
    dw = r_work.json()
    assert dw["eligible"] is True
    assert dw["parental_weeks_extended_by_work"] == 10.0
    assert dw["parental_weeks_total"] == 42.0
    assert dw["paternity_weeks"] == 2


def test_integrated_supplementary_maternity_art180_2_all_tiers():
    # <28 tyg. -> maks. 15 tyg.
    r1 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 26,
            "birth_weight_grams": 1200,
            "hospitalization_weeks": 18,
        },
    ).json()
    assert r1["supplementary_maternity_weeks"] == 15

    # >=37 tyg. (masa >1000g) i warunek 2 kolejnych dni (5–28 dzień) NIESPEŁNIONY -> 0 tyg.
    r2 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 39,
            "birth_weight_grams": 3200,
            "hospitalization_weeks": 3,
            "full_term_hospitalization_condition_met": False,
        },
    ).json()
    assert r2["supplementary_maternity_weeks"] == 0

    # >=37 tyg. (masa >1000g) i warunek SPEŁNIONY -> 3 tyg. (maks. 8)
    r3 = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "premature_or_hospitalized": True,
            "gestation_week": 39,
            "birth_weight_grams": 3200,
            "hospitalization_weeks": 3,
            "full_term_hospitalization_condition_met": True,
        },
    ).json()
    assert r3["supplementary_maternity_weeks"] == 3


def test_integrated_zlecenie_deregistration_warning_and_twins_stillbirth():
    # Zlecenie dostaje ostrzeżenie o automatycznym wyrejestrowaniu z dobrowolnego chorobowego (Poradnik ZUS str. 36)
    r_zl = client.post(
        "/api/v1/calculator/integrated",
        json={"scenario": "birth", "insurance_title": "zlecenie", "gross_monthly_salary": 6000.0},
    ).json()
    assert any("wyrejestrowanie" in w for w in r_zl["warnings"])

    # Bliźniaki, 1 dziecko zmarło -> wymiar jak dla 1 żywego (20 + 41) + zasiłek pogrzebowy 7000 zł
    r_tw = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "children_count": 2,
            "stillbirth_or_early_death": True,
            "gross_monthly_salary": 7000.0,
            "father_takes_parental_weeks": 9,
        },
    ).json()
    assert r_tw["maternity_weeks"] == 20
    assert r_tw["parental_weeks_total"] == 41.0
    assert any("7 000" in w for w in r_tw["warnings"])


def test_docs_verification_discovered_edge_cases():
    # 1. Zaokrąglenie ROUND_HALF_UP limitu 250% dobrowolnego chorobowego: 23 550 * 0.8629 = 20 321,30 zł (Załącznik ZUS 2026)
    r_cap = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "jdg", "has_voluntary_sickness_insurance": True, "insurance_days": 365, "gross_monthly_salary": 30000.0},
    ).json()
    assert r_cap["benefit_base_monthly"] == 20321.30

    # 2. Aktywne ubezpieczenie bez kodu B -> wstępnie 80% i 182 dni (art. 8 ust. 1 u.z.)
    r_nob = client.post(
        "/api/v1/calculator/pregnancy",
        json={"insurance_title": "uop", "insurance_days": 120, "gross_monthly_salary": 6500.0, "has_code_b": False},
    ).json()
    assert r_nob["benefit_rate_percent"] == 80.0
    assert r_nob["max_benefit_days"] == 182

    # 3. Zwolnienie z okresu wyczekiwania (art. 4 ust. 3) -> waiting_period_required_days == 0 + płatnik 'zleceniodawca'
    r_ex = client.post(
        "/api/v1/calculator/pregnancy",
        json={
            "insurance_title": "zlecenie",
            "has_voluntary_sickness_insurance": True,
            "insurance_days": 3,
            "waiting_period_exemption_reason": "commute_accident",
            "gross_monthly_salary": 5000.0,
            "employer_insured_count": 30,
        },
    ).json()
    assert r_ex["waiting_period_required_days"] == 0
    assert r_ex["waiting_period_met"] is True
    assert "zleceniodawca" in r_ex["payer"].lower()

    # 4. Adopcja w wieku 13.5 lat (pozostało 6 tyg. < 9 tyg. do 14. r.ż.) -> 6 tyg. rodzicielskiego nie przepada!
    r_ad135 = client.post(
        "/api/v1/calculator/integrated",
        json={"scenario": "adoption", "insurance_title": "uop", "child_age_years": 13.5, "gross_monthly_salary": 7500.0, "father_takes_parental_weeks": 0},
    ).json()
    assert r_ad135["maternity_weeks"] == 20
    assert r_ad135["parental_weeks_total"] == 6.0

    # 5. Art. 31 ust. 3h (matka nieubezpieczona) z domyślnym father_takes_parental_weeks=0 + ojcowski -> ojciec dostaje 32 tyg. + 2 tyg. ojc.
    r_3h = client.post(
        "/api/v1/calculator/integrated",
        json={
            "scenario": "birth",
            "insurance_title": "none",
            "has_sickness_insurance_on_birth_date": False,
            "second_parent_insured_claim": True,
            "second_parent_insurance_title": "uop",
            "second_parent_has_sickness_insurance": True,
            "second_parent_gross_salary": 8000.0,
            "father_takes_paternity_leave": True,
        },
    ).json()
    assert r_3h["eligible"] is True
    assert r_3h["parental_weeks_total"] == 32.0
    assert r_3h["paternity_weeks"] == 2

