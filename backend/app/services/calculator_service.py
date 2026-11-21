import math
from app.models.calculator import (
    BenefitScenario,
    InsuranceTitle,
    IntegratedCalculatorRequest,
    IntegratedCalculatorResponse,
    LeaveBreakdownItem,
    PaymentVariant,
    PregnancyBenefitRequest,
    PregnancyBenefitResponse,
)
from app.models.parameters import LegalParameters


def _compute_benefit_base(
    gross_salary: float,
    custom_base: float | None,
    insurance_title: InsuranceTitle,
    params: LegalParameters,
) -> float:
    if custom_base is not None and custom_base > 0:
        return round(custom_base, 2)
    base = gross_salary * (1.0 - params.employee_social_security_rate)
    if insurance_title == InsuranceTitle.UOP:
        min_base = params.minimum_wage_gross * (1.0 - params.employee_social_security_rate)
        base = max(base, min_base)
    return round(base, 2)


def _determine_payer(insurance_title: InsuranceTitle, employer_insured_count: int, params: LegalParameters) -> str:
    if insurance_title in (InsuranceTitle.UOP, InsuranceTitle.ZLECENIE) and employer_insured_count > params.payer_employee_threshold:
        return f"Płatnik składek (pracodawca zgłaszający > {params.payer_employee_threshold} ubezpieczonych)"
    return "Zakład Ubezpieczeń Społecznych (ZUS)"


def calculate_pregnancy_benefit(
    req: PregnancyBenefitRequest, params: LegalParameters
) -> PregnancyBenefitResponse:
    warnings: list[str] = []

    if req.employment_terminated_special and req.termination_reason in (
        "bankruptcy_liquidation",
        "employer_death",
        "unlawful_termination_court_ruling",
    ):
        base = _compute_benefit_base(req.gross_monthly_salary, req.custom_benefit_base, InsuranceTitle.UOP, params)
        daily = round(base / 30.0, 2)
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=False,
            eligible_maternity_equivalent=True,
            waiting_period_required_days=0,
            waiting_period_met=True,
            benefit_rate_percent=100.0,
            benefit_base_monthly=base,
            daily_benefit_gross=daily,
            monthly_benefit_gross=round(base, 2),
            max_benefit_days=params.sickness_benefit_pregnancy_max_days,
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=[
                "Zasiłek w wysokości zasiłku macierzyńskiego przysługuje do dnia porodu po ustaniu zatrudnienia w szczególnych okolicznościach (upadłość/likwidacja/śmierć pracodawcy lub prawomocny wyrok sądu)."
            ],
            summary="Przysługuje zasiłek w wysokości zasiłku macierzyńskiego (100% podstawy wymiaru) wypłacany przez ZUS do dnia porodu.",
        )

    if req.insurance_title == InsuranceTitle.NONE or (
        req.insurance_title in (InsuranceTitle.ZLECENIE, InsuranceTitle.JDG)
        and not req.has_voluntary_sickness_insurance
    ):
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=False,
            eligible_maternity_equivalent=False,
            waiting_period_required_days=params.waiting_period_voluntary_days,
            waiting_period_met=False,
            benefit_rate_percent=0.0,
            benefit_base_monthly=0.0,
            daily_benefit_gross=0.0,
            monthly_benefit_gross=0.0,
            max_benefit_days=0,
            employer_pay_days=0,
            payer="Brak uprawnień",
            warnings=[
                "Brak podlegania ubezpieczeniu chorobowemu. Aby uzyskać prawo do zasiłku chorobowego na umowie zleceniu lub JDG, wymagane jest dobrowolne ubezpieczenie chorobowe."
            ],
            summary="Brak prawa do zasiłku chorobowego z powodu niepodlegania ubezpieczeniu chorobowemu.",
        )

    waiting_days = (
        params.waiting_period_mandatory_days
        if req.insurance_title == InsuranceTitle.UOP
        else params.waiting_period_voluntary_days
    )
    waiting_met = req.insurance_days >= waiting_days

    if not waiting_met:
        warnings.append(
            f"Nie upłynął okres wyczekiwania ({req.insurance_days}/{waiting_days} dni). Prawo do zasiłku powstanie po osiągnięciu {waiting_days} dni nieprzerwanego ubezpieczenia."
        )

    rate = params.sickness_benefit_pregnancy_rate if req.has_code_b else 0.8
    if not req.has_code_b:
        warnings.append(
            "Brak kodu literowego 'B' na e-ZLA skutkuje stawką 80% zamiast 100%. Można złożyć wniosek do lekarza o dopisanie kodu lub zaświadczenie o ciąży."
        )

    base = _compute_benefit_base(req.gross_monthly_salary, req.custom_benefit_base, req.insurance_title, params)
    daily = round((base * rate) / 30.0, 2)
    monthly = round(base * rate, 2)
    employer_days = 0
    if req.insurance_title == InsuranceTitle.UOP:
        employer_days = (
            params.sickness_pay_employer_days_over_50
            if req.age_over_50
            else params.sickness_pay_employer_days_under_50
        )

    payer = _determine_payer(req.insurance_title, req.employer_insured_count, params)
    summary = (
        f"Przysługuje zasiłek chorobowy w ciąży w wysokości {int(rate * 100)}% podstawy wymiaru (maks. {params.sickness_benefit_pregnancy_max_days} dni)."
        if waiting_met
        else f"Ubezpieczenie aktywne, ale okres wyczekiwania ({waiting_days} dni) nie został jeszcze spełniony."
    )

    return PregnancyBenefitResponse(
        eligible_sickness_benefit=waiting_met,
        eligible_maternity_equivalent=False,
        waiting_period_required_days=waiting_days,
        waiting_period_met=waiting_met,
        benefit_rate_percent=round(rate * 100, 1),
        benefit_base_monthly=base,
        daily_benefit_gross=daily,
        monthly_benefit_gross=monthly,
        max_benefit_days=params.sickness_benefit_pregnancy_max_days,
        employer_pay_days=employer_days,
        payer=payer,
        warnings=warnings,
        summary=summary,
    )


def _compute_supplementary_weeks(req: IntegratedCalculatorRequest, params: LegalParameters) -> int:
    if not req.premature_or_hospitalized or req.hospitalization_weeks <= 0:
        return 0
    is_extreme = (req.gestation_week is not None and req.gestation_week < 28) or (
        req.birth_weight_grams is not None and req.birth_weight_grams <= 1000
    )
    cap = (
        params.supplementary_maternity_max_weeks_extreme
        if is_extreme
        else params.supplementary_maternity_max_weeks_standard
    )
    return min(req.hospitalization_weeks, cap)


def calculate_integrated_maternity(
    req: IntegratedCalculatorRequest, params: LegalParameters
) -> IntegratedCalculatorResponse:
    warnings: list[str] = []
    docs: list[str] = []

    if req.insurance_title == InsuranceTitle.NONE or not req.has_sickness_insurance_on_birth_date:
        return IntegratedCalculatorResponse(
            eligible=False,
            ineligibility_reason="Brak podlegania ubezpieczeniu chorobowemu na dzień porodu lub przyjęcia dziecka na wychowanie.",
            benefit_base_parent1=0.0,
            benefit_base_parent2=0.0,
            total_weeks=0.0,
            maternity_weeks=0,
            supplementary_maternity_weeks=0,
            parental_weeks_total=0.0,
            parental_weeks_extended_by_work=0.0,
            paternity_weeks=0,
            payer="Brak uprawnień",
            breakdown=[],
            total_estimated_gross_pln=0.0,
            warnings=[
                "Zasiłek macierzyński wymaga podlegania ubezpieczeniu chorobowemu w dniu porodu/przyjęcia dziecka. Sprawdź możliwość świadczenia rodzicielskiego (Kosiniakowe) lub uprawnienia drugiego rodzica (ojciec ma prawo do urlopu rodzicielskiego i ojcowskiego, jeśli sam podlega ubezpieczeniu)."
            ],
            required_documents=[],
        )

    # Weryfikacja limitu wieku dla adopcji i rodziny zastępczej
    if req.scenario == BenefitScenario.FOSTER and req.child_age_years is not None:
        max_age = (
            params.foster_deferred_school_max_child_age
            if req.foster_deferred_school
            else params.foster_max_child_age
        )
        if req.child_age_years > max_age:
            warnings.append(
                f"Wiek dziecka ({req.child_age_years} lat) przekracza limit {max_age} lat dla rodziny zastępczej niezawodowej."
            )
    elif req.scenario == BenefitScenario.ADOPTION and req.child_age_years is not None:
        if req.child_age_years > params.adoption_max_child_age:
            warnings.append(
                f"Wiek dziecka ({req.child_age_years} lat) przekracza limit {params.adoption_max_child_age} lat dla przysposobienia."
            )

    # Podstawa wymiaru
    base_p1 = _compute_benefit_base(req.gross_monthly_salary, req.custom_benefit_base, req.insurance_title, params)
    p2_gross = req.second_parent_gross_salary if req.second_parent_gross_salary is not None else req.gross_monthly_salary
    base_p2 = _compute_benefit_base(p2_gross, req.second_parent_custom_base, InsuranceTitle.UOP, params)

    # Wymiar urlopu macierzyńskiego / na warunkach urlopu macierzyńskiego
    child_key = str(min(req.children_count, 5))
    maternity_weeks = params.maternity_weeks_by_children.get(child_key, 20)

    # Uzupełniający urlop macierzyński (wcześniak / hospitalizacja)
    supplementary_weeks = _compute_supplementary_weeks(req, params)
    if supplementary_weeks > 0:
        docs.append("Zaświadczenie wydane przez szpital o okresie hospitalizacji i masie/tygodniu urodzenia dziecka")

    # Wymiar urlopu rodzicielskiego
    if req.has_za_zyciem_certificate:
        parental_base_weeks = (
            params.parental_weeks_za_zyciem_single
            if req.children_count == 1
            else params.parental_weeks_za_zyciem_multiple
        )
        docs.append("Zaświadczenie lekarskie 'Za życiem' (art. 4 ust. 3 ustawy)")
    else:
        parental_base_weeks = (
            params.parental_weeks_single if req.children_count == 1 else params.parental_weeks_multiple
        )

    # Podział macierzyńskiego (matka min. 14 tygodni przy porodzie)
    if req.scenario == BenefitScenario.BIRTH:
        mother_mat = (
            req.mother_maternity_weeks
            if req.mother_maternity_weeks is not None
            else maternity_weeks
        )
        if mother_mat < params.maternity_min_mother_weeks:
            warnings.append(
                f"Pierwsze {params.maternity_min_mother_weeks} tygodni urlopu macierzyńskiego po porodzie matka musi wykorzystać osobiście (poza sytuacjami szczególnymi). Skorygowano podział w symulacji."
            )
            mother_mat = params.maternity_min_mother_weeks
        mother_mat = min(mother_mat, maternity_weeks)
        father_mat = maternity_weeks - mother_mat
    else:
        mother_mat = maternity_weeks
        father_mat = 0

    # Podział rodzicielskiego (z zachowaniem 9 tygodni nieprzenoszalnych)
    non_transferable = params.parental_non_transferable_weeks
    max_single_parent_parental = parental_base_weeks - non_transferable
    father_parental = min(req.father_takes_parental_weeks, parental_base_weeks)
    mother_parental = max(0, min(max_single_parent_parental, parental_base_weeks - father_parental))

    if father_parental < non_transferable:
        warnings.append(
            f"Drugiemu rodzicowi przysługuje {non_transferable} tygodni nieprzenoszalnego urlopu rodzicielskiego. Niewykorzystana część z tych {non_transferable} tygodni przepada."
        )

    # Łączenie urlopu rodzicielskiego z pracą (proporcjonalne wydłużenie)
    extended_weeks = 0.0
    if req.combine_parental_with_work and req.work_fte_fraction > 0 and req.combined_work_weeks > 0:
        if req.insurance_title != InsuranceTitle.UOP:
            warnings.append(
                "Łączenie urlopu rodzicielskiego z pracą u pracodawcy (do 1/2 etatu) z proporcjonalnym wydłużeniem urlopu dotyczy pracowników zatrudnionych na umowę o pracę."
            )
        else:
            fte = min(req.work_fte_fraction, params.parental_work_max_fte)
            effective_work_weeks = min(req.combined_work_weeks, mother_parental)
            extended_weeks = round(effective_work_weeks * fte / (1.0 - fte), 1)
            # Limit maksymalnego wydłużenia wg Kodeksu pracy (do 82/86 tyg. standardowo)
            max_extended = parental_base_weeks * 2 - parental_base_weeks
            extended_weeks = min(extended_weeks, float(max_extended))

    # Stawki procentowe
    if req.payment_variant == PaymentVariant.COMBINED_81_5:
        mat_rate = params.combined_21_days_rate
        mother_parental_rate = params.combined_21_days_rate
        father_parental_rate = params.non_transferable_parental_rate
        warnings.append(
            f"Wariant 81,5% wymaga złożenia wniosku w nieprzekraczalnym terminie {params.combined_application_deadline_days} dni po porodzie/przyjęciu dziecka. Część nieprzenoszalna drugiego rodzica (9 tyg.) jest zawsze płatna 70%."
        )
    else:
        mat_rate = params.maternity_rate_standard
        mother_parental_rate = params.parental_rate_standard
        father_parental_rate = params.parental_rate_standard

    def _calc_amount(base: float, rate: float, weeks: float) -> tuple[float, float]:
        monthly = round(base * rate, 2)
        total = round((base * rate / 30.0) * (weeks * 7.0), 2)
        return monthly, total

    breakdown: list[LeaveBreakdownItem] = []
    p1_label = "Matka" if req.scenario == BenefitScenario.BIRTH else "Rodzic (wnioskodawca)"
    p2_label = "Ojciec" if req.scenario == BenefitScenario.BIRTH else "Drugi rodzic"

    # 1. Macierzyński / na warunkach
    m_monthly, m_total = _calc_amount(base_p1, mat_rate, mother_mat)
    breakdown.append(
        LeaveBreakdownItem(
            label="Urlop macierzyński" if req.scenario == BenefitScenario.BIRTH else "Urlop na warunkach urlopu macierzyńskiego",
            parent=p1_label,
            weeks=float(mother_mat),
            rate_percent=round(mat_rate * 100, 1),
            monthly_gross_pln=m_monthly,
            total_gross_pln=m_total,
        )
    )

    if father_mat > 0:
        fm_monthly, fm_total = _calc_amount(base_p2, mat_rate, father_mat)
        breakdown.append(
            LeaveBreakdownItem(
                label="Przejęta część urlopu macierzyńskiego",
                parent=p2_label,
                weeks=float(father_mat),
                rate_percent=round(mat_rate * 100, 1),
                monthly_gross_pln=fm_monthly,
                total_gross_pln=fm_total,
            )
        )

    # 2. Uzupełniający urlop macierzyński
    if supplementary_weeks > 0:
        sup_rate = params.supplementary_maternity_rate
        s_monthly, s_total = _calc_amount(base_p1, sup_rate, supplementary_weeks)
        breakdown.append(
            LeaveBreakdownItem(
                label="Uzupełniający urlop macierzyński (wcześniak / hospitalizacja)",
                parent=p1_label,
                weeks=float(supplementary_weeks),
                rate_percent=round(sup_rate * 100, 1),
                monthly_gross_pln=s_monthly,
                total_gross_pln=s_total,
                notes="Udzielany jednorazowo bezpośrednio po urlopie macierzyńskim.",
            )
        )

    # 3. Urlop rodzicielski rodzica 1
    if mother_parental > 0:
        # W trakcie łączenia z pracą zasiłek jest pomniejszany proporcjonalnie do etatu
        mp_monthly, mp_total = _calc_amount(base_p1, mother_parental_rate, mother_parental)
        if extended_weeks > 0:
            fte = min(req.work_fte_fraction, params.parental_work_max_fte)
            # Łączna kwota za część łączoną + wydłużenie odpowiada proporcjonalnie pomniejszonemu zasiłkowi
            notes = f"Zawiera proporcjonalne wydłużenie o {extended_weeks} tyg. przy pracy na {fte} etatu (zasiłek pomniejszany proporcjonalnie do etatu w okresie pracy)."
        else:
            notes = None
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop rodzicielski",
                parent=p1_label,
                weeks=round(float(mother_parental) + extended_weeks, 1),
                rate_percent=round(mother_parental_rate * 100, 1),
                monthly_gross_pln=mp_monthly,
                total_gross_pln=mp_total,
                notes=notes,
            )
        )

    # 4. Urlop rodzicielski rodzica 2
    if father_parental > 0:
        fp_monthly, fp_total = _calc_amount(base_p2, father_parental_rate, father_parental)
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop rodzicielski (w tym 9 tyg. nieprzenoszalnych)",
                parent=p2_label,
                weeks=float(father_parental),
                rate_percent=round(father_parental_rate * 100, 1),
                monthly_gross_pln=fp_monthly,
                total_gross_pln=fp_total,
            )
        )

    # 5. Urlop ojcowski
    paternity_weeks = params.paternity_weeks if req.father_takes_paternity_leave else 0
    if paternity_weeks > 0:
        pat_monthly, pat_total = _calc_amount(base_p2, params.paternity_rate, paternity_weeks)
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop ojcowski",
                parent=p2_label,
                weeks=float(paternity_weeks),
                rate_percent=round(params.paternity_rate * 100, 1),
                monthly_gross_pln=pat_monthly,
                total_gross_pln=pat_total,
                notes="Do ukończenia 12. miesiąca życia dziecka (lub 12 mies. od uprawomocnienia adopcji, maks. do 14 r.ż.).",
            )
        )

    # Wymagane dokumenty
    payer = _determine_payer(req.insurance_title, req.employer_insured_count, params)
    if req.insurance_title == InsuranceTitle.UOP:
        docs.insert(0, "Wniosek do pracodawcy o udzielenie urlopu macierzyńskiego i rodzicielskiego")
        if req.employer_insured_count <= params.payer_employee_threshold:
            docs.append("Zaświadczenie płatnika składek Z-3 (przesyła pracodawca do ZUS)")
    elif req.insurance_title == InsuranceTitle.ZLECENIE:
        docs.insert(0, "Wniosek o zasiłek macierzyński ZAM")
        if req.employer_insured_count <= params.payer_employee_threshold:
            docs.append("Zaświadczenie płatnika składek Z-3a (przesyła zleceniodawca do ZUS)")
    else:
        docs.insert(0, "Wniosek o zasiłek macierzyński ZAM (składany bezpośrednio do ZUS przez PUE/eZUS)")
    docs.append("Odpis skrócony aktu urodzenia dziecka (lub orzeczenie sądu przy adopcji/rodzinie zastępczej)")

    total_weeks = round(sum(item.weeks for item in breakdown), 1)
    total_gross = round(sum(item.total_gross_pln for item in breakdown), 2)

    return IntegratedCalculatorResponse(
        eligible=True,
        benefit_base_parent1=base_p1,
        benefit_base_parent2=base_p2,
        total_weeks=total_weeks,
        maternity_weeks=maternity_weeks,
        supplementary_maternity_weeks=supplementary_weeks,
        parental_weeks_total=round(float(mother_parental + father_parental) + extended_weeks, 1),
        parental_weeks_extended_by_work=extended_weeks,
        paternity_weeks=paternity_weeks,
        payer=payer,
        breakdown=breakdown,
        total_estimated_gross_pln=total_gross,
        warnings=warnings,
        required_documents=docs,
    )
