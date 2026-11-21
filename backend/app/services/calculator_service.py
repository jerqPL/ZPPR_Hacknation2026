from fastapi import HTTPException
from app.models.calculator import (
    BenefitScenario,
    FosterFamilyType,
    IndividualBaseCalculationRequest,
    IndividualBaseCalculationResponse,
    InsuranceTitle,
    IntegratedCalculatorRequest,
    IntegratedCalculatorResponse,
    LeaveBreakdownItem,
    PaymentVariant,
    PregnancyBenefitRequest,
    PregnancyBenefitResponse,
    TerminationReason,
)
from app.models.parameters import LegalParameters


def calculate_individual_benefit_base(
    req: IndividualBaseCalculationRequest, params: LegalParameters
) -> IndividualBaseCalculationResponse:
    """Kalkulator indywidualnej podstawy wymiaru zasiłku — Art. 36–52 ustawy zasiłkowej."""
    rate = params.employee_social_security_rate
    steps: list[str] = []
    cap_applied = False
    floor_applied = False

    if req.mode == "previous_benefit" and req.previous_benefit_base and req.previous_benefit_base > 0:
        base = round(req.previous_benefit_base, 2)
        legal_basis = "Art. 43 ustawy zasiłkowej (przerwa między zasiłkami krótsza niż miesiąc kalendarzowy)"
        steps.append(
            f"Zachowano podstawę wymiaru z poprzedniego zasiłku (np. chorobowego w ciąży): {base:.2f} zł (brak przerwy lub przerwa < 1 miesiąc kalendarzowy)."
        )
    elif req.mode == "jdg_art48a":
        max_cap_gross = params.voluntary_sickness_max_monthly_gross
        max_cap_net = round(max_cap_gross * (1.0 - rate), 2)
        declared_gross = req.jdg_declared_monthly_gross
        if declared_gross > max_cap_gross:
            declared_gross = max_cap_gross
            cap_applied = True
            steps.append(
                f"Ograniczono deklarowaną podstawę do ustawowego limitu 250% przeciętnego wynagrodzenia ({max_cap_gross:.2f} zł brutto -> {max_cap_net:.2f} zł po odliczeniu {rate*100:.2f}%)."
            )

        if req.jdg_min_monthly_gross is not None and req.jdg_min_monthly_gross > 0:
            min_gross = req.jdg_min_monthly_gross
        elif req.jdg_preferential_zus:
            min_gross = params.jdg_preferential_min_base_gross
        else:
            min_gross = params.jdg_standard_min_base_gross

        min_net = round(min_gross * (1.0 - rate), 2)
        declared_net = round(declared_gross * (1.0 - rate), 2)

        if req.jdg_insured_months < 12 and declared_net > min_net:
            legal_basis = "Art. 48a ust. 1 ustawy zasiłkowej (ubezpieczenie chorobowe na JDG krótsze niż 12 miesięcy)"
            excess = round(((declared_net - min_net) / 12.0) * req.jdg_insured_months, 2)
            base = round(min_net + excess, 2)
            steps.append(
                f"Najniższa podstawa po odliczeniu {rate*100:.2f}%: {min_net:.2f} zł (z {min_gross:.2f} zł brutto{' — preferencyjny ZUS' if req.jdg_preferential_zus else ''})."
            )
            steps.append(
                f"Zadeklarowana podstawa po odliczeniu {rate*100:.2f}%: {declared_net:.2f} zł przez {req.jdg_insured_months}/12 pełnych miesięcy."
            )
            steps.append(
                f"Proporcjonalna nadwyżka (art. 48a): ({declared_net:.2f} - {min_net:.2f}) × {req.jdg_insured_months}/12 = {excess:.2f} zł."
            )
            steps.append(f"Indywidualna podstawa wymiaru zasiłku: {min_net:.2f} + {excess:.2f} = {base:.2f} zł.")
        else:
            legal_basis = "Art. 48 ust. 1 ustawy zasiłkowej (przeciętny miesięczny przychód z 12 miesięcy na JDG)"
            base = declared_net
            steps.append(
                f"Przeciętna miesięczna podstawa składek z {req.jdg_insured_months} mies. po odliczeniu {rate*100:.2f}%: {base:.2f} zł."
            )
    else:
        legal_basis = "Art. 36–42 oraz art. 45 ustawy zasiłkowej (średnia z miesięcy ubezpieczenia + składniki okresowe)"
        # Odrzucamy zera i wartości ujemne (np. błędy wpisu lub miesiące zerowe)
        raw_salaries = [s for s in req.monthly_gross_salaries if s > 0][:12]
        if not raw_salaries:
            raise HTTPException(
                status_code=422,
                detail="Podaj co najmniej jedno dodatnie miesięczne wynagrodzenie brutto do wyliczenia podstawy wymiaru.",
            )

        # Realne wyłączenie miesięcy z przepracowaniem < 1/2 czasu pracy (art. 38 ust. 2 pkt 1)
        if req.uncompleted_months_excluded > 0:
            if len(raw_salaries) > req.uncompleted_months_excluded:
                sorted_asc = sorted(raw_salaries)
                excluded_vals = sorted_asc[: req.uncompleted_months_excluded]
                remaining = list(raw_salaries)
                for ev in excluded_vals:
                    remaining.remove(ev)
                raw_salaries = remaining
                steps.append(
                    f"Wyłączono {req.uncompleted_months_excluded} najniższych niepełnych mies. (<1/2 czasu pracy, art. 38 ust. 2 pkt 1): {', '.join(f'{v:.2f} zł' for v in excluded_vals)}."
                )
            else:
                steps.append(
                    f"Liczba miesięcy do wyłączenia ({req.uncompleted_months_excluded}) ≥ liczba wpisanych miesięcy ({len(raw_salaries)}) — pozostawiono dostępne miesiące."
                )

        if req.insurance_title in (InsuranceTitle.ZLECENIE, InsuranceTitle.JDG):
            max_cap_gross = params.voluntary_sickness_max_monthly_gross
            salaries = []
            for s in raw_salaries:
                if s > max_cap_gross:
                    cap_applied = True
                    salaries.append(max_cap_gross)
                else:
                    salaries.append(s)
            if cap_applied:
                steps.append(
                    f"Ograniczono miesięczne podstawy dobrowolnego ubezpieczenia chorobowego do limitu 250% przeciętnego wynagrodzenia ({max_cap_gross:.2f} zł brutto)."
                )
        else:
            salaries = raw_salaries

        months_count = len(salaries)
        avg_gross = sum(salaries) / months_count
        avg_net = avg_gross * (1.0 - rate)
        steps.append(
            f"Średnie miesięczne wynagrodzenie z {months_count} pełnych miesięcy: {avg_gross:.2f} zł brutto -> {avg_net:.2f} zł po odliczeniu {rate*100:.2f}%."
        )

        quarterly_addition = 0.0
        if req.quarterly_bonuses_total > 0:
            quarterly_addition = (req.quarterly_bonuses_total * (1.0 - rate)) / 12.0
            steps.append(
                f"Doliczono 1/12 premii kwartalnych z 4 kwartałów ({req.quarterly_bonuses_total:.2f} zł brutto): +{quarterly_addition:.2f} zł (art. 42 ust. 2)."
            )

        annual_addition = 0.0
        if req.annual_bonus_total > 0:
            annual_addition = (req.annual_bonus_total * (1.0 - rate)) / 12.0
            steps.append(
                f"Doliczono 1/12 nagrody rocznej / 13. pensji ({req.annual_bonus_total:.2f} zł brutto): +{annual_addition:.2f} zł (art. 42 ust. 3)."
            )

        base = round(avg_net + quarterly_addition + annual_addition, 2)

        if req.insurance_title == InsuranceTitle.UOP:
            min_base = round(params.minimum_wage_gross * req.fte_fraction * (1.0 - rate), 2)
            if base < min_base:
                base = min_base
                floor_applied = True
                steps.append(
                    f"Podniesiono podstawę do gwarantowanego minimum dla {req.fte_fraction:.2f} etatu: {min_base:.2f} zł (art. 45 ustawy zasiłkowej)."
                )
        elif req.insurance_title in (InsuranceTitle.ZLECENIE, InsuranceTitle.JDG):
            max_cap_net = round(params.voluntary_sickness_max_monthly_gross * (1.0 - rate), 2)
            if base > max_cap_net:
                base = max_cap_net
                cap_applied = True
                steps.append(
                    f"Ograniczono podstawę do maksymalnego limitu dobrowolnego ubezpieczenia chorobowego: {max_cap_net:.2f} zł."
                )

    return IndividualBaseCalculationResponse(
        computed_base_monthly=base,
        daily_rate_100_percent=round(base / 30.0, 2),
        daily_rate_81_5_percent=round((base * params.combined_21_days_rate) / 30.0, 2),
        daily_rate_70_percent=round((base * params.parental_rate_standard) / 30.0, 2),
        cap_applied=cap_applied,
        floor_applied=floor_applied,
        legal_basis=legal_basis,
        explanation_steps=steps,
    )


def _compute_benefit_base_with_explanation(
    gross_salary: float,
    custom_base: float | None,
    individual_config: IndividualBaseCalculationRequest | None,
    insurance_title: InsuranceTitle,
    params: LegalParameters,
    fte_fraction: float = 1.0,
) -> tuple[float, str]:
    rate = params.employee_social_security_rate
    if individual_config is not None:
        ind_res = calculate_individual_benefit_base(individual_config, params)
        return ind_res.computed_base_monthly, f"{ind_res.legal_basis}: " + " ".join(ind_res.explanation_steps)

    if custom_base is not None and custom_base > 0:
        base = round(custom_base, 2)
        notes_custom: list[str] = []
        if insurance_title == InsuranceTitle.UOP:
            min_base = round(params.minimum_wage_gross * fte_fraction * (1.0 - rate), 2)
            if base < min_base:
                base = min_base
                notes_custom.append(
                    f"podwyższono do gwarantowanego minimum dla {fte_fraction:.2f} etatu w {params.year} r.: {min_base:.2f} zł (art. 45)"
                )
        elif insurance_title in (InsuranceTitle.JDG, InsuranceTitle.ZLECENIE):
            max_base = round(params.voluntary_sickness_max_monthly_gross * (1.0 - rate), 2)
            if base > max_base:
                base = max_base
                notes_custom.append(
                    f"ograniczono do maksymalnego limitu podstawy dobrowolnego ubezpieczenia chorobowego {max_base:.2f} zł"
                )
        extra_info = f" ({'; '.join(notes_custom)})" if notes_custom else ""
        return (
            base,
            f"Zastosowano indywidualną podstawę wymiaru zasiłku ({base:.2f} zł po odliczeniu składek) ustaloną na podstawie dokumentacji sprawy{extra_info}.",
        )

    effective_gross = gross_salary
    notes: list[str] = []

    if insurance_title in (InsuranceTitle.JDG, InsuranceTitle.ZLECENIE):
        if effective_gross > params.voluntary_sickness_max_monthly_gross:
            effective_gross = params.voluntary_sickness_max_monthly_gross
            notes.append(
                f"zastosowano limit 250% przeciętnego wynagrodzenia dla dobrowolnego chorobowego ({params.voluntary_sickness_max_monthly_gross:.2f} zł brutto)"
            )

    base = effective_gross * (1.0 - rate)
    if insurance_title == InsuranceTitle.UOP:
        min_base = params.minimum_wage_gross * fte_fraction * (1.0 - rate)
        if base < min_base:
            base = min_base
            notes.append(
                f"podwyższono do minimalnej podstawy wymiaru zasiłku dla {fte_fraction:.2f} etatu w {params.year} r. ({min_base:.2f} zł)"
            )

    base_rounded = round(base, 2)
    extra = f" ({'; '.join(notes)})" if notes else ""
    explanation = (
        f"Przeciętny miesięczny przychód {gross_salary:.2f} zł brutto pomniejszony o {rate*100:.2f}% składek społecznych = {base_rounded:.2f} zł{extra}."
    )
    return base_rounded, explanation


def _determine_payer(insurance_title: InsuranceTitle, employer_insured_count: int, params: LegalParameters) -> str:
    if insurance_title in (InsuranceTitle.UOP, InsuranceTitle.ZLECENIE) and employer_insured_count > params.payer_employee_threshold:
        return f"Płatnik składek (pracodawca zgłaszający > {params.payer_employee_threshold} ubezpieczonych)"
    return "Zakład Ubezpieczeń Społecznych (ZUS)"


def calculate_pregnancy_benefit(
    req: PregnancyBenefitRequest, params: LegalParameters
) -> PregnancyBenefitResponse:
    warnings: list[str] = []

    # 1. Zasiłek chorobowy po ustaniu tytułu ubezpieczenia w ciąży (art. 7, art. 13, art. 46 ustawy zasiłkowej)
    if req.employment_terminated_special and req.termination_reason == TerminationReason.POST_EMPLOYMENT_ART7:
        base, base_expl = _compute_benefit_base_with_explanation(
            req.gross_monthly_salary,
            req.custom_benefit_base,
            None,
            req.insurance_title if req.insurance_title != InsuranceTitle.NONE else InsuranceTitle.UOP,
            params,
            fte_fraction=req.fte_fraction,
        )
        art46_cap = round(params.post_employment_sickness_cap_monthly_gross * (1.0 - params.employee_social_security_rate), 2)
        if base > art46_cap:
            base = art46_cap
            base_expl += f" Ograniczono podstawę po ustaniu ubezpieczenia do 100% przeciętnego wynagrodzenia: {art46_cap:.2f} zł (art. 46 ustawy zasiłkowej)."

        rate = params.sickness_benefit_pregnancy_rate if req.has_code_b else params.sickness_benefit_standard_rate
        daily = round((base * rate) / 30.0, 2)
        monthly = round(base * rate, 2)
        rehab_rate = params.rehabilitation_benefit_pregnancy_rate
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=True,
            eligible_maternity_equivalent=False,
            waiting_period_required_days=0,
            waiting_period_met=True,
            benefit_rate_percent=round(rate * 100, 1),
            benefit_base_monthly=base,
            benefit_base_explanation=base_expl,
            daily_benefit_gross=daily,
            monthly_benefit_gross=monthly,
            rehabilitation_monthly_gross=round(base * rehab_rate, 2),
            rehabilitation_daily_gross=round((base * rehab_rate) / 30.0, 2),
            rehabilitation_max_days=params.rehabilitation_benefit_max_days,
            max_benefit_days=params.sickness_benefit_pregnancy_max_days,
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=[
                "Zasiłek chorobowy po ustaniu ubezpieczenia (art. 7 ustawy zasiłkowej) przysługuje, jeśli niezdolność do pracy powstała do 14 dni od ustania tytułu ubezpieczenia i trwa nieprzerwanie co najmniej 30 dni. Podstawa wymiaru nie może przekroczyć 100% przeciętnego wynagrodzenia (art. 46).",
                "Uwaga (art. 13 ustawy zasiłkowej): Zasiłek po ustaniu zatrudnienia nie przysługuje m.in. w razie podjęcia innej działalności zarobkowej, prawa do emerytury/renty lub zasiłku dla bezrobotnych.",
            ],
            summary=f"Przysługuje zasiłek chorobowy po ustaniu ubezpieczenia w ciąży ({int(rate*100)}%, maks. {params.sickness_benefit_pregnancy_max_days} dni, pułap podstawy z art. 46: {art46_cap:.2f} zł) wypłacany przez ZUS.",
        )

    # 2. Zasiłek w wysokości zasiłku macierzyńskiego (art. 30 ust. 3)
    if req.employment_terminated_special and req.termination_reason in (
        TerminationReason.BANKRUPTCY_LIQUIDATION,
        TerminationReason.EMPLOYER_DEATH,
        TerminationReason.UNLAWFUL_TERMINATION_COURT_RULING,
    ):
        base, base_expl = _compute_benefit_base_with_explanation(
            req.gross_monthly_salary,
            req.custom_benefit_base,
            None,
            InsuranceTitle.UOP,
            params,
            fte_fraction=req.fte_fraction,
        )
        daily = round(base / 30.0, 2)
        rehab_rate = params.rehabilitation_benefit_pregnancy_rate
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=False,
            eligible_maternity_equivalent=True,
            waiting_period_required_days=0,
            waiting_period_met=True,
            benefit_rate_percent=round(params.maternity_rate_standard * 100, 1),
            benefit_base_monthly=base,
            benefit_base_explanation=base_expl,
            daily_benefit_gross=daily,
            monthly_benefit_gross=round(base * params.maternity_rate_standard, 2),
            rehabilitation_monthly_gross=round(base * rehab_rate, 2),
            rehabilitation_daily_gross=round((base * rehab_rate) / 30.0, 2),
            rehabilitation_max_days=params.rehabilitation_benefit_max_days,
            max_benefit_days=params.sickness_benefit_pregnancy_max_days,
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=[
                "Zasiłek w wysokości zasiłku macierzyńskiego przysługuje do dnia porodu po ustaniu zatrudnienia w szczególnych okolicznościach (upadłość/likwidacja/śmierć pracodawcy lub prawomocny wyrok sądu — art. 30 ust. 3 ustawy zasiłkowej)."
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
            benefit_base_explanation="Brak podstawy wymiaru (brak podlegania ubezpieczeniu chorobowemu).",
            daily_benefit_gross=0.0,
            monthly_benefit_gross=0.0,
            rehabilitation_monthly_gross=0.0,
            rehabilitation_daily_gross=0.0,
            rehabilitation_max_days=0,
            max_benefit_days=0,
            employer_pay_days=0,
            payer="Brak uprawnień",
            warnings=[
                "Brak podlegania ubezpieczeniu chorobowemu. Aby uzyskać prawo do zasiłku chorobowego na umowie zleceniu lub JDG, wymagane jest przystąpienie do dobrowolnego ubezpieczenia chorobowego."
            ],
            summary="Brak prawa do zasiłku chorobowego z powodu niepodlegania ubezpieczeniu chorobowemu.",
        )

    waiting_days = (
        params.waiting_period_mandatory_days
        if req.insurance_title == InsuranceTitle.UOP
        else params.waiting_period_voluntary_days
    )
    # Art. 4 ust. 3 pkt 3 (10 lat obowiązkowego ubezpieczenia) dotyczy WYŁĄCZNIE ubezpieczonych obowiązkowo (UoP)
    effective_exempt = req.waiting_period_exempt and req.insurance_title == InsuranceTitle.UOP
    waiting_met = effective_exempt or (req.insurance_days >= waiting_days)

    if req.waiting_period_exempt and req.insurance_title != InsuranceTitle.UOP:
        warnings.append(
            "Uwaga (art. 4 ust. 3 pkt 3 ustawy zasiłkowej): Zwolnienie z okresu wyczekiwania z tytułu 10-letniego stażu obowiązkowego ubezpieczenia chorobowego przysługuje wyłącznie ubezpieczonym obowiązkowo (umowa o pracę). Dla ubezpieczenia dobrowolnego (JDG/zlecenie) obowiązuje 90 dni wyczekiwania (poza szczególnymi wyjątkami np. wypadek w drodze do/z pracy)."
        )
    elif effective_exempt and req.insurance_days < waiting_days:
        warnings.append(
            "Zastosowano ustawowe zwolnienie z okresu wyczekiwania (art. 4 ust. 3 ustawy zasiłkowej — min. 10-letni okres obowiązkowego ubezpieczenia chorobowego lub absolwent szkoły/uczelni w ciągu 90 dni)."
        )
    elif not waiting_met:
        warnings.append(
            f"Nie upłynął okres wyczekiwania ({req.insurance_days}/{waiting_days} dni). Prawo do zasiłku powstanie po osiągnięciu {waiting_days} dni nieprzerwanego ubezpieczenia (wlicza się poprzednie okresy, jeśli przerwa nie przekroczyła 30 dni — art. 4 ust. 2)."
        )

    debt_threshold = round(params.minimum_wage_gross * params.debt_threshold_min_wage_fraction, 2)
    if req.insurance_title == InsuranceTitle.JDG and req.contribution_debt_pln > debt_threshold:
        warnings.append(
            f"UWAGA (art. 2a ustawy zasiłkowej): Wykazano zadłużenie z tytułu składek ZUS ({req.contribution_debt_pln:.2f} zł), które przekracza {params.debt_threshold_min_wage_fraction*100:.1f}% minimalnego wynagrodzenia ({debt_threshold:.2f} zł). Wypłata zasiłku zostanie wstrzymana do czasu spłaty całości zadłużenia (po {params.claim_limitation_months} miesiącach prawo ulega przedawnieniu)."
        )

    # Art. 11 ust. 2 pkt 1: ciąża daje 100% z mocy ustawy; kod "B" jest dowodem na e-ZLA
    rate = params.sickness_benefit_pregnancy_rate if req.has_code_b else params.sickness_benefit_standard_rate
    if not req.has_code_b:
        warnings.append(
            f"Zgodnie z art. 11 ust. 2 pkt 1 ustawy zasiłkowej zasiłek chorobowy w okresie ciąży wynosi 100% podstawy wymiaru. Kod literowy „B” na e-ZLA stanowi dowód stanu ciąży — bez niego płatnik/ZUS wypłaci wstępnie {int(params.sickness_benefit_standard_rate*100)}%, ale po dostarczeniu odrębnego zaświadczenia lekarskiego o ciąży przysługuje pełne wyrównanie do 100%."
        )

    base, base_expl = _compute_benefit_base_with_explanation(
        req.gross_monthly_salary,
        req.custom_benefit_base,
        None,
        req.insurance_title,
        params,
        fte_fraction=req.fte_fraction,
    )
    daily = round((base * rate) / 30.0, 2)
    monthly = round(base * rate, 2)
    rehab_rate = params.rehabilitation_benefit_pregnancy_rate
    rehab_monthly = round(base * rehab_rate, 2)
    rehab_daily = round((base * rehab_rate) / 30.0, 2)

    employer_days = 0
    if req.insurance_title == InsuranceTitle.UOP:
        employer_days = (
            params.sickness_pay_employer_days_over_50
            if req.age_over_50
            else params.sickness_pay_employer_days_under_50
        )

    payer = _determine_payer(req.insurance_title, req.employer_insured_count, params)
    summary = (
        f"Przysługuje zasiłek chorobowy w ciąży w wysokości {int(rate * 100)}% podstawy wymiaru (maks. {params.sickness_benefit_pregnancy_max_days} dni), a po jego wyczerpaniu świadczenie rehabilitacyjne w ciąży ({int(rehab_rate*100)}% podstawy wymiaru, do {params.rehabilitation_benefit_max_days} dni)."
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
        benefit_base_explanation=base_expl,
        daily_benefit_gross=daily,
        monthly_benefit_gross=monthly,
        rehabilitation_monthly_gross=rehab_monthly,
        rehabilitation_daily_gross=rehab_daily,
        rehabilitation_max_days=params.rehabilitation_benefit_max_days,
        max_benefit_days=params.sickness_benefit_pregnancy_max_days,
        employer_pay_days=employer_days,
        payer=payer,
        warnings=warnings,
        summary=summary,
    )


def _compute_supplementary_weeks(
    req: IntegratedCalculatorRequest, params: LegalParameters, warnings: list[str]
) -> int:
    if not req.premature_or_hospitalized or req.hospitalization_weeks <= 0:
        return 0
    is_extreme = (req.gestation_week is not None and req.gestation_week < 28) or (
        req.birth_weight_grams is not None and req.birth_weight_grams <= 1000
    )
    if not is_extreme and req.gestation_week is not None and req.gestation_week >= 37:
        warnings.append(
            "Dla dziecka urodzonego po ukończeniu 37. tygodnia ciąży uzupełniający urlop macierzyński (do 8 tyg.) przysługuje pod warunkiem, że pobyt dziecka w szpitalu trwał co najmniej 2 kolejne dni, a pierwszy z nich przypadał w okresie od 5. do 28. dnia po porodzie (art. 180² § 1 pkt 3 Kodeksu pracy)."
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
    top_up_applied = False
    min_monthly_floor = params.parental_benefit_minimum_monthly

    def _calc_amount(base: float, rate: float, weeks: float, fte_work: float = 0.0) -> tuple[float, float]:
        nonlocal top_up_applied
        effective_fraction = 1.0 - fte_work
        raw_full_monthly = round(base * rate, 2)
        if raw_full_monthly < min_monthly_floor and base >= 0:
            full_monthly = min_monthly_floor
            top_up_applied = True
        else:
            full_monthly = raw_full_monthly
        monthly = round(full_monthly * effective_fraction, 2)
        total = round((monthly / 30.0) * (weeks * 7.0), 2)
        return monthly, total

    p2_eligible = (
        not req.single_parent_or_no_second_parent
        and req.second_parent_has_sickness_insurance
        and req.second_parent_insurance_title != InsuranceTitle.NONE
    )

    # Sytuacja: Matka (Rodzic 1) nie podlega ubezpieczeniu chorobowemu w dniu porodu
    if req.insurance_title == InsuranceTitle.NONE or not req.has_sickness_insurance_on_birth_date:
        if not req.second_parent_insured_claim or not p2_eligible:
            return IntegratedCalculatorResponse(
                eligible=False,
                ineligibility_reason="Brak podlegania ubezpieczeniu chorobowemu na dzień porodu lub przyjęcia dziecka na wychowanie.",
                benefit_base_parent1=0.0,
                benefit_base_parent2=0.0,
                benefit_base_explanation="Brak podstawy wymiaru — osoba nie podlega ubezpieczeniu chorobowemu.",
                benefit_base_parent2_explanation=None,
                minimum_benefit_top_up_applied=False,
                equalization_to_100_pln=0.0,
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
                    f"Zasiłek macierzyński wymaga podlegania ubezpieczeniu chorobowemu w dniu porodu/przyjęcia dziecka. Sprawdź świadczenie rodzicielskie (Kosiniakowe — {min_monthly_floor:.0f} zł/mies.) lub uprawnienia ubezpieczonego drugiego rodzica (art. 31 ust. 3h ustawy zasiłkowej)."
                ],
                required_documents=[],
            )

        p2_gross = req.second_parent_gross_salary if req.second_parent_gross_salary is not None else req.gross_monthly_salary
        base_p2, base_p2_expl = _compute_benefit_base_with_explanation(
            p2_gross,
            req.second_parent_custom_base,
            None,
            req.second_parent_insurance_title,
            params,
            fte_fraction=req.second_parent_fte_fraction,
        )
        parental_pool = (
            (params.parental_weeks_za_zyciem_single if req.children_count == 1 else params.parental_weeks_za_zyciem_multiple)
            if req.has_za_zyciem_certificate
            else (params.parental_weeks_single if req.children_count == 1 else params.parental_weeks_multiple)
        )
        max_father_parental = max(0, parental_pool - params.parental_non_transferable_weeks)
        requested_father_par = req.father_takes_parental_weeks if req.father_takes_parental_weeks > 0 else max_father_parental
        father_par_weeks = min(requested_father_par, max_father_parental)
        breakdown_uninsured: list[LeaveBreakdownItem] = []

        if father_par_weeks > 0:
            fp_m, fp_t = _calc_amount(base_p2, params.parental_rate_standard, father_par_weeks)
            breakdown_uninsured.append(
                LeaveBreakdownItem(
                    label="Urlop rodzicielski ojca (gdy matka nie podlega ubezpieczeniu — art. 31 ust. 3h)",
                    parent="Ojciec (ubezpieczony)",
                    weeks=float(father_par_weeks),
                    rate_percent=round(params.parental_rate_standard * 100, 1),
                    monthly_gross_pln=fp_m,
                    total_gross_pln=fp_t,
                    notes="Finansowany z dotacji budżetu państwa do FUS (art. 31 ust. 3h ustawy zasiłkowej).",
                )
            )

        pat_weeks = params.paternity_weeks if (req.father_takes_paternity_leave and req.scenario != BenefitScenario.FOSTER) else 0
        if pat_weeks > 0:
            pt_m, pt_t = _calc_amount(base_p2, params.paternity_rate, pat_weeks)
            breakdown_uninsured.append(
                LeaveBreakdownItem(
                    label="Urlop ojcowski (art. 182³ KP)",
                    parent="Ojciec (ubezpieczony)",
                    weeks=float(pat_weeks),
                    rate_percent=round(params.paternity_rate * 100, 1),
                    monthly_gross_pln=pt_m,
                    total_gross_pln=pt_t,
                )
            )

        payer_p2 = _determine_payer(req.second_parent_insurance_title, req.employer_insured_count, params)
        return IntegratedCalculatorResponse(
            eligible=True,
            benefit_base_parent1=0.0,
            benefit_base_parent2=base_p2,
            benefit_base_explanation="Matka (Rodzic 1) nie podlega ubezpieczeniu chorobowemu — brak prawa do zasiłku dla matki.",
            benefit_base_parent2_explanation=base_p2_expl,
            minimum_benefit_top_up_applied=top_up_applied,
            equalization_to_100_pln=0.0,
            total_weeks=round(sum(x.weeks for x in breakdown_uninsured), 1),
            maternity_weeks=0,
            supplementary_maternity_weeks=0,
            parental_weeks_total=float(father_par_weeks),
            parental_weeks_extended_by_work=0.0,
            paternity_weeks=pat_weeks,
            payer=payer_p2,
            breakdown=breakdown_uninsured,
            total_estimated_gross_pln=round(sum(x.total_gross_pln for x in breakdown_uninsured), 2),
            warnings=[
                "Matka dziecka nie podlega ubezpieczeniu chorobowemu w dniu porodu, dlatego nie nabywa prawa do zasiłku za urlop macierzyński. Ubezpieczony ojciec ma jednak niezależne prawo do zasiłku za urlop rodzicielski (70%, art. 31 ust. 3h) oraz urlop ojcowski (2 tyg., 100%)."
            ],
            required_documents=[
                "Wniosek ojca o urlop rodzicielski / zasiłek macierzyński ZAM",
                "Odpis skrócony aktu urodzenia dziecka",
                "Oświadczenie o braku podlegania przez matkę dziecka ubezpieczeniu chorobowemu",
            ],
        )

    # Wyłączenie rodziny zastępczej zawodowej
    if req.scenario == BenefitScenario.FOSTER and req.foster_family_type == FosterFamilyType.PROFESSIONAL:
        return IntegratedCalculatorResponse(
            eligible=False,
            ineligibility_reason=(
                "Brak prawa do urlopu na warunkach urlopu macierzyńskiego, urlopu rodzicielskiego oraz zasiłku "
                "macierzyńskiego dla osób pełniących funkcję rodziny zastępczej zawodowej (art. 29 ust. 1 pkt 3 ustawy zasiłkowej)."
            ),
            benefit_base_parent1=0.0,
            benefit_base_parent2=0.0,
            benefit_base_explanation="Wyłączenie ustawowe dla rodzin zastępczych zawodowych.",
            benefit_base_parent2_explanation=None,
            minimum_benefit_top_up_applied=False,
            equalization_to_100_pln=0.0,
            total_weeks=0.0,
            maternity_weeks=0,
            supplementary_maternity_weeks=0,
            parental_weeks_total=0.0,
            parental_weeks_extended_by_work=0.0,
            paternity_weeks=0,
            payer="Brak uprawnień (rodzina zastępcza zawodowa)",
            breakdown=[],
            total_estimated_gross_pln=0.0,
            warnings=[
                "Zasiłek macierzyński z tytułu rodziny zastępczej przysługuje wyłącznie rodzinom zastępczym niezawodowym (w tym spokrewnionym)."
            ],
            required_documents=[],
        )

    # Zadłużenie JDG (art. 2a) + informacja o automatycznym wyrejestrowaniu z dobrowolnego chorobowego
    debt_threshold = round(params.minimum_wage_gross * params.debt_threshold_min_wage_fraction, 2)
    if req.insurance_title == InsuranceTitle.JDG:
        if req.contribution_debt_pln > debt_threshold:
            warnings.append(
                f"UWAGA (art. 2a ustawy zasiłkowej): Zadłużenie ZUS ({req.contribution_debt_pln:.2f} zł > {params.debt_threshold_min_wage_fraction*100:.1f}% płacy minimalnej tj. {debt_threshold:.2f} zł) wstrzymuje wypłatę zasiłku do czasu spłaty (przedawnienie po {params.claim_limitation_months} miesiącach)."
            )
        warnings.append(
            "Informacja dla JDG (Poradnik ZUS): Rozpoczęcie pobierania zasiłku macierzyńskiego powoduje ustanie dobrowolnego ubezpieczenia chorobowego. Po zakończeniu zasiłku, aby ponownie podlegać chorobowemu, należy złożyć zgłoszenie ZUS ZUA."
        )

    # Podstawa wymiaru Rodzica 1 i Rodzica 2 (z poszanowaniem tytułu ubezpieczenia obu rodziców!)
    base_p1, base_p1_expl = _compute_benefit_base_with_explanation(
        req.gross_monthly_salary,
        req.custom_benefit_base,
        req.individual_base_config,
        req.insurance_title,
        params,
        fte_fraction=req.fte_fraction,
    )
    if p2_eligible:
        p2_gross = req.second_parent_gross_salary if req.second_parent_gross_salary is not None else req.gross_monthly_salary
        base_p2, base_p2_expl = _compute_benefit_base_with_explanation(
            p2_gross,
            req.second_parent_custom_base,
            None,
            req.second_parent_insurance_title,
            params,
            fte_fraction=req.second_parent_fte_fraction,
        )
    else:
        base_p2 = 0.0
        base_p2_expl = (
            "Rodzic samotny / brak drugiego rodzica uprawnionego do zasiłku."
            if req.single_parent_or_no_second_parent
            else "Drugi rodzic nie podlega ubezpieczeniu chorobowemu."
        )

    payer = _determine_payer(req.insurance_title, req.employer_insured_count, params)

    # Urodzenie martwego dziecka lub zgon dziecka przed upływem 8 tygodni życia (art. 180¹ § 1 KP)
    if req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death:
        if req.children_count == 1:
            sb_weeks = params.stillbirth_maternity_weeks
            sb_monthly, sb_total = _calc_amount(base_p1, params.maternity_rate_standard, sb_weeks)
            return IntegratedCalculatorResponse(
                eligible=True,
                benefit_base_parent1=base_p1,
                benefit_base_parent2=base_p2,
                benefit_base_explanation=base_p1_expl,
                benefit_base_parent2_explanation=base_p2_expl,
                minimum_benefit_top_up_applied=top_up_applied,
                equalization_to_100_pln=0.0,
                total_weeks=float(sb_weeks),
                maternity_weeks=sb_weeks,
                supplementary_maternity_weeks=0,
                parental_weeks_total=0.0,
                parental_weeks_extended_by_work=0.0,
                paternity_weeks=0,
                payer=payer,
                breakdown=[
                    LeaveBreakdownItem(
                        label="Urlop macierzyński po urodzeniu martwego dziecka / zgonie dziecka (art. 180¹ § 1 KP)",
                        parent="Matka",
                        weeks=float(sb_weeks),
                        rate_percent=round(params.maternity_rate_standard * 100, 1),
                        monthly_gross_pln=sb_monthly,
                        total_gross_pln=sb_total,
                        notes=f"Wymiar {sb_weeks} tygodni po porodzie, nie krócej niż {params.child_death_min_days} dni od dnia zgonu dziecka.",
                    )
                ],
                total_estimated_gross_pln=sb_total,
                warnings=[
                    f"Zgodnie z art. 180¹ § 1 Kodeksu pracy przysługuje urlop i zasiłek macierzyński (100%) w wymiarze {sb_weeks} tygodni po porodzie (nie krócej niż {params.child_death_min_days} dni od dnia zgonu).",
                    f"Wsparcie dodatkowe (Poradnik ZUS 2026): W przypadku urodzenia martwego dziecka rodzinie przysługuje również zasiłek pogrzebowy z ZUS w wysokości {params.funeral_grant_pln:,.0f} zł (po przedłożeniu aktu urodzenia z adnotacją o martwym urodzeniu).".replace(",", " "),
                ],
                required_documents=[
                    "Odpis skrócony aktu urodzenia dziecka z adnotacją o urodzeniu martwym (lub odpis aktu zgonu dziecka)",
                    "Wniosek o urlop macierzyński (do pracodawcy) lub wniosek ZAM (do ZUS)",
                    f"Wniosek Z-12 o zasiłek pogrzebowy ({params.funeral_grant_pln:,.0f} zł) — opcjonalnie".replace(",", " "),
                ],
            )
        else:
            surviving = req.children_count - 1
            warnings.append(
                f"Przy porodzie mnogim, w którym jedno z dzieci urodziło się martwe lub zmarło, przysługuje urlop macierzyński stosowny do liczby dzieci pozostałych przy życiu ({surviving}), nie krócej niż {params.stillbirth_maternity_weeks} tygodni (art. 180¹ § 1 KP)."
            )

    # Limity wieku dla adopcji i rodziny zastępczej
    apply_reduced_9_weeks_regime = req.adoption_short_period_9_weeks
    weeks_until_age_limit: int | None = None

    if req.scenario == BenefitScenario.FOSTER:
        max_age = params.foster_deferred_school_max_child_age if req.foster_deferred_school else params.foster_max_child_age
        if req.child_age_years is not None:
            if req.child_age_years >= max_age:
                return IntegratedCalculatorResponse(
                    eligible=False,
                    ineligibility_reason=f"Wiek dziecka ({req.child_age_years} lat) przekracza lub osiągnął ustawowy limit {max_age} roku życia dla rodziny zastępczej niezawodowej.",
                    benefit_base_parent1=0.0,
                    benefit_base_parent2=0.0,
                    minimum_benefit_top_up_applied=False,
                    equalization_to_100_pln=0.0,
                    total_weeks=0.0,
                    maternity_weeks=0,
                    supplementary_maternity_weeks=0,
                    parental_weeks_total=0.0,
                    parental_weeks_extended_by_work=0.0,
                    paternity_weeks=0,
                    payer="Brak uprawnień (przekroczony wiek dziecka)",
                    breakdown=[],
                    total_estimated_gross_pln=0.0,
                    warnings=[f"Dla rodziny zastępczej niezawodowej zasiłek przysługuje do ukończenia przez dziecko {max_age} roku życia."],
                    required_documents=[],
                )
            weeks_until_age_limit = max(1, int(round((max_age - req.child_age_years) * params.weeks_per_year)))
    elif req.scenario == BenefitScenario.ADOPTION:
        max_age = params.adoption_max_child_age
        if req.child_age_years is not None:
            if req.child_age_years >= max_age:
                return IntegratedCalculatorResponse(
                    eligible=False,
                    ineligibility_reason=f"Wiek przysposabianego dziecka ({req.child_age_years} lat) przekracza lub osiągnął ustawowy limit {max_age} roku życia.",
                    benefit_base_parent1=0.0,
                    benefit_base_parent2=0.0,
                    minimum_benefit_top_up_applied=False,
                    equalization_to_100_pln=0.0,
                    total_weeks=0.0,
                    maternity_weeks=0,
                    supplementary_maternity_weeks=0,
                    parental_weeks_total=0.0,
                    parental_weeks_extended_by_work=0.0,
                    paternity_weeks=0,
                    payer="Brak uprawnień (przekroczony wiek dziecka)",
                    breakdown=[],
                    total_estimated_gross_pln=0.0,
                    warnings=[f"Przy przysposobieniu zasiłek macierzyński przysługuje do ukończenia przez dziecko {max_age} roku życia."],
                    required_documents=[],
                )
            weeks_until_age_limit = max(1, int(round((max_age - req.child_age_years) * params.weeks_per_year)))

    # Wymiar urlopu macierzyńskiego
    effective_children = (
        max(1, req.children_count - 1)
        if (req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death and req.children_count > 1)
        else req.children_count
    )
    child_key = str(min(effective_children, 5))
    standard_maternity_weeks = params.maternity_weeks_by_children.get(child_key, 20)
    maternity_weeks = standard_maternity_weeks

    if req.scenario == BenefitScenario.BIRTH and req.pre_birth_maternity_weeks > 0:
        pre_weeks = min(req.pre_birth_maternity_weeks, params.maternity_pre_birth_max_weeks)
        warnings.append(
            f"Uwzględniono {pre_weeks} tyg. urlopu macierzyńskiego przed porodem (maks. {params.maternity_pre_birth_max_weeks} tyg. — art. 180 § 2 KP). Po porodzie pozostaje {maternity_weeks - pre_weeks} tyg."
        )

    if req.scenario in (BenefitScenario.ADOPTION, BenefitScenario.FOSTER):
        min_mat = params.adoption_foster_min_maternity_weeks
        if apply_reduced_9_weeks_regime or (weeks_until_age_limit is not None and weeks_until_age_limit <= min_mat):
            apply_reduced_9_weeks_regime = True
            maternity_weeks = min_mat
            warnings.append(
                f"Zastosowano minimalny wymiar {min_mat} tyg. urlopu na warunkach macierzyńskiego (art. 183 § 3 KP) oraz {params.adoption_foster_reduced_parental_weeks_za_zyciem if req.has_za_zyciem_certificate else params.adoption_foster_reduced_parental_weeks} tyg. rodzicielskiego."
            )
        elif weeks_until_age_limit is not None and weeks_until_age_limit < standard_maternity_weeks:
            maternity_weeks = max(min_mat, weeks_until_age_limit)
            warnings.append(
                f"Wymiar urlopu na warunkach macierzyńskiego dostosowano do wieku dziecka ({maternity_weeks} tyg., nie mniej niż {min_mat} tyg.)."
            )

    supplementary_weeks = _compute_supplementary_weeks(req, params, warnings)
    if supplementary_weeks > 0:
        docs.append("Zaświadczenie wydane przez szpital o okresie hospitalizacji i masie/tygodniu urodzenia dziecka")

    if req.scenario in (BenefitScenario.ADOPTION, BenefitScenario.FOSTER) and apply_reduced_9_weeks_regime:
        parental_base_weeks = (
            params.adoption_foster_reduced_parental_weeks_za_zyciem
            if req.has_za_zyciem_certificate
            else params.adoption_foster_reduced_parental_weeks
        )
        if req.has_za_zyciem_certificate:
            docs.append("Zaświadczenie lekarskie 'Za życiem' (art. 4 ust. 3 ustawy)")
    elif req.has_za_zyciem_certificate:
        parental_base_weeks = (
            params.parental_weeks_za_zyciem_single
            if effective_children == 1
            else params.parental_weeks_za_zyciem_multiple
        )
        docs.append("Zaświadczenie lekarskie 'Za życiem' (art. 4 ust. 3 ustawy)")
    else:
        parental_base_weeks = (
            params.parental_weeks_single if effective_children == 1 else params.parental_weeks_multiple
        )

    if req.scenario == BenefitScenario.ADOPTION:
        if req.previously_used_foster_maternity_weeks > 0:
            maternity_weeks = max(0, maternity_weeks - req.previously_used_foster_maternity_weeks)
            warnings.append(
                f"Wymiar urlopu na warunkach macierzyńskiego obniżono o {req.previously_used_foster_maternity_weeks} tyg. wykorzystanych wcześniej jako rodzina zastępcza (art. 183 § 7 KP)."
            )
        if req.previously_used_foster_parental_weeks > 0:
            parental_base_weeks = max(0, parental_base_weeks - req.previously_used_foster_parental_weeks)
            warnings.append(
                f"Wymiar urlopu rodzicielskiego obniżono o {req.previously_used_foster_parental_weeks} tyg. wykorzystanych wcześniej jako rodzina zastępcza (art. 183 § 8 KP)."
            )

    # Podział macierzyńskiego
    if not p2_eligible:
        mother_mat = maternity_weeks
        father_mat = 0
    elif req.scenario == BenefitScenario.BIRTH:
        min_mother_weeks = 8 if req.mother_early_transfer_8_weeks else params.maternity_min_mother_weeks
        mother_mat = req.mother_maternity_weeks if req.mother_maternity_weeks is not None else maternity_weeks
        if mother_mat < min_mother_weeks:
            warnings.append(
                f"Pierwsze {min_mother_weeks} tygodni urlopu macierzyńskiego po porodzie matka musi wykorzystać osobiście. Skorygowano podział w symulacji."
            )
            mother_mat = min_mother_weeks
        mother_mat = min(mother_mat, maternity_weeks)
        father_mat = maternity_weeks - mother_mat
    else:
        mother_mat = min(req.mother_maternity_weeks, maternity_weeks) if req.mother_maternity_weeks is not None else maternity_weeks
        father_mat = max(0, maternity_weeks - mother_mat)

    # Podział rodzicielskiego (art. 182¹ᵃ § 4 KP: 9 tyg. nieprzenoszalnych dla każdego rodzica)
    non_transferable = params.parental_non_transferable_weeks
    max_single_parent_parental = max(0, parental_base_weeks - non_transferable)

    if not p2_eligible:
        father_parental = 0
        if req.single_parent_or_no_second_parent:
            warnings.append(
                f"Rodzic samotny / brak drugiego rodzica uprawnionego: zgodnie z art. 182¹ᵃ § 4 KP część nieprzenoszalna ({non_transferable} tyg.) nie przechodzi na pierwszego rodzica (maksymalny wymiar dla jednego rodzica wynosi {max_single_parent_parental} tyg. z puli {parental_base_weeks} tyg.)."
            )
        else:
            warnings.append(
                f"Drugi rodzic nie podlega ubezpieczeniu chorobowemu — nie pobiera zasiłku macierzyńskiego za swoją część ({non_transferable} tyg. nieprzenoszalne)."
            )
    else:
        if req.father_takes_parental_weeks > max_single_parent_parental:
            warnings.append(
                f"Jeden rodzic może wykorzystać maksymalnie {max_single_parent_parental} tyg. urlopu rodzicielskiego (skorygowano z {req.father_takes_parental_weeks} tyg.)."
            )
        father_parental = min(req.father_takes_parental_weeks, max_single_parent_parental)
        if father_parental < non_transferable and parental_base_weeks >= non_transferable:
            warnings.append(
                f"Drugiemu rodzicowi przysługuje {non_transferable} tyg. nieprzenoszalnego urlopu rodzicielskiego (art. 182¹ᵃ § 4 KP). Niewykorzystana część przepada."
            )

    default_mother_parental = max(0, min(max_single_parent_parental, parental_base_weeks - father_parental))
    if req.mother_takes_parental_weeks is not None:
        mother_parental = min(req.mother_takes_parental_weeks, default_mother_parental)
    else:
        mother_parental = default_mother_parental

    # Łączenie urlopu rodzicielskiego z pracą — Rodzic 1
    extended_weeks_p1 = 0.0
    effective_work_weeks_p1 = 0
    fte_p1 = 0.0
    if req.combine_parental_with_work and req.work_fte_fraction > 0 and req.combined_work_weeks > 0:
        if req.insurance_title != InsuranceTitle.UOP:
            warnings.append(
                "Łączenie urlopu rodzicielskiego z pracą (do 1/2 etatu) z proporcjonalnym wydłużeniem dotyczy pracowników na umowie o pracę (art. 182¹ᵉ § 1 KP)."
            )
        else:
            fte_p1 = min(req.work_fte_fraction, params.parental_work_max_fte)
            effective_work_weeks_p1 = min(req.combined_work_weeks, mother_parental)
            raw_ext = (
                effective_work_weeks_p1 * fte_p1 / (1.0 - fte_p1)
                if req.work_during_extended_part
                else effective_work_weeks_p1 * fte_p1
            )
            extended_weeks_p1 = round(min(raw_ext, float(parental_base_weeks)), 2)

    # Łączenie urlopu rodzicielskiego z pracą — Rodzic 2
    extended_weeks_p2 = 0.0
    effective_work_weeks_p2 = 0
    fte_p2 = 0.0
    if p2_eligible and req.father_combine_parental_with_work and req.father_work_fte_fraction > 0 and req.father_combined_work_weeks > 0:
        if req.second_parent_insurance_title != InsuranceTitle.UOP:
            warnings.append(
                "Łączenie urlopu rodzicielskiego z pracą dla drugiego rodzica z proporcjonalnym wydłużeniem przysługuje wyłącznie przy umowie o pracę (art. 182¹ᵉ § 1 KP)."
            )
        else:
            fte_p2 = min(req.father_work_fte_fraction, params.parental_work_max_fte)
            effective_work_weeks_p2 = min(req.father_combined_work_weeks, father_parental)
            raw_ext_p2 = (
                effective_work_weeks_p2 * fte_p2 / (1.0 - fte_p2)
                if req.father_work_during_extended_part
                else effective_work_weeks_p2 * fte_p2
            )
            extended_weeks_p2 = round(min(raw_ext_p2, float(parental_base_weeks)), 2)

    total_extended_weeks = round(extended_weeks_p1 + extended_weeks_p2, 2)

    # Stawki procentowe + wyrównanie do 100% (art. 31 ust. 4)
    equalization_to_100_pln = 0.0
    if req.payment_variant == PaymentVariant.COMBINED_81_5:
        mat_rate = params.combined_21_days_rate
        mother_parental_rate = params.combined_21_days_rate
        father_shared_parental_rate = params.combined_21_days_rate
        father_non_transferable_rate = params.non_transferable_parental_rate
        warnings.append(
            f"Wariant 81,5% wymaga złożenia wniosku lub pisemnej deklaracji w nieprzekraczalnym terminie {params.combined_application_deadline_days} dni po porodzie/przyjęciu dziecka (art. 30a ustawy zasiłkowej). Część nieprzenoszalna drugiego rodzica ({non_transferable} tyg.) jest zawsze płatna {round(father_non_transferable_rate*100, 1)}%."
        )
        if mother_parental == 0 and father_parental == 0 and mother_mat > 0:
            diff_rate = max(0.0, params.maternity_rate_standard - params.combined_21_days_rate)
            equalization_to_100_pln = round((base_p1 * diff_rate / 30.0) * (mother_mat * 7.0), 2)
            warnings.append(
                f"Wyrównanie do 100% (art. 31 ust. 4 ustawy zasiłkowej): Ponieważ nie zaplanowano żadnego dnia urlopu rodzicielskiego w pierwszym roku życia dziecka, przysługuje jednorazowe wyrównanie zasiłku za urlop macierzyński do 100% w szacowanej kwocie {equalization_to_100_pln:.2f} zł brutto."
            )
    else:
        mat_rate = params.maternity_rate_standard
        mother_parental_rate = params.parental_rate_standard
        father_shared_parental_rate = params.parental_rate_standard
        father_non_transferable_rate = params.parental_rate_standard

    breakdown: list[LeaveBreakdownItem] = []
    if req.scenario == BenefitScenario.BIRTH:
        p1_label, p2_label = "Matka", "Ojciec"
    elif req.scenario == BenefitScenario.ADOPTION:
        p1_label, p2_label = "Rodzic adopcyjny 1", "Rodzic adopcyjny 2"
    else:
        p1_label, p2_label = "Rodzic zastępczy 1 (niezawodowy)", "Rodzic zastępczy 2 (niezawodowy)"

    # 1. Macierzyński / na warunkach
    if mother_mat > 0:
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
                label="Przejęta część urlopu macierzyńskiego" if req.scenario == BenefitScenario.BIRTH else "Część urlopu na warunkach macierzyńskiego",
                parent=p2_label,
                weeks=float(father_mat),
                rate_percent=round(mat_rate * 100, 1),
                monthly_gross_pln=fm_monthly,
                total_gross_pln=fm_total,
            )
        )

    # 2. Uzupełniający urlop macierzyński
    if supplementary_weeks > 0:
        s_monthly, s_total = _calc_amount(base_p1, params.supplementary_maternity_rate, supplementary_weeks)
        breakdown.append(
            LeaveBreakdownItem(
                label="Uzupełniający urlop macierzyński (wcześniak / hospitalizacja)",
                parent=p1_label,
                weeks=float(supplementary_weeks),
                rate_percent=round(params.supplementary_maternity_rate * 100, 1),
                monthly_gross_pln=s_monthly,
                total_gross_pln=s_total,
                notes="Udzielany jednorazowo bezpośrednio po urlopie macierzyńskim (wniosek min. 21 dni przed końcem macierzyńskiego).",
            )
        )

    # Helper do rozbicia urlopu rodzicielskiego z ewentualnym łączeniem z pracą
    def _append_parental_with_work(
        parent_label: str,
        base_val: float,
        parental_weeks: int,
        rate_val: float,
        eff_work: int,
        fte_val: float,
        ext_weeks: float,
        work_in_ext: bool,
        base_label: str,
    ):
        if ext_weeks > 0 and eff_work > 0:
            full_weeks = parental_weeks - eff_work
            if full_weeks > 0:
                fl_m, fl_t = _calc_amount(base_val, rate_val, full_weeks)
                breakdown.append(
                    LeaveBreakdownItem(
                        label=f"{base_label} (pełny wymiar)",
                        parent=parent_label,
                        weeks=float(full_weeks),
                        rate_percent=round(rate_val * 100, 1),
                        monthly_gross_pln=fl_m,
                        total_gross_pln=fl_t,
                    )
                )
            if work_in_ext:
                comb_weeks = round(float(eff_work) + ext_weeks, 2)
                cw_m, cw_t = _calc_amount(base_val, rate_val, comb_weeks, fte_work=fte_val)
                breakdown.append(
                    LeaveBreakdownItem(
                        label=f"{base_label} łączony z pracą ({fte_val} etatu) + wydłużenie (+{ext_weeks} tyg.)",
                        parent=parent_label,
                        weeks=comb_weeks,
                        rate_percent=round(rate_val * (1.0 - fte_val) * 100, 2),
                        monthly_gross_pln=cw_m,
                        total_gross_pln=cw_t,
                        notes=f"Art. 182¹ᶠ § 7 KP: zasiłek pomniejszony proporcjonalnie o {int(fte_val*100)}%.",
                    )
                )
            else:
                cw_m, cw_t = _calc_amount(base_val, rate_val, float(eff_work), fte_work=fte_val)
                breakdown.append(
                    LeaveBreakdownItem(
                        label=f"{base_label} łączony z pracą ({fte_val} etatu)",
                        parent=parent_label,
                        weeks=float(eff_work),
                        rate_percent=round(rate_val * (1.0 - fte_val) * 100, 2),
                        monthly_gross_pln=cw_m,
                        total_gross_pln=cw_t,
                    )
                )
                ex_m, ex_t = _calc_amount(base_val, rate_val, ext_weeks)
                breakdown.append(
                    LeaveBreakdownItem(
                        label=f"Wydłużona część urlopu rodzicielskiego (bez pracy, art. 182¹ᶠ § 2 KP)",
                        parent=parent_label,
                        weeks=ext_weeks,
                        rate_percent=round(rate_val * 100, 1),
                        monthly_gross_pln=ex_m,
                        total_gross_pln=ex_t,
                    )
                )
        else:
            mp_m, mp_t = _calc_amount(base_val, rate_val, parental_weeks)
            breakdown.append(
                LeaveBreakdownItem(
                    label=base_label,
                    parent=parent_label,
                    weeks=float(parental_weeks),
                    rate_percent=round(rate_val * 100, 1),
                    monthly_gross_pln=mp_m,
                    total_gross_pln=mp_t,
                )
            )

    # 3. Urlop rodzicielski rodzica 1
    if mother_parental > 0:
        _append_parental_with_work(
            p1_label,
            base_p1,
            mother_parental,
            mother_parental_rate,
            effective_work_weeks_p1,
            fte_p1,
            extended_weeks_p1,
            req.work_during_extended_part,
            "Urlop rodzicielski",
        )

    # 4. Urlop rodzicielski rodzica 2
    if father_parental > 0:
        if (
            req.payment_variant == PaymentVariant.COMBINED_81_5
            and father_parental > non_transferable
            and father_shared_parental_rate != father_non_transferable_rate
            and extended_weeks_p2 == 0
        ):
            shared_fw = father_parental - non_transferable
            f_sh_m, f_sh_t = _calc_amount(base_p2, father_shared_parental_rate, shared_fw)
            breakdown.append(
                LeaveBreakdownItem(
                    label="Urlop rodzicielski (część z puli wspólnej)",
                    parent=p2_label,
                    weeks=float(shared_fw),
                    rate_percent=round(father_shared_parental_rate * 100, 1),
                    monthly_gross_pln=f_sh_m,
                    total_gross_pln=f_sh_t,
                )
            )
            f_nt_m, f_nt_t = _calc_amount(base_p2, father_non_transferable_rate, non_transferable)
            breakdown.append(
                LeaveBreakdownItem(
                    label=f"Urlop rodzicielski ({non_transferable} tyg. nieprzenoszalnych)",
                    parent=p2_label,
                    weeks=float(non_transferable),
                    rate_percent=round(father_non_transferable_rate * 100, 1),
                    monthly_gross_pln=f_nt_m,
                    total_gross_pln=f_nt_t,
                )
            )
        else:
            _append_parental_with_work(
                p2_label,
                base_p2,
                father_parental,
                father_non_transferable_rate,
                effective_work_weeks_p2,
                fte_p2,
                extended_weeks_p2,
                req.father_work_during_extended_part,
                f"Urlop rodzicielski (w tym do {non_transferable} tyg. nieprzenoszalnych)",
            )

    # 5. Urlop ojcowski
    paternity_weeks = 0
    if req.father_takes_paternity_leave and p2_eligible:
        if req.scenario == BenefitScenario.FOSTER:
            warnings.append("Urlop ojcowski (2 tygodnie) przysługuje ojcu biologicznemu lub adopcyjnemu — nie dotyczy rodziny zastępczej.")
        else:
            paternity_weeks = params.paternity_weeks

    if paternity_weeks > 0:
        pat_m, pat_t = _calc_amount(base_p2, params.paternity_rate, paternity_weeks)
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop ojcowski",
                parent="Ojciec adopcyjny" if req.scenario == BenefitScenario.ADOPTION else p2_label,
                weeks=float(paternity_weeks),
                rate_percent=round(params.paternity_rate * 100, 1),
                monthly_gross_pln=pat_m,
                total_gross_pln=pat_t,
            )
        )

    if top_up_applied:
        warnings.append(
            f"Zastosowano ustawowe podwyższenie zasiłku macierzyńskiego do wysokości świadczenia rodzicielskiego ({min_monthly_floor:.2f} zł/mies. — art. 31 ust. 3a–3c)."
        )

    # Dokumenty
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

    if req.scenario == BenefitScenario.BIRTH:
        docs.append("Odpis skrócony aktu urodzenia dziecka")
    elif req.scenario == BenefitScenario.ADOPTION:
        docs.append("Zaświadczenie sądu opiekuńczego o wszczęciu postępowania o przysposobienie lub prawomocne orzeczenie")
    else:
        docs.append("Orzeczenie sądu opiekuńczego o umieszczeniu dziecka w rodzinie zastępczej niezawodowej lub umowa ze starostą")

    total_weeks = round(sum(item.weeks for item in breakdown), 2)
    total_gross = round(sum(item.total_gross_pln for item in breakdown) + equalization_to_100_pln, 2)

    return IntegratedCalculatorResponse(
        eligible=True,
        benefit_base_parent1=base_p1,
        benefit_base_parent2=base_p2,
        benefit_base_explanation=base_p1_expl,
        benefit_base_parent2_explanation=base_p2_expl,
        minimum_benefit_top_up_applied=top_up_applied,
        equalization_to_100_pln=equalization_to_100_pln,
        total_weeks=total_weeks,
        maternity_weeks=maternity_weeks,
        supplementary_maternity_weeks=supplementary_weeks,
        parental_weeks_total=round(float(mother_parental + father_parental) + total_extended_weeks, 2),
        parental_weeks_extended_by_work=total_extended_weeks,
        paternity_weeks=paternity_weeks,
        payer=payer,
        breakdown=breakdown,
        total_estimated_gross_pln=total_gross,
        warnings=warnings,
        required_documents=docs,
    )
