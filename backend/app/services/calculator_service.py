from decimal import Decimal, ROUND_HALF_UP
import math
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
    WaitingPeriodExemptionReason,
)
from app.models.parameters import LegalParameters


def _round_pln(value: float) -> float:
    """Zaokrąglenie kwot PLN do grosza metodą matematyczną (ROUND_HALF_UP, zgodnie z praktyką ZUS)."""
    return float(Decimal(str(round(value, 8))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_individual_benefit_base(
    req: IndividualBaseCalculationRequest, params: LegalParameters
) -> IndividualBaseCalculationResponse:
    """Kalkulator indywidualnej podstawy wymiaru zasiłku — Art. 36–52 ustawy zasiłkowej."""
    if req.insurance_title == InsuranceTitle.NONE:
        raise HTTPException(
            status_code=422,
            detail="Osoba niepodlegająca ubezpieczeniu chorobowemu nie ma ustalanej podstawy wymiaru zasiłku — wybierz tytuł ubezpieczenia (UoP, zlecenie lub JDG).",
        )
    rate = params.employee_social_security_rate
    steps: list[str] = []
    cap_applied = False
    floor_applied = False

    if req.mode == "previous_benefit":
        if req.previous_benefit_base is None or req.previous_benefit_base <= 0:
            raise HTTPException(
                status_code=422,
                detail="Podaj dodatnią podstawę wymiaru z poprzedniego zasiłku (art. 43 ustawy zasiłkowej).",
            )
        base = _round_pln(req.previous_benefit_base)
        legal_basis = "Art. 43 ustawy zasiłkowej (przerwa między zasiłkami krótsza niż miesiąc kalendarzowy)"
        steps.append(
            f"Zachowano podstawę wymiaru z poprzedniego zasiłku (np. chorobowego w ciąży): {base:.2f} zł (brak przerwy lub przerwa < 1 miesiąc kalendarzowy)."
        )
        if req.insurance_title == InsuranceTitle.UOP:
            min_base = _round_pln(params.minimum_wage_gross * req.fte_fraction * (1.0 - rate))
            if base < min_base:
                base = min_base
                floor_applied = True
                steps.append(
                    f"Podniesiono zachowaną podstawę do gwarantowanego minimum dla {req.fte_fraction:.2f} etatu w {params.year} r.: {min_base:.2f} zł (art. 45 ustawy zasiłkowej)."
                )
        elif req.insurance_title in (InsuranceTitle.ZLECENIE, InsuranceTitle.JDG):
            max_cap_net = _round_pln(params.voluntary_sickness_max_monthly_gross * (1.0 - rate))
            if base > max_cap_net:
                base = max_cap_net
                cap_applied = True
                steps.append(
                    f"Ograniczono podstawę do maksymalnego limitu dobrowolnego ubezpieczenia chorobowego (250% przeciętnego wynagrodzenia): {max_cap_net:.2f} zł."
                )
    elif req.mode == "jdg_art48a":
        max_cap_gross = params.voluntary_sickness_max_monthly_gross
        max_cap_net = _round_pln(max_cap_gross * (1.0 - rate))
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

        min_net = _round_pln(min_gross * (1.0 - rate))
        declared_net = _round_pln(declared_gross * (1.0 - rate))

        if req.jdg_insured_months == 0:
            legal_basis = "Art. 49 ust. 1 pkt 1 ustawy zasiłkowej (powstanie prawa przed upływem 1 pełnego miesiąca kalendarzowego ubezpieczenia na JDG)"
            base = min_net
            floor_applied = True
            steps.append(
                f"Brak pełnego miesiąca kalendarzowego ubezpieczenia chorobowego (0/12 mies.) — zgodnie z art. 49 ust. 1 pkt 1 podstawę stanowi najniższa miesięczna podstawa wymiaru składek po odliczeniu {rate*100:.2f}%: {min_net:.2f} zł (z {min_gross:.2f} zł brutto{' — preferencyjny ZUS' if req.jdg_preferential_zus else ''})."
            )
            if declared_net > min_net:
                steps.append(
                    f"Nadwyżka zadeklarowanej podstawy ({declared_net:.2f} zł) nie podlega doliczeniu przy 0 pełnych miesiącach ubezpieczenia (chyba że spełniono warunki ciągłości z innego tytułu z art. 49 ust. 3)."
                )
        elif req.jdg_insured_months < 12 and declared_net > min_net:
            legal_basis = "Art. 48a ust. 1 ustawy zasiłkowej (ubezpieczenie chorobowe na JDG krótsze niż 12 miesięcy)"
            excess = _round_pln(((declared_net - min_net) / 12.0) * req.jdg_insured_months)
            base = _round_pln(min_net + excess)
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
        elif req.jdg_insured_months < 12:
            legal_basis = "Art. 48a ust. 1 w zw. z art. 48 ust. 2 ustawy zasiłkowej (ubezpieczenie na JDG < 12 mies. bez nadwyżki ponad najniższą podstawę)"
            if declared_gross <= 0:
                base = min_net
                floor_applied = True
                steps.append(
                    f"Nie wskazano dodatniej deklarowanej podstawy — przyjęto najniższą podstawę składek JDG po odliczeniu {rate*100:.2f}%: {min_net:.2f} zł."
                )
            else:
                base = declared_net
                steps.append(
                    f"Przeciętna miesięczna podstawa składek z {req.jdg_insured_months} pełnych mies. po odliczeniu {rate*100:.2f}%: {base:.2f} zł (brak nadwyżki ponad najniższą podstawę {min_net:.2f} zł)."
                )
                if declared_gross < min_gross:
                    steps.append(
                        f"Uwaga: wskazana kwota ({declared_gross:.2f} zł) jest niższa od przyjętej najniższej podstawy składek JDG ({min_gross:.2f} zł). Sprawdź czy korzystasz z preferencyjnego ZUS lub Małego ZUS+."
                    )
        else:
            legal_basis = "Art. 48 ust. 1 ustawy zasiłkowej (przeciętny miesięczny przychód z 12 miesięcy na JDG)"
            if declared_gross <= 0:
                base = min_net
                floor_applied = True
                steps.append(
                    f"Nie wskazano dodatniej deklarowanej podstawy — przyjęto najniższą podstawę składek JDG po odliczeniu {rate*100:.2f}%: {min_net:.2f} zł."
                )
            else:
                base = declared_net
                steps.append(
                    f"Przeciętna miesięczna podstawa składek z 12 pełnych mies. po odliczeniu {rate*100:.2f}%: {base:.2f} zł."
                )
                if declared_gross < min_gross:
                    steps.append(
                        f"Uwaga: wskazana kwota ({declared_gross:.2f} zł) jest niższa od standardowej najniższej podstawy składek JDG ({min_gross:.2f} zł)."
                    )
    else:
        is_employee = req.insurance_title == InsuranceTitle.UOP
        legal_basis = (
            "Art. 36–42 oraz art. 45 ustawy zasiłkowej (średnia z miesięcy ubezpieczenia + składniki okresowe)"
            if is_employee
            else "Art. 48–52 ustawy zasiłkowej (przeciętny miesięczny przychód ubezpieczonego niebędącego pracownikiem)"
        )
        # Odrzucamy zera i wartości ujemne (np. błędy wpisu lub miesiące zerowe) — art. 36: ostatnie 12 miesięcy
        raw_salaries = [s for s in req.monthly_gross_salaries if s > 0][-12:]
        if not raw_salaries:
            raise HTTPException(
                status_code=422,
                detail="Podaj co najmniej jedno dodatnie miesięczne wynagrodzenie brutto do wyliczenia podstawy wymiaru.",
            )

        # Realne wyłączenie miesięcy z przepracowaniem < 1/2 czasu pracy (art. 38 ust. 2 pkt 1 / art. 50 ust. 1 pkt 1)
        if req.uncompleted_months_excluded > 0:
            excl_ref = "art. 38 ust. 2 pkt 1" if is_employee else "art. 50 ust. 1 pkt 1"
            all_excl_ref = "art. 38 ust. 3" if is_employee else "art. 50 ust. 2"
            if len(raw_salaries) > req.uncompleted_months_excluded:
                sorted_asc = sorted(raw_salaries)
                excluded_vals = sorted_asc[: req.uncompleted_months_excluded]
                remaining = list(raw_salaries)
                for ev in excluded_vals:
                    remaining.remove(ev)
                raw_salaries = remaining
                steps.append(
                    f"Wyłączono {req.uncompleted_months_excluded} najniższych niepełnych mies. (<1/2 czasu pracy/działalności, {excl_ref}): {', '.join(f'{v:.2f} zł' for v in excluded_vals)}."
                )
            else:
                steps.append(
                    f"Liczba miesięcy do wyłączenia ({req.uncompleted_months_excluded}) ≥ liczba wpisanych miesięcy ({len(raw_salaries)}) — zgodnie z {all_excl_ref} przyjęto wszystkie dostępne miesiące."
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
            f"Średnie miesięczne wynagrodzenie/przychód z {months_count} pełnych miesięcy: {avg_gross:.2f} zł brutto -> {avg_net:.2f} zł po odliczeniu {rate*100:.2f}%."
        )

        quarterly_addition = 0.0
        annual_addition = 0.0
        if req.insurance_title == InsuranceTitle.JDG:
            if req.quarterly_bonuses_total > 0 or req.annual_bonus_total > 0:
                steps.append(
                    "Pominięto premie kwartalne/roczne: na JDG podstawę wymiaru stanowi wyłącznie zadeklarowana podstawa składek na ubezpieczenie chorobowe (art. 48 ustawy zasiłkowej)."
                )
        else:
            if req.quarterly_bonuses_total > 0:
                quarterly_addition = (req.quarterly_bonuses_total * (1.0 - rate)) / 12.0
                steps.append(
                    f"Doliczono 1/12 premii kwartalnych z 4 kwartałów ({req.quarterly_bonuses_total:.2f} zł brutto): +{quarterly_addition:.2f} zł (art. 42 ust. 2)."
                )
            if req.annual_bonus_total > 0:
                annual_addition = (req.annual_bonus_total * (1.0 - rate)) / 12.0
                steps.append(
                    f"Doliczono 1/12 nagrody rocznej / 13. pensji ({req.annual_bonus_total:.2f} zł brutto): +{annual_addition:.2f} zł (art. 42 ust. 3)."
                )
            if months_count < 12 and (req.quarterly_bonuses_total > 0 or req.annual_bonus_total > 0):
                steps.append(
                    "Uwaga (art. 42 ust. 2–3): Przy zatrudnieniu krótszym niż 12 miesięcy składniki kwartalne/roczne dolicza się proporcjonalnie do pełnych miesięcy kalendarzowych zatrudnienia w danym okresie."
                )

        base = _round_pln(avg_net + quarterly_addition + annual_addition)

        if req.insurance_title == InsuranceTitle.UOP:
            min_base = _round_pln(params.minimum_wage_gross * req.fte_fraction * (1.0 - rate))
            if base < min_base:
                base = min_base
                floor_applied = True
                steps.append(
                    f"Podniesiono podstawę do gwarantowanego minimum dla {req.fte_fraction:.2f} etatu: {min_base:.2f} zł (art. 45 ustawy zasiłkowej)."
                )
        elif req.insurance_title in (InsuranceTitle.ZLECENIE, InsuranceTitle.JDG):
            max_cap_net = _round_pln(params.voluntary_sickness_max_monthly_gross * (1.0 - rate))
            if base > max_cap_net:
                base = max_cap_net
                cap_applied = True
                steps.append(
                    f"Ograniczono podstawę do maksymalnego limitu dobrowolnego ubezpieczenia chorobowego: {max_cap_net:.2f} zł."
                )

    return IndividualBaseCalculationResponse(
        computed_base_monthly=base,
        daily_rate_100_percent=_round_pln(base / 30.0),
        daily_rate_81_5_percent=_round_pln((base * params.combined_21_days_rate) / 30.0),
        daily_rate_70_percent=_round_pln((base * params.parental_rate_standard) / 30.0),
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
        base = _round_pln(custom_base)
        notes_custom: list[str] = []
        if insurance_title == InsuranceTitle.UOP:
            min_base = _round_pln(params.minimum_wage_gross * fte_fraction * (1.0 - rate))
            if base < min_base:
                base = min_base
                notes_custom.append(
                    f"podwyższono do gwarantowanego minimum dla {fte_fraction:.2f} etatu w {params.year} r.: {min_base:.2f} zł (art. 45)"
                )
        elif insurance_title in (InsuranceTitle.JDG, InsuranceTitle.ZLECENIE):
            max_base = _round_pln(params.voluntary_sickness_max_monthly_gross * (1.0 - rate))
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
                f"podwyższono do minimalnej podstawy wymiaru zasiłku dla {fte_fraction:.2f} etatu w {params.year} r. ({_round_pln(min_base):.2f} zł)"
            )

    base_rounded = _round_pln(base)
    extra = f" ({'; '.join(notes)})" if notes else ""
    explanation = (
        f"Przeciętny miesięczny przychód {gross_salary:.2f} zł brutto pomniejszony o {rate*100:.2f}% składek społecznych = {base_rounded:.2f} zł{extra}."
    )
    return base_rounded, explanation


def _determine_payer(insurance_title: InsuranceTitle, employer_insured_count: int, params: LegalParameters) -> str:
    if insurance_title == InsuranceTitle.UOP and employer_insured_count > params.payer_employee_threshold:
        return f"Płatnik składek (pracodawca zgłaszający > {params.payer_employee_threshold} ubezpieczonych)"
    if insurance_title == InsuranceTitle.ZLECENIE and employer_insured_count > params.payer_employee_threshold:
        return f"Płatnik składek (zleceniodawca zgłaszający > {params.payer_employee_threshold} ubezpieczonych)"
    return "Zakład Ubezpieczeń Społecznych (ZUS)"


def _resolve_waiting_period_exemption(
    req: PregnancyBenefitRequest, waiting_days: int, warnings: list[str]
) -> tuple[bool, bool]:
    """Rozstrzyga przesłanki zwolnienia z okresu wyczekiwania (art. 4 ust. 3 ustawy zasiłkowej)."""
    reason = req.waiting_period_exemption_reason
    if reason == WaitingPeriodExemptionReason.NONE and req.waiting_period_exempt:
        reason = WaitingPeriodExemptionReason.MANDATORY_10_YEARS

    effective_exempt = False
    if reason == WaitingPeriodExemptionReason.MANDATORY_10_YEARS:
        if req.insurance_title == InsuranceTitle.UOP:
            effective_exempt = True
            if req.insurance_days < waiting_days:
                warnings.append(
                    "Zastosowano ustawowe zwolnienie z okresu wyczekiwania (art. 4 ust. 3 pkt 3 ustawy zasiłkowej — co najmniej 10-letni wcześniejszy okres obowiązkowego ubezpieczenia chorobowego)."
                )
        else:
            warnings.append(
                "Uwaga (art. 4 ust. 3 pkt 3 ustawy zasiłkowej): Zwolnienie z okresu wyczekiwania z tytułu 10-letniego stażu obowiązkowego ubezpieczenia chorobowego przysługuje wyłącznie ubezpieczonym obowiązkowo (umowa o pracę). Dla ubezpieczenia dobrowolnego (JDG/zlecenie) obowiązuje 90 dni wyczekiwania — wyjątki dotyczą m.in. absolwentów w ciągu 90 dni (pkt 1) i wypadku w drodze do/z pracy (pkt 2)."
            )
    elif reason == WaitingPeriodExemptionReason.GRADUATE_90_DAYS:
        effective_exempt = True
        if req.insurance_days < waiting_days:
            warnings.append(
                "Zastosowano ustawowe zwolnienie z okresu wyczekiwania (art. 4 ust. 3 pkt 1 ustawy zasiłkowej — absolwent szkoły, uczelni lub szkoły doktorskiej objęty/przystępujący do ubezpieczenia chorobowego w ciągu 90 dni od ukończenia nauki)."
            )
    elif reason == WaitingPeriodExemptionReason.COMMUTE_ACCIDENT:
        effective_exempt = True
        if req.insurance_days < waiting_days:
            warnings.append(
                "Zastosowano ustawowe zwolnienie z okresu wyczekiwania (art. 4 ust. 3 pkt 2 ustawy zasiłkowej — niezdolność do pracy spowodowana wypadkiem w drodze do pracy lub z pracy)."
            )

    waiting_met = effective_exempt or (req.insurance_days >= waiting_days)
    return effective_exempt, waiting_met


def calculate_pregnancy_benefit(
    req: PregnancyBenefitRequest, params: LegalParameters
) -> PregnancyBenefitResponse:
    warnings: list[str] = []
    debt_threshold = round(params.minimum_wage_gross * params.debt_threshold_min_wage_fraction, 2)
    has_blocking_debt = (
        req.insurance_title == InsuranceTitle.JDG and req.contribution_debt_pln > debt_threshold
    )

    # 1. Zasiłek chorobowy po ustaniu tytułu ubezpieczenia w ciąży (art. 7, art. 8 ust. 2, art. 13, art. 46 ustawy zasiłkowej)
    if req.employment_terminated_special and req.termination_reason == TerminationReason.POST_EMPLOYMENT_ART7:
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
                benefit_base_explanation="Brak podstawy wymiaru — brak wcześniejszego tytułu ubezpieczenia chorobowego.",
                daily_benefit_gross=0.0,
                monthly_benefit_gross=0.0,
                rehabilitation_monthly_gross=0.0,
                rehabilitation_daily_gross=0.0,
                rehabilitation_max_days=0,
                max_benefit_days=0,
                benefit_duration_label="Brak uprawnień",
                employer_pay_days=0,
                payer="Brak uprawnień",
                warnings=[
                    "Zasiłek chorobowy po ustaniu tytułu ubezpieczenia (art. 7 ustawy zasiłkowej) przysługuje wyłącznie osobie, która wcześniej podlegała ubezpieczeniu chorobowemu."
                ],
                summary="Brak prawa do zasiłku chorobowego po ustaniu zatrudnienia z powodu braku tytułu ubezpieczenia chorobowego.",
            )

        waiting_days = (
            params.waiting_period_mandatory_days
            if req.insurance_title == InsuranceTitle.UOP
            else params.waiting_period_voluntary_days
        )
        effective_exempt, waiting_met = _resolve_waiting_period_exemption(req, waiting_days, warnings)
        if not waiting_met:
            warnings.append(
                f"Brak prawa po ustaniu ubezpieczenia (art. 13 ust. 1 pkt 3 w zw. z art. 4 ust. 1 ustawy zasiłkowej): w czasie trwania ubezpieczenia nie upłynął okres wyczekiwania ({req.insurance_days}/{waiting_days} dni), więc prawo do zasiłku nie zostało nabyte przed ustaniem tytułu."
            )
            return PregnancyBenefitResponse(
                eligible_sickness_benefit=False,
                eligible_maternity_equivalent=False,
                waiting_period_required_days=waiting_days,
                waiting_period_met=False,
                benefit_rate_percent=0.0,
                benefit_base_monthly=0.0,
                benefit_base_explanation="Nie nabyto prawa do zasiłku przed ustaniem tytułu ubezpieczenia (art. 13 ust. 1 pkt 3).",
                daily_benefit_gross=0.0,
                monthly_benefit_gross=0.0,
                rehabilitation_monthly_gross=0.0,
                rehabilitation_daily_gross=0.0,
                rehabilitation_max_days=0,
                max_benefit_days=0,
                benefit_duration_label="Brak uprawnień (niespełniony okres wyczekiwania)",
                employer_pay_days=0,
                payer="Brak uprawnień",
                warnings=warnings,
                summary=f"Brak prawa do zasiłku chorobowego po ustaniu ubezpieczenia — nie spełniono okresu wyczekiwania ({req.insurance_days}/{waiting_days} dni, art. 13 ust. 1 pkt 3).",
            )

        base, base_expl = _compute_benefit_base_with_explanation(
            req.gross_monthly_salary,
            req.custom_benefit_base,
            None,
            req.insurance_title,
            params,
            fte_fraction=req.fte_fraction,
        )
        # Art. 46: ograniczenie bezpośrednio podstawy wymiaru zasiłku (już po -13,71%) do 100% przeciętnego wynagrodzenia
        art46_cap = _round_pln(params.post_employment_sickness_cap_monthly_gross)
        if base > art46_cap:
            base = art46_cap
            base_expl += f" Ograniczono podstawę po ustaniu ubezpieczenia do 100% przeciętnego wynagrodzenia: {art46_cap:.2f} zł (art. 46 ustawy zasiłkowej)."

        if has_blocking_debt:
            warnings.append(
                f"UWAGA (art. 2a ustawy zasiłkowej): Zadłużenie składkowe ZUS ({req.contribution_debt_pln:.2f} zł > {debt_threshold:.2f} zł) wstrzymuje wypłatę świadczenia do czasu spłaty całości zadłużenia (przedawnienie po {params.claim_limitation_months} miesiącach)."
            )

        rate = params.sickness_benefit_pregnancy_rate if req.has_code_b else params.sickness_benefit_standard_rate
        if not req.has_code_b:
            warnings.append(
                f"Uwaga (art. 8 ust. 2 i art. 11 ust. 2 pkt 1): Bez kodu „B” na e-ZLA lub odrębnego zaświadczenia o ciąży ZUS wypłaci wstępnie {int(params.sickness_benefit_standard_rate*100)}% i zastosuje standardowy limit 91 dni po ustaniu ubezpieczenia. Po udokumentowaniu ciąży przysługuje wyrównanie do 100% oraz okres zasiłkowy do {params.sickness_benefit_pregnancy_max_days} dni."
            )

        warnings.extend(
            [
                f"Zasiłek chorobowy po ustaniu ubezpieczenia (art. 7 ustawy zasiłkowej) przysługuje, jeśli niezdolność do pracy powstała do 14 dni od ustania tytułu ubezpieczenia (lub do 3 mies. dla chorób z art. 7 pkt 2) i trwa nieprzerwanie co najmniej 30 dni. Podstawa wymiaru nie może przekroczyć 100% przeciętnego wynagrodzenia ({art46_cap:.2f} zł — art. 46).",
                "Uwaga (art. 13 ustawy zasiłkowej): Zasiłek po ustaniu zatrudnienia nie przysługuje m.in. w razie podjęcia lub kontynuowania innej działalności zarobkowej, prawa do emerytury/renty, zasiłku dla bezrobotnych albo obowiązkowego ubezpieczenia w KRUS.",
            ]
        )
        daily = _round_pln((base * rate) / 30.0)
        monthly = _round_pln(base * rate)
        rehab_rate = params.rehabilitation_benefit_pregnancy_rate
        max_days = params.sickness_benefit_pregnancy_max_days if req.has_code_b else 91
        duration_label = (
            f"Maks. {params.sickness_benefit_pregnancy_max_days} dni (w ciąży nie obowiązuje skrócony limit 91 dni — art. 8 ust. 2)"
            if req.has_code_b
            else "Wstępnie maks. 91 dni po ustaniu (art. 8 ust. 2) — po dostarczeniu zaświadczenia o ciąży do 270 dni"
        )
        summary = (
            f"Prawo do zasiłku chorobowego po ustaniu ubezpieczenia w ciąży ({int(rate*100)}%, pułap z art. 46: {art46_cap:.2f} zł), lecz wypłata jest wstrzymana z powodu zadłużenia ZUS (art. 2a)."
            if has_blocking_debt
            else f"Przysługuje zasiłek chorobowy po ustaniu ubezpieczenia w ciąży ({int(rate*100)}%, maks. {max_days} dni, pułap podstawy z art. 46: {art46_cap:.2f} zł) wypłacany przez ZUS."
        )
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=True,
            eligible_maternity_equivalent=False,
            payout_suspended_due_to_debt=has_blocking_debt,
            waiting_period_required_days=0 if effective_exempt else waiting_days,
            waiting_period_met=True,
            benefit_rate_percent=round(rate * 100, 1),
            benefit_base_monthly=base,
            benefit_base_explanation=base_expl,
            daily_benefit_gross=daily,
            monthly_benefit_gross=monthly,
            rehabilitation_monthly_gross=round(base * rehab_rate, 2),
            rehabilitation_daily_gross=round((base * rehab_rate) / 30.0, 2),
            rehabilitation_max_days=params.rehabilitation_benefit_max_days,
            max_benefit_days=max_days,
            benefit_duration_label=duration_label,
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=warnings,
            summary=summary,
        )

    # 2. Zasiłek w wysokości zasiłku macierzyńskiego do dnia porodu — ścisły art. 30 ust. 3 (tylko pracownica UoP: upadłość/likwidacja/śmierć pracodawcy)
    if req.employment_terminated_special and req.termination_reason in (
        TerminationReason.BANKRUPTCY_LIQUIDATION,
        TerminationReason.EMPLOYER_DEATH,
    ):
        if req.insurance_title != InsuranceTitle.UOP:
            return PregnancyBenefitResponse(
                eligible_sickness_benefit=False,
                eligible_maternity_equivalent=False,
                eligible_post_birth_maternity_art30=False,
                waiting_period_required_days=0,
                waiting_period_met=False,
                benefit_rate_percent=0.0,
                benefit_base_monthly=0.0,
                benefit_base_explanation="Art. 30 ust. 3 ustawy zasiłkowej ma zastosowanie wyłącznie do pracownicy zatrudnionej na podstawie umowy o pracę.",
                daily_benefit_gross=0.0,
                monthly_benefit_gross=0.0,
                rehabilitation_monthly_gross=0.0,
                rehabilitation_daily_gross=0.0,
                rehabilitation_max_days=0,
                max_benefit_days=0,
                benefit_duration_label="Brak uprawnień (dotyczy wyłącznie UoP)",
                employer_pay_days=0,
                payer="Brak uprawnień",
                warnings=[
                    "Zasiłek w wysokości zasiłku macierzyńskiego (art. 30 ust. 3 ustawy zasiłkowej) przysługuje wyłącznie ubezpieczonej będącej pracownicą (umowa o pracę), której umowa wygasła wskutek śmierci pracodawcy lub została rozwiązana z powodu jego upadłości albo likwidacji."
                ],
                summary="Brak prawa do zasiłku w wysokości zasiłku macierzyńskiego — art. 30 ust. 3 dotyczy wyłącznie pracownic (umowa o pracę).",
            )

        base, base_expl = _compute_benefit_base_with_explanation(
            req.gross_monthly_salary,
            req.custom_benefit_base,
            None,
            InsuranceTitle.UOP,
            params,
            fte_fraction=req.fte_fraction,
        )
        monthly_mat = _round_pln(base * params.maternity_rate_standard)
        daily = _round_pln(monthly_mat / 30.0)
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=False,
            eligible_maternity_equivalent=True,
            eligible_post_birth_maternity_art30=True,
            waiting_period_required_days=0,
            waiting_period_met=True,
            benefit_rate_percent=round(params.maternity_rate_standard * 100, 1),
            benefit_base_monthly=base,
            benefit_base_explanation=base_expl,
            daily_benefit_gross=daily,
            monthly_benefit_gross=monthly_mat,
            rehabilitation_monthly_gross=0.0,
            rehabilitation_daily_gross=0.0,
            rehabilitation_max_days=0,
            max_benefit_days=0,
            benefit_duration_label="Do dnia porodu (bez limitu 270 dni — art. 30 ust. 3; od dnia porodu zasiłek macierzyński z art. 30 ust. 1 pkt 1)",
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=[
                "Zasiłek w wysokości zasiłku macierzyńskiego (art. 30 ust. 3 ustawy zasiłkowej) przysługuje pracownicy do dnia porodu w razie upadłości, likwidacji lub śmierci pracodawcy, o ile nie zapewniono jej innego zatrudnienia. Nie obowiązuje tu limit 270 dni okresu zasiłkowego ani nie przechodzi się na świadczenie rehabilitacyjne.",
                "Po urodzeniu dziecka przysługuje pełny zasiłek macierzyński po ustaniu ubezpieczenia wypłacany przez ZUS (art. 30 ust. 1 pkt 1 ustawy zasiłkowej). Wymagane dokumenty (§ 17 rozporządzenia): zaświadczenie lekarskie o stanie ciąży w okresie zatrudnienia, świadectwo pracy potwierdzające przyczynę ustania stosunku pracy oraz oświadczenie o niezapewnieniu innego zatrudnienia.",
            ],
            summary="Przysługuje zasiłek w wysokości zasiłku macierzyńskiego (100% podstawy wymiaru) wypłacany przez ZUS do dnia porodu, a od dnia porodu — zasiłek macierzyński (art. 30 ust. 1 pkt 1 i ust. 3).",
        )

    # 3. Rozwiązanie umowy z naruszeniem przepisów prawa (prawomocny wyrok sądu) — ścisła wykładnia art. 30 ust. 1 pkt 2 vs ust. 3
    if req.employment_terminated_special and req.termination_reason == TerminationReason.UNLAWFUL_TERMINATION_COURT_RULING:
        if req.insurance_title != InsuranceTitle.UOP:
            return PregnancyBenefitResponse(
                eligible_sickness_benefit=False,
                eligible_maternity_equivalent=False,
                eligible_post_birth_maternity_art30=False,
                waiting_period_required_days=0,
                waiting_period_met=False,
                benefit_rate_percent=0.0,
                benefit_base_monthly=0.0,
                benefit_base_explanation="Art. 30 ust. 1 pkt 2 ustawy zasiłkowej dotyczy ustania zatrudnienia pracowniczego (umowa o pracę).",
                daily_benefit_gross=0.0,
                monthly_benefit_gross=0.0,
                rehabilitation_monthly_gross=0.0,
                rehabilitation_daily_gross=0.0,
                rehabilitation_max_days=0,
                max_benefit_days=0,
                benefit_duration_label="Brak uprawnień (dotyczy wyłącznie UoP)",
                employer_pay_days=0,
                payer="Brak uprawnień",
                warnings=[
                    "Ochrona z art. 30 ust. 1 pkt 2 ustawy zasiłkowej (rozwiązanie stosunku pracy z naruszeniem prawa stwierdzone prawomocnym wyrokiem sądu) dotyczy wyłącznie pracownic (umowa o pracę)."
                ],
                summary="Brak uprawnień z art. 30 ust. 1 pkt 2 — przepis dotyczy wyłącznie pracownic zatrudnionych na umowę o pracę.",
            )

        base, base_expl = _compute_benefit_base_with_explanation(
            req.gross_monthly_salary,
            req.custom_benefit_base,
            None,
            InsuranceTitle.UOP,
            params,
            fte_fraction=req.fte_fraction,
        )
        monthly_mat = _round_pln(base * params.maternity_rate_standard)
        daily = _round_pln(monthly_mat / 30.0)
        return PregnancyBenefitResponse(
            eligible_sickness_benefit=False,
            eligible_maternity_equivalent=False,
            eligible_post_birth_maternity_art30=True,
            waiting_period_required_days=0,
            waiting_period_met=True,
            benefit_rate_percent=round(params.maternity_rate_standard * 100, 1),
            benefit_base_monthly=base,
            benefit_base_explanation=base_expl,
            daily_benefit_gross=daily,
            monthly_benefit_gross=monthly_mat,
            rehabilitation_monthly_gross=0.0,
            rehabilitation_daily_gross=0.0,
            rehabilitation_max_days=0,
            max_benefit_days=0,
            benefit_duration_label="Brak zasiłku w wys. macierzyńskiego przed porodem (art. 30 ust. 3); od dnia porodu pełny zasiłek macierzyński z ZUS (art. 30 ust. 1 pkt 2)",
            employer_pay_days=0,
            payer="Zakład Ubezpieczeń Społecznych (ZUS)",
            warnings=[
                "Ścisła wykładnia ustawy (art. 30 ust. 3 vs art. 30 ust. 1 pkt 2 ustawy zasiłkowej oraz § 15 ust. 2 i § 17 rozporządzenia): Zasiłek w wysokości zasiłku macierzyńskiego wypłacany do dnia porodu (art. 30 ust. 3) obejmuje wyłącznie upadłość, likwidację lub śmierć pracodawcy. Przy rozwiązaniu umowy o pracę z naruszeniem prawa (wyrok sądu) zasiłek w wysokości macierzyńskiego przed porodem nie przysługuje z ZUS — pracownica dochodzi roszczeń wobec pracodawcy przed sądem pracy (np. wynagrodzenia za czas pozostawania bez pracy).",
                "Przysługuje natomiast pełny zasiłek macierzyński PO porodzie z ZUS (art. 30 ust. 1 pkt 2 ustawy zasiłkowej) — od dnia urodzenia dziecka za okres urlopu macierzyńskiego i rodzicielskiego. Wymagane dokumenty (§ 15 ust. 2 rozporządzenia): zaświadczenie lekarskie o stanie ciąży w okresie zatrudnienia oraz prawomocne orzeczenie sądu o rozwiązaniu stosunku pracy z naruszeniem przepisów prawa.",
                "Uwaga: jeśli w okresie do 14 dni od ustania stosunku pracy powstała niezdolność do pracy trwająca nieprzerwanie min. 30 dni, sprawdź opcję zasiłku chorobowego po ustaniu ubezpieczenia (art. 7 i 46).",
            ],
            summary="Zgodnie z art. 30 ust. 3 nie przysługuje zasiłek w wysokości macierzyńskiego przed porodem, natomiast na mocy art. 30 ust. 1 pkt 2 przysługuje pełny zasiłek macierzyński po porodzie wypłacany przez ZUS (prognozowana podstawa i stawka 100% poniżej).",
        )

    # 4. Brak podlegania ubezpieczeniu chorobowemu
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
            benefit_duration_label="Brak okresu zasiłkowego",
            employer_pay_days=0,
            payer="Brak uprawnień",
            warnings=[
                "Brak podlegania ubezpieczeniu chorobowemu. Aby uzyskać prawo do zasiłku chorobowego na umowie zleceniu lub JDG, wymagane jest przystąpienie do dobrowolnego ubezpieczenia chorobowego."
            ],
            summary="Brak prawa do zasiłku chorobowego z powodu niepodlegania ubezpieczeniu chorobowemu.",
        )

    # 5. Standardowy zasiłek chorobowy w ciąży (aktywne ubezpieczenie)
    waiting_days = (
        params.waiting_period_mandatory_days
        if req.insurance_title == InsuranceTitle.UOP
        else params.waiting_period_voluntary_days
    )
    effective_exempt, waiting_met = _resolve_waiting_period_exemption(req, waiting_days, warnings)
    if not waiting_met:
        warnings.append(
            f"Nie upłynął okres wyczekiwania ({req.insurance_days}/{waiting_days} dni). Prawo do zasiłku powstanie po osiągnięciu {waiting_days} dni nieprzerwanego ubezpieczenia (wlicza się poprzednie okresy, jeśli przerwa nie przekroczyła 30 dni — art. 4 ust. 2)."
        )

    if has_blocking_debt:
        warnings.append(
            f"UWAGA (art. 2a ustawy zasiłkowej): Wykazano zadłużenie z tytułu składek ZUS ({req.contribution_debt_pln:.2f} zł), które przekracza {params.debt_threshold_min_wage_fraction*100:.1f}% minimalnego wynagrodzenia ({debt_threshold:.2f} zł). Świadczenie nie przysługuje do czasu spłaty całości zadłużenia (po {params.claim_limitation_months} miesiącach od dnia powstania prawa roszczenie ulega przedawnieniu)."
        )

    if (
        req.insurance_title == InsuranceTitle.JDG
        and req.custom_benefit_base is None
        and req.insurance_days < 365
        and req.gross_monthly_salary > params.jdg_standard_min_base_gross
    ):
        warnings.append(
            f"Uwaga dla JDG (art. 48a ustawy zasiłkowej): Przy stażu dobrowolnego ubezpieczenia chorobowego krótszym niż 12 pełnych miesięcy kalendarzowych ({req.insurance_days} dni) i podstawie wyższej niż minimalna ({params.jdg_standard_min_base_gross:.2f} zł brutto), ZUS obliczy podstawę proporcjonalnie (najniższa podstawa + 1/12 nadwyżki za każdy pełny miesiąc). Użyj Kreatora podstawy w zakładce Kalkulator i wpisz wynik jako indywidualną podstawę."
        )
    elif (
        req.insurance_title == InsuranceTitle.JDG
        and req.custom_benefit_base is None
        and 0 < req.gross_monthly_salary < params.jdg_preferential_min_base_gross
    ):
        warnings.append(
            f"Uwaga: Podana kwota brutto ({req.gross_monthly_salary:.2f} zł) jest niższa od minimalnej preferencyjnej podstawy składek JDG w {params.year} r. ({params.jdg_preferential_min_base_gross:.2f} zł — 30% płacy minimalnej)."
        )

    if req.insurance_title == InsuranceTitle.UOP and req.age_over_50:
        warnings.append(
            "Informacja (art. 92 § 5 Kodeksu pracy): Skrócony 14-dniowy okres wynagrodzenia chorobowego finansowanego przez pracodawcę dotyczy niezdolności do pracy przypadającej po roku kalendarzowym, w którym pracownik ukończył 50. rok życia."
        )

    # Art. 8 ust. 1 i art. 11 ust. 2 pkt 1: ciąża daje 100% i 270 dni z mocy ustawy; kod "B" jest dowodem na e-ZLA
    rate = params.sickness_benefit_pregnancy_rate if req.has_code_b else params.sickness_benefit_standard_rate
    max_days = params.sickness_benefit_pregnancy_max_days if req.has_code_b else 182
    if not req.has_code_b:
        warnings.append(
            f"Zgodnie z art. 8 ust. 1 i art. 11 ust. 2 pkt 1 ustawy zasiłkowej zasiłek chorobowy w okresie ciąży wynosi 100% podstawy wymiaru do {params.sickness_benefit_pregnancy_max_days} dni. Kod literowy „B” na e-ZLA stanowi dowód stanu ciąży — bez niego płatnik/ZUS zastosuje wstępnie {int(params.sickness_benefit_standard_rate*100)}% i standardowy limit 182 dni, ale po dostarczeniu odrębnego zaświadczenia lekarskiego o ciąży przysługuje pełne wyrównanie do 100% oraz okres zasiłkowy do {params.sickness_benefit_pregnancy_max_days} dni."
        )

    base, base_expl = _compute_benefit_base_with_explanation(
        req.gross_monthly_salary,
        req.custom_benefit_base,
        None,
        req.insurance_title,
        params,
        fte_fraction=req.fte_fraction,
    )
    daily = _round_pln((base * rate) / 30.0)
    monthly = _round_pln(base * rate)
    rehab_rate = params.rehabilitation_benefit_pregnancy_rate
    rehab_monthly = _round_pln(base * rehab_rate)
    rehab_daily = _round_pln((base * rehab_rate) / 30.0)

    employer_days = 0
    if req.insurance_title == InsuranceTitle.UOP:
        employer_days = (
            params.sickness_pay_employer_days_over_50
            if req.age_over_50
            else params.sickness_pay_employer_days_under_50
        )

    payer = _determine_payer(req.insurance_title, req.employer_insured_count, params)
    if not waiting_met:
        summary = f"Ubezpieczenie aktywne, ale okres wyczekiwania ({req.insurance_days}/{waiting_days} dni) nie został jeszcze spełniony. Poniższe kwoty stanowią prognozę po spełnieniu okresu wyczekiwania."
    elif has_blocking_debt:
        summary = f"Wypłata zasiłku chorobowego w ciąży ({int(rate * 100)}%, maks. {max_days} dni) jest wstrzymana z powodu zadłużenia składkowego ZUS ({req.contribution_debt_pln:.2f} zł > {debt_threshold:.2f} zł — art. 2a). Poniższe kwoty przysługują po spłacie całości zadłużenia w terminie {params.claim_limitation_months} miesięcy."
    else:
        summary = f"Przysługuje zasiłek chorobowy w ciąży w wysokości {int(rate * 100)}% podstawy wymiaru (maks. {max_days} dni), a po jego wyczerpaniu świadczenie rehabilitacyjne w ciąży ({int(rehab_rate*100)}% podstawy wymiaru, do {params.rehabilitation_benefit_max_days} dni)."

    if req.has_code_b:
        duration_label = (
            f"Maks. {max_days} dni (pierwsze {employer_days} dni wynagrodzenie chorobowe pracodawcy, od {employer_days + 1}. dnia zasiłek z FUS)"
            if employer_days > 0
            else f"Maks. {max_days} dni (zasiłek z FUS od 1. dnia niezdolności do pracy)"
        )
    else:
        duration_label = (
            f"Wstępnie maks. 182 dni bez kodu B (pierwsze {employer_days} dni pracodawca, od {employer_days + 1}. dnia FUS) — po zaświadczeniu o ciąży do {params.sickness_benefit_pregnancy_max_days} dni"
            if employer_days > 0
            else f"Wstępnie maks. 182 dni bez kodu B (FUS od 1. dnia) — po zaświadczeniu o ciąży do {params.sickness_benefit_pregnancy_max_days} dni"
        )

    return PregnancyBenefitResponse(
        eligible_sickness_benefit=waiting_met,
        eligible_maternity_equivalent=False,
        payout_suspended_due_to_debt=has_blocking_debt,
        waiting_period_required_days=0 if effective_exempt else waiting_days,
        waiting_period_met=waiting_met,
        benefit_rate_percent=round(rate * 100, 1),
        benefit_base_monthly=base,
        benefit_base_explanation=base_expl,
        daily_benefit_gross=daily,
        monthly_benefit_gross=monthly,
        rehabilitation_monthly_gross=rehab_monthly if waiting_met else 0.0,
        rehabilitation_daily_gross=rehab_daily if waiting_met else 0.0,
        rehabilitation_max_days=params.rehabilitation_benefit_max_days if waiting_met else 0,
        max_benefit_days=max_days,
        benefit_duration_label=duration_label,
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
        if not req.full_term_hospitalization_condition_met:
            warnings.append(
                "Brak prawa do uzupełniającego urlopu macierzyńskiego (art. 180² § 1 pkt 3 KP): dla dziecka urodzonego po ukończeniu 37. tygodnia ciąży (masa > 1000 g) wymagany jest pobyt w szpitalu trwający co najmniej 2 kolejne dni, z których pierwszy przypada w okresie od 5. do 28. dnia po porodzie."
            )
            return 0
        warnings.append(
            "Dla dziecka urodzonego po ukończeniu 37. tygodnia ciąży uzupełniający urlop macierzyński (do 8 tyg.) przysługuje pod warunkiem, że pobyt dziecka w szpitalu trwał co najmniej 2 kolejne dni, a pierwszy z nich przypadał w okresie od 5. do 28. dnia po porodzie (art. 180² § 1 pkt 3 Kodeksu pracy)."
        )
    cap = (
        params.supplementary_maternity_max_weeks_extreme
        if is_extreme
        else params.supplementary_maternity_max_weeks_standard
    )
    if req.scenario in (BenefitScenario.ADOPTION, BenefitScenario.FOSTER):
        if req.child_age_years is not None:
            age_weeks = req.child_age_years * params.weeks_per_year
            max_after_placement = max(0, math.ceil(cap - age_weeks - 1e-9))
            if max_after_placement <= 0:
                warnings.append(
                    f"Brak prawa do uzupełniającego urlopu macierzyńskiego (art. 183 § 3¹ w zw. z art. 180² § 1 KP): przy adopcji lub rodzinie zastępczej urlop ten przysługuje wyłącznie za pobyt dziecka w szpitalu po przyjęciu na wychowanie przypadający do upływu {cap}. tygodnia po porodzie."
                )
                return 0
            warnings.append(
                "Uzupełniający urlop macierzyński przy adopcji lub rodzinie zastępczej (art. 183 § 3¹ KP) przysługuje wyłącznie, jeżeli pobyt dziecka w szpitalu miał miejsce po przyjęciu dziecka na wychowanie."
            )
            return min(req.hospitalization_weeks, cap, max_after_placement)
        warnings.append(
            "Uzupełniający urlop macierzyński przy adopcji lub rodzinie zastępczej (art. 183 § 3¹ KP) przysługuje wyłącznie, jeżeli pobyt dziecka w szpitalu miał miejsce po przyjęciu dziecka na wychowanie."
        )
    return min(req.hospitalization_weeks, cap)


def _calc_work_extension_days(work_weeks: int, fte: float, work_in_ext: bool, max_ext_days: int) -> int:
    """Oblicza wydłużenie urlopu rodzicielskiego w pełnych dniach (art. 182¹ᶠ § 2, § 4 i § 7 KP — niepełny dzień pomija się)."""
    if work_weeks <= 0 or fte <= 0 or max_ext_days <= 0:
        return 0
    raw_days = (
        (work_weeks * 7.0 * fte) / (1.0 - fte)
        if work_in_ext
        else (work_weeks * 7.0 * fte)
    )
    return min(max(0, math.floor(raw_days + 1e-9)), max_ext_days)


def _format_days_label(days: int) -> str:
    w, d = divmod(days, 7)
    if d == 0:
        return f"{w} tyg. ({days} dni)"
    return f"{w} tyg. i {d} {'dzień' if d == 1 else 'dni'} ({days} dni)"


def calculate_integrated_maternity(
    req: IntegratedCalculatorRequest, params: LegalParameters
) -> IntegratedCalculatorResponse:
    warnings: list[str] = []
    docs: list[str] = []
    top_up_applied = False
    min_monthly_floor = params.parental_benefit_minimum_monthly
    debt_threshold = round(params.minimum_wage_gross * params.debt_threshold_min_wage_fraction, 2)

    def _calc_amount_days(
        base: float,
        rate: float,
        days: int,
        fte_work: float = 0.0,
        track_top_up: bool = True,
    ) -> tuple[float, float]:
        nonlocal top_up_applied
        effective_fraction = 1.0 - fte_work
        raw_full_monthly = round(base * rate, 2)
        if raw_full_monthly < min_monthly_floor and base >= 0:
            full_monthly = min_monthly_floor
            if track_top_up:
                top_up_applied = True
        else:
            full_monthly = raw_full_monthly
        monthly = round(full_monthly * effective_fraction, 2)
        daily = round(monthly / 30.0, 2)
        total = round(daily * days, 2)
        return monthly, total

    def _append_parental_segment(
        target_list: list[LeaveBreakdownItem],
        parent_label: str,
        base_val: float,
        segment_weeks: int,
        rate_val: float,
        work_weeks: int,
        fte_val: float,
        ext_days: int,
        work_in_ext: bool,
        base_label: str,
        extra_note: str | None = None,
    ) -> None:
        if segment_weeks <= 0:
            return
        if work_weeks > 0 and fte_val > 0:
            full_weeks = segment_weeks - work_weeks
            if full_weeks > 0:
                fl_days = full_weeks * 7
                fl_m, fl_t = _calc_amount_days(base_val, rate_val, fl_days)
                target_list.append(
                    LeaveBreakdownItem(
                        label=f"{base_label} (pełny wymiar)",
                        parent=parent_label,
                        weeks=float(full_weeks),
                        days=fl_days,
                        rate_percent=round(rate_val * 100, 1),
                        monthly_gross_pln=fl_m,
                        total_gross_pln=fl_t,
                        notes=extra_note,
                    )
                )
            ext_label = _format_days_label(ext_days)
            if work_in_ext:
                comb_days = work_weeks * 7 + ext_days
                comb_weeks = round(comb_days / 7.0, 2)
                cw_m, cw_t = _calc_amount_days(base_val, rate_val, comb_days, fte_work=fte_val)
                if ext_days > 0:
                    comb_label = f"{base_label} łączony z pracą ({fte_val} etatu) + wydłużenie (+{round(ext_days/7.0, 2)} tyg.)"
                    note = (
                        f"Art. 182¹ᶠ § 4 i § 7 KP: łączny okres {_format_days_label(comb_days)} "
                        f"(w tym wydłużenie {ext_label}, niepełny dzień pominięto); zasiłek pomniejszony proporcjonalnie o {round(fte_val*100, 1)}%."
                    )
                else:
                    comb_label = f"{base_label} łączony z pracą ({fte_val} etatu)"
                    note = (
                        f"Art. 31 ust. 4a ustawy zasiłkowej i art. 182¹ᶠ § 4 KP: wydłużenie wynosi 0 dni "
                        f"(niepełny dzień pominięto lub osiągnięto limit wieku/puli); zasiłek pomniejszony proporcjonalnie o {round(fte_val*100, 1)}%."
                    )
                if extra_note:
                    note = f"{note} {extra_note}"
                target_list.append(
                    LeaveBreakdownItem(
                        label=comb_label,
                        parent=parent_label,
                        weeks=comb_weeks,
                        days=comb_days,
                        rate_percent=round(rate_val * (1.0 - fte_val) * 100, 2),
                        monthly_gross_pln=cw_m,
                        total_gross_pln=cw_t,
                        notes=note,
                    )
                )
            else:
                cw_days = work_weeks * 7
                cw_m, cw_t = _calc_amount_days(base_val, rate_val, cw_days, fte_work=fte_val)
                if ext_days == 0:
                    cw_note = (
                        f"Art. 31 ust. 4a ustawy zasiłkowej i art. 182¹ᶠ § 4 KP: wydłużenie wynosi 0 dni "
                        f"(niepełny dzień pominięto lub osiągnięto limit wieku/puli); zasiłek pomniejszony proporcjonalnie o {round(fte_val*100, 1)}%."
                    )
                    if extra_note:
                        cw_note = f"{cw_note} {extra_note}"
                else:
                    cw_note = extra_note
                target_list.append(
                    LeaveBreakdownItem(
                        label=f"{base_label} łączony z pracą ({fte_val} etatu)",
                        parent=parent_label,
                        weeks=float(work_weeks),
                        days=cw_days,
                        rate_percent=round(rate_val * (1.0 - fte_val) * 100, 2),
                        monthly_gross_pln=cw_m,
                        total_gross_pln=cw_t,
                        notes=cw_note,
                    )
                )
                if ext_days > 0:
                    ex_m, ex_t = _calc_amount_days(base_val, rate_val, ext_days)
                    ex_note = f"Art. 182¹ᶠ § 2 i § 4 KP: wydłużenie {ext_label} (niepełny dzień pominięto)."
                    if extra_note:
                        ex_note = f"{ex_note} {extra_note}"
                    target_list.append(
                        LeaveBreakdownItem(
                            label="Wydłużona część urlopu rodzicielskiego (bez pracy, art. 182¹ᶠ § 2 KP)",
                            parent=parent_label,
                            weeks=round(ext_days / 7.0, 2),
                            days=ext_days,
                            rate_percent=round(rate_val * 100, 1),
                            monthly_gross_pln=ex_m,
                            total_gross_pln=ex_t,
                            notes=ex_note,
                        )
                    )
        else:
            seg_days = segment_weeks * 7
            mp_m, mp_t = _calc_amount_days(base_val, rate_val, seg_days)
            target_list.append(
                LeaveBreakdownItem(
                    label=base_label,
                    parent=parent_label,
                    weeks=float(segment_weeks),
                    days=seg_days,
                    rate_percent=round(rate_val * 100, 1),
                    monthly_gross_pln=mp_m,
                    total_gross_pln=mp_t,
                    notes=extra_note,
                )
            )

    # 0A. Wyłączenie rodziny zastępczej zawodowej (art. 29 ust. 1 pkt 3) — ZAWSZE sprawdzane przed gałęzią 2. rodzica!
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

    # 0B. Limity wieku dla adopcji (14 lat) i rodziny zastępczej (7 / 10 lat) — ZAWSZE przed gałęzią 2. rodzica!
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
            weeks_until_age_limit = max(1, math.floor((max_age - req.child_age_years) * params.weeks_per_year + 1e-9))
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
            weeks_until_age_limit = max(1, math.floor((max_age - req.child_age_years) * params.weeks_per_year + 1e-9))

    p2_eligible = (
        not req.single_parent_or_no_second_parent
        and req.second_parent_has_sickness_insurance
        and req.second_parent_insurance_title != InsuranceTitle.NONE
    )

    # 0C. Sytuacja: Matka (Rodzic 1) nie podlega ubezpieczeniu chorobowemu w dniu porodu/przyjęcia dziecka
    if req.insurance_title == InsuranceTitle.NONE or not req.has_sickness_insurance_on_birth_date:
        if req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death and req.children_count == 1:
            return IntegratedCalculatorResponse(
                eligible=False,
                ineligibility_reason="Matka dziecka nie podlega ubezpieczeniu chorobowemu (brak prawa do 8 tyg. zasiłku macierzyńskiego z art. 180¹ § 1 KP), a przy urodzeniu martwego dziecka nie przysługuje urlop rodzicielski ani ojcowski dla drugiego rodzica.",
                benefit_base_parent1=0.0,
                benefit_base_parent2=0.0,
                benefit_base_explanation="Brak ubezpieczenia chorobowego matki na dzień porodu.",
                benefit_base_parent2_explanation=None,
                minimum_benefit_top_up_applied=False,
                equalization_to_100_pln=0.0,
                total_weeks=0.0,
                maternity_weeks=0,
                supplementary_maternity_weeks=0,
                parental_weeks_total=0.0,
                parental_weeks_extended_by_work=0.0,
                paternity_weeks=0,
                payer="Brak uprawnień do zasiłku macierzyńskiego",
                breakdown=[],
                total_estimated_gross_pln=0.0,
                warnings=[
                    f"Wsparcie dodatkowe (Poradnik ZUS 2026): Rodzinie przysługuje zasiłek pogrzebowy w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12, bez względu na czas trwania ciąży — na podstawie aktu urodzenia z adnotacją o martwym urodzeniu lub zaświadczenia lekarza/położnej).".replace(",", " "),
                ],
                required_documents=[
                    f"Wniosek Z-12 o zasiłek pogrzebowy ({params.funeral_grant_pln:,.0f} zł)".replace(",", " "),
                    "Odpis skrócony aktu urodzenia z adnotacją o martwym urodzeniu lub karta zgonu / zaświadczenie lekarza ginekologa albo położnej",
                ],
            )

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
        p2_warnings: list[str] = []
        p2_debt_suspended = (
            req.second_parent_insurance_title == InsuranceTitle.JDG
            and req.second_parent_contribution_debt_pln > debt_threshold
        )
        if p2_debt_suspended:
            p2_warnings.append(
                f"UWAGA (art. 2a ustawy zasiłkowej): Zadłużenie składkowe ZUS drugiego rodzica na JDG ({req.second_parent_contribution_debt_pln:.2f} zł > {debt_threshold:.2f} zł) wstrzymuje wypłatę zasiłku do czasu spłaty całości zadłużenia (przedawnienie po {params.claim_limitation_months} miesiącach)."
            )
        if req.second_parent_insurance_title in (InsuranceTitle.JDG, InsuranceTitle.ZLECENIE):
            p2_warnings.append(
                "Informacja (Poradnik ZUS 2026): Rozpoczęcie pobierania zasiłku macierzyńskiego przez osobę podlegającą dobrowolnie ubezpieczeniu chorobowemu (JDG/zlecenie) powoduje automatyczne wyrejestrowanie z tego ubezpieczenia. Po zakończeniu zasiłku wymagane jest ponowne zgłoszenie ZUS ZUA."
            )

        eff_children_u = (
            max(1, req.children_count - 1)
            if (req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death and req.children_count > 1)
            else req.children_count
        )
        if req.scenario in (BenefitScenario.ADOPTION, BenefitScenario.FOSTER) and (
            apply_reduced_9_weeks_regime
            or (weeks_until_age_limit is not None and weeks_until_age_limit < params.adoption_foster_min_maternity_weeks)
        ):
            apply_reduced_9_weeks_regime = True
            parental_pool = (
                params.adoption_foster_reduced_parental_weeks_za_zyciem
                if req.has_za_zyciem_certificate
                else params.adoption_foster_reduced_parental_weeks
            )
        elif req.has_za_zyciem_certificate:
            parental_pool = (
                params.parental_weeks_za_zyciem_single
                if eff_children_u == 1
                else params.parental_weeks_za_zyciem_multiple
            )
        else:
            parental_pool = (
                params.parental_weeks_single if eff_children_u == 1 else params.parental_weeks_multiple
            )

        orig_pool_u = parental_pool

        if req.scenario == BenefitScenario.ADOPTION and not apply_reduced_9_weeks_regime and weeks_until_age_limit is not None:
            if parental_pool > weeks_until_age_limit:
                parental_pool = weeks_until_age_limit
                p2_warnings.append(
                    f"Wymiar urlopu rodzicielskiego przy przysposobieniu ograniczono do granicy 14. roku życia dziecka ({parental_pool} tyg. — art. 183 § 4¹/§ 4⁴ KP)."
                )

        if req.scenario == BenefitScenario.ADOPTION and req.previously_used_foster_parental_weeks > 0:
            parental_pool = max(0, parental_pool - req.previously_used_foster_parental_weeks)
            p2_warnings.append(
                f"Wymiar urlopu rodzicielskiego obniżono o {req.previously_used_foster_parental_weeks} tyg. wykorzystanych wcześniej jako rodzina zastępcza (art. 183 § 8 KP)."
            )

        max_father_parental = min(parental_pool, max(0, orig_pool_u - params.parental_non_transferable_weeks))
        if req.father_takes_parental_weeks > max_father_parental:
            p2_warnings.append(
                f"Jeden rodzic może wykorzystać maksymalnie {max_father_parental} tyg. urlopu rodzicielskiego (skorygowano z {req.father_takes_parental_weeks} tyg.)."
            )
            father_par_weeks = max_father_parental
        elif req.father_takes_parental_weeks > 0:
            father_par_weeks = req.father_takes_parental_weeks
        else:
            father_par_weeks = max_father_parental

        ext_days_u = 0
        eff_work_u = 0
        fte_u = 0.0
        if (
            father_par_weeks > 0
            and req.father_combine_parental_with_work
            and req.father_work_fte_fraction > 0
            and req.father_combined_work_weeks > 0
        ):
            if req.second_parent_insurance_title != InsuranceTitle.UOP:
                p2_warnings.append(
                    "Łączenie urlopu rodzicielskiego z pracą (do 1/2 etatu) z proporcjonalnym wydłużeniem przysługuje wyłącznie przy umowie o pracę (art. 182¹ᵉ § 1 KP)."
                )
            else:
                fte_u = min(req.father_work_fte_fraction, params.parental_work_max_fte)
                if req.father_combined_work_weeks > father_par_weeks:
                    p2_warnings.append(
                        f"Liczbę tygodni łączenia urlopu rodzicielskiego z pracą ograniczono do wymiaru urlopu ojca ({father_par_weeks} tyg.)."
                    )
                eff_work_u = min(req.father_combined_work_weeks, father_par_weeks)
                max_ext_days_u = parental_pool * 7
                if (
                    req.scenario == BenefitScenario.ADOPTION
                    and not apply_reduced_9_weeks_regime
                    and weeks_until_age_limit is not None
                ):
                    max_ext_days_u = min(
                        max_ext_days_u, max(0, (weeks_until_age_limit - father_par_weeks) * 7)
                    )
                ext_days_u = _calc_work_extension_days(
                    eff_work_u, fte_u, req.father_work_during_extended_part, max_ext_days_u
                )

        breakdown_uninsured: list[LeaveBreakdownItem] = []
        if father_par_weeks > 0:
            _append_parental_segment(
                breakdown_uninsured,
                "Ojciec / Drugi rodzic (ubezpieczony)",
                base_p2,
                father_par_weeks,
                params.parental_rate_standard,
                eff_work_u,
                fte_u,
                ext_days_u,
                req.father_work_during_extended_part,
                "Urlop rodzicielski ojca (gdy matka nie podlega ubezpieczeniu — art. 31 ust. 3h)",
                extra_note="Finansowany z dotacji budżetu państwa do FUS (art. 31 ust. 3h ustawy zasiłkowej).",
            )

        pat_weeks = 0
        if req.father_takes_paternity_leave:
            if req.scenario == BenefitScenario.FOSTER:
                p2_warnings.append("Urlop ojcowski (2 tygodnie) przysługuje ojcu biologicznemu lub adopcyjnemu — nie dotyczy rodziny zastępczej.")
            else:
                pat_weeks = params.paternity_weeks
                if req.scenario == BenefitScenario.ADOPTION and weeks_until_age_limit is not None and weeks_until_age_limit < pat_weeks:
                    pat_weeks = weeks_until_age_limit
                    p2_warnings.append(
                        f"Urlop ojcowski przy adopcji ograniczono do granicy 14. roku życia dziecka ({pat_weeks} tyg. — art. 182³ § 1 pkt 2 KP)."
                    )
        if pat_weeks > 0:
            pat_days = pat_weeks * 7
            pt_m, pt_t = _calc_amount_days(base_p2, params.paternity_rate, pat_days)
            breakdown_uninsured.append(
                LeaveBreakdownItem(
                    label="Urlop ojcowski (art. 182³ KP)",
                    parent="Ojciec (ubezpieczony)",
                    weeks=float(pat_weeks),
                    days=pat_days,
                    rate_percent=round(params.paternity_rate * 100, 1),
                    monthly_gross_pln=pt_m,
                    total_gross_pln=pt_t,
                )
            )

        p2_emp_count = (
            req.second_parent_employer_insured_count
            if req.second_parent_employer_insured_count is not None
            else req.employer_insured_count
        )
        payer_p2 = _determine_payer(req.second_parent_insurance_title, p2_emp_count, params)
        p2_is_zus = payer_p2 == "Zakład Ubezpieczeń Społecznych (ZUS)"

        p2_warnings.insert(
            0,
            "Matka dziecka nie podlega ubezpieczeniu chorobowemu w dniu porodu, dlatego nie nabywa prawa do zasiłku za urlop macierzyński. Ubezpieczony ojciec ma jednak niezależne prawo do zasiłku za urlop rodzicielski (70%, art. 31 ust. 3h) oraz urlop ojcowski (2 tyg., 100%). Dodatkowo w szczególnych przypadkach (zgon, porzucenie, niezdolność do samodzielnej egzystencji lub podjęcie przez nieubezpieczoną matkę zatrudnienia ≥1/2 etatu — art. 29 ust. 9–10) ojciec może przejąć także urlop macierzyński.",
        )
        if top_up_applied:
            p2_warnings.append(
                f"Zastosowano ustawowe podwyższenie zasiłku macierzyńskiego do wysokości świadczenia rodzicielskiego ({min_monthly_floor:.2f} zł/mies. netto — art. 31 ust. 3a–3c)."
            )

        p2_docs: list[str] = []
        if req.second_parent_insurance_title == InsuranceTitle.UOP:
            p2_docs.append("Wniosek pracownika-ojca do pracodawcy o udzielenie urlopu rodzicielskiego (i ewentualnie ojcowskiego)")
            if p2_is_zus:
                p2_docs.append("Zaświadczenie płatnika składek Z-3 oraz zaświadczenie pracodawcy o udzielonym urlopie i ewentualnym łączeniu z pracą (§ 32 ust. 1 pkt 2 rozporządzenia)")
        elif req.second_parent_insurance_title == InsuranceTitle.ZLECENIE:
            p2_docs.append("Wniosek o zasiłek macierzyński ZAM złożony przed rozpoczęciem korzystania z zasiłku (§ 32 ust. 1 pkt 3)")
            if p2_is_zus:
                p2_docs.append("Zaświadczenie płatnika składek Z-3a (przesyła zleceniodawca do ZUS)")
        else:
            p2_docs.append("Wniosek o zasiłek macierzyński ZAM złożony do ZUS przed rozpoczęciem korzystania z zasiłku przez PUE/eZUS (§ 32 ust. 1 pkt 3)")

        if p2_is_zus:
            p2_docs.append("Dane dziecka (imię, nazwisko, PESEL, data i miejsce urodzenia) — przy płatniku ZUS nie trzeba dostarczać odpisu aktu urodzenia (§ 13 ust. 2 rozporządzenia)")
        else:
            p2_docs.append("Odpis skrócony aktu urodzenia dziecka (lub orzeczenie/zaświadczenie z sądu przy adopcji/pieczy)")
        p2_docs.append("Oświadczenie ojca, że matka dziecka nie posiada tytułu do ubezpieczenia chorobowego (z jej imieniem, nazwiskiem i PESEL — § 32 ust. 1 pkt 4)")

        total_days_u = sum(x.days or int(round(x.weeks * 7)) for x in breakdown_uninsured)
        return IntegratedCalculatorResponse(
            eligible=True,
            payout_suspended_due_to_debt=p2_debt_suspended,
            benefit_base_parent1=0.0,
            benefit_base_parent2=base_p2,
            benefit_base_explanation="Matka (Rodzic 1) nie podlega ubezpieczeniu chorobowemu — brak prawa do zasiłku dla matki.",
            benefit_base_parent2_explanation=base_p2_expl,
            minimum_benefit_top_up_applied=top_up_applied,
            equalization_to_100_pln=0.0,
            total_weeks=round(total_days_u / 7.0, 2),
            maternity_weeks=0,
            supplementary_maternity_weeks=0,
            parental_weeks_total=round((father_par_weeks * 7 + ext_days_u) / 7.0, 2),
            parental_weeks_extended_by_work=round(ext_days_u / 7.0, 2),
            paternity_weeks=pat_weeks,
            payer=payer_p2,
            breakdown=breakdown_uninsured,
            total_estimated_gross_pln=round(sum(x.total_gross_pln for x in breakdown_uninsured), 2),
            warnings=p2_warnings,
            required_documents=p2_docs,
        )

    # Zadłużenie JDG (art. 2a) + informacja o automatycznym wyrejestrowaniu z dobrowolnego chorobowego (JDG i ZLECENIE)
    p1_debt_suspended = req.insurance_title == InsuranceTitle.JDG and req.contribution_debt_pln > debt_threshold
    p2_has_blocking_debt = (
        p2_eligible
        and req.second_parent_insurance_title == InsuranceTitle.JDG
        and req.second_parent_contribution_debt_pln > debt_threshold
    )

    if p1_debt_suspended:
        warnings.append(
            f"UWAGA (art. 2a ustawy zasiłkowej): Zadłużenie ZUS Rodzica 1 na JDG ({req.contribution_debt_pln:.2f} zł > {params.debt_threshold_min_wage_fraction*100:.1f}% płacy minimalnej tj. {debt_threshold:.2f} zł) wstrzymuje wypłatę zasiłku do czasu spłaty całości zadłużenia (przedawnienie po {params.claim_limitation_months} miesiącach)."
        )
    if req.insurance_title in (InsuranceTitle.JDG, InsuranceTitle.ZLECENIE):
        warnings.append(
            "Informacja (Poradnik ZUS 2026): Rozpoczęcie pobierania zasiłku macierzyńskiego przez osobę podlegającą dobrowolnie ubezpieczeniu chorobowemu (JDG lub umowa zlecenie) powoduje automatyczne i obowiązkowe wyrejestrowanie z tego ubezpieczenia. Po zakończeniu zasiłku, aby ponownie podlegać chorobowemu, należy złożyć zgłoszenie ZUS ZUA."
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
    p1_is_zus = payer == "Zakład Ubezpieczeń Społecznych (ZUS)"

    # Urodzenie martwego dziecka lub zgon dziecka przed upływem 8 tygodni życia (art. 180¹ § 1 KP)
    if req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death:
        if req.children_count == 1:
            sb_weeks = params.stillbirth_maternity_weeks
            sb_days = sb_weeks * 7
            sb_monthly, sb_total = _calc_amount_days(base_p1, params.maternity_rate_standard, sb_days)
            sb_warnings = list(warnings)
            sb_warnings.append(
                f"Zgodnie z art. 180¹ § 1 Kodeksu pracy przysługuje urlop i zasiłek macierzyński (100%) w wymiarze {sb_weeks} tygodni po porodzie (nie krócej niż {params.child_death_min_days} dni od dnia zgonu). W razie zgonu dziecka po upływie 8 tygodni życia zasiłek przysługuje przez {params.child_death_min_days} dni od dnia zgonu (art. 180¹ § 2 KP)."
            )
            if req.pre_birth_maternity_weeks > 0:
                sb_warnings.append(
                    f"Uwaga (art. 180¹ § 1 KP): Gwarantowane {sb_weeks} tygodni przysługuje po porodzie — niezależnie od {req.pre_birth_maternity_weeks} tyg. wykorzystanych przed przewidywaną datą porodu."
                )
            sb_warnings.append(
                f"Wsparcie dodatkowe (Poradnik ZUS 2026): W przypadku urodzenia martwego dziecka (bez względu na czas trwania ciąży) rodzinie przysługuje również zasiłek pogrzebowy z ZUS w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12 w ciągu 12 mies. od pochówku).".replace(",", " ")
            )
            if top_up_applied:
                sb_warnings.append(
                    f"Zastosowano ustawowe podwyższenie zasiłku macierzyńskiego do wysokości świadczenia rodzicielskiego ({min_monthly_floor:.2f} zł/mies. netto — art. 31 ust. 3a–3c)."
                )
            sb_docs = [
                "Odpis skrócony aktu urodzenia z adnotacją o martwym urodzeniu ALBO — gdy nie sporządzono aktu urodzenia — zaświadczenie lekarza ginekologa lub położnej o martwym urodzeniu bez względu na czas trwania ciąży (§ 13 ust. 1 pkt 2 rozporządzenia)",
                "Wniosek o urlop macierzyński (do pracodawcy) lub wniosek ZAM (do ZUS)",
                f"Wniosek Z-12 o zasiłek pogrzebowy ({params.funeral_grant_pln:,.0f} zł) — opcjonalnie".replace(",", " "),
            ]
            if p1_is_zus:
                sb_docs.append("Przy płatniku ZUS: jeżeli sporządzono akt urodzenia, nie trzeba składać odpisu — ZUS pozyskuje go z USC na podstawie danych dziecka (§ 13 ust. 2 rozporządzenia)")
            return IntegratedCalculatorResponse(
                eligible=True,
                payout_suspended_due_to_debt=p1_debt_suspended,
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
                        days=sb_days,
                        rate_percent=round(params.maternity_rate_standard * 100, 1),
                        monthly_gross_pln=sb_monthly,
                        total_gross_pln=sb_total,
                        notes=f"Wymiar {sb_weeks} tygodni po porodzie, nie krócej niż {params.child_death_min_days} dni od dnia zgonu dziecka.",
                    )
                ],
                total_estimated_gross_pln=sb_total,
                warnings=sb_warnings,
                required_documents=sb_docs,
            )
        else:
            surviving = req.children_count - 1
            warnings.append(
                f"Przy porodzie mnogim, w którym jedno z dzieci urodziło się martwe lub zmarło, przysługuje urlop macierzyński stosowny do liczby dzieci pozostałych przy życiu ({surviving}), nie krócej niż {params.stillbirth_maternity_weeks} tygodni (art. 180¹ § 1 KP)."
            )
            warnings.append(
                f"Wsparcie dodatkowe (Poradnik ZUS 2026): Z tytułu martwego urodzenia / zgonu dziecka przysługuje również zasiłek pogrzebowy z ZUS w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12).".replace(",", " ")
            )
            docs.append(
                f"Wniosek Z-12 o zasiłek pogrzebowy ({params.funeral_grant_pln:,.0f} zł) oraz akt urodzenia z adnotacją o martwym urodzeniu / zaświadczenie lekarza lub położnej (§ 13 ust. 1 pkt 2)".replace(",", " ")
            )

    # Wymiar urlopu macierzyńskiego
    effective_children = (
        max(1, req.children_count - 1)
        if (req.scenario == BenefitScenario.BIRTH and req.stillbirth_or_early_death and req.children_count > 1)
        else req.children_count
    )
    child_key = str(min(effective_children, 5))
    standard_maternity_weeks = params.maternity_weeks_by_children.get(child_key, 20)
    maternity_weeks = standard_maternity_weeks

    pre_weeks = 0
    if req.scenario == BenefitScenario.BIRTH and req.pre_birth_maternity_weeks > 0:
        pre_weeks = min(req.pre_birth_maternity_weeks, params.maternity_pre_birth_max_weeks)
        pre_note = (
            f"Uwzględniono {pre_weeks} tyg. urlopu macierzyńskiego przed porodem (maks. {params.maternity_pre_birth_max_weeks} tyg. — art. 180 § 2 KP). Po porodzie pozostaje {maternity_weeks - pre_weeks} tyg."
        )
        if req.payment_variant == PaymentVariant.COMBINED_81_5:
            pre_note += " Przed porodem zasiłek wypłacany jest wstępnie w wysokości 100%, a po złożeniu wniosku z art. 30a w ciągu 21 dni po porodzie całość okresu rozliczana jest stawką 81,5%."
        warnings.append(pre_note)

    if req.scenario in (BenefitScenario.ADOPTION, BenefitScenario.FOSTER):
        min_mat = params.adoption_foster_min_maternity_weeks
        if apply_reduced_9_weeks_regime or (weeks_until_age_limit is not None and weeks_until_age_limit < min_mat):
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
    elif req.has_za_zyciem_certificate:
        parental_base_weeks = (
            params.parental_weeks_za_zyciem_single
            if effective_children == 1
            else params.parental_weeks_za_zyciem_multiple
        )
    else:
        parental_base_weeks = (
            params.parental_weeks_single if effective_children == 1 else params.parental_weeks_multiple
        )

    if req.has_za_zyciem_certificate:
        if p1_is_zus:
            docs.append("Oświadczenie ubezpieczonego o posiadaniu przez dziecko zaświadczenia „Za życiem” (art. 61b ust. 4a ustawy zasiłkowej)")
        else:
            docs.append("Kopia zaświadczenia lekarskiego „Za życiem” (art. 4 ust. 3 ustawy o wsparciu kobiet w ciąży i rodzin „Za życiem”)")

    original_parental_pool = parental_base_weeks

    # Art. 183 § 4¹ i § 4⁴ KP: przy adopcji poza trybem minimalnym (§ 3 / § 4² / § 4⁵) urlop rodzicielski przysługuje nie dłużej niż do ukończenia 14. r.ż.
    if (
        req.scenario == BenefitScenario.ADOPTION
        and not apply_reduced_9_weeks_regime
        and weeks_until_age_limit is not None
    ):
        remaining_until_14 = max(0, weeks_until_age_limit - maternity_weeks - supplementary_weeks)
        if parental_base_weeks > remaining_until_14:
            parental_base_weeks = remaining_until_14
            reduced_par_ref = (
                params.adoption_foster_reduced_parental_weeks_za_zyciem
                if req.has_za_zyciem_certificate
                else params.adoption_foster_reduced_parental_weeks
            )
            warnings.append(
                f"Zgodnie z art. 183 § 4¹/§ 4⁴ KP urlop rodzicielski przy przysposobieniu przysługuje nie dłużej niż do ukończenia przez dziecko 14. roku życia — po wykorzystaniu {maternity_weeks} tyg. na warunkach macierzyńskiego pozostaje {parental_base_weeks} tyg. rodzicielskiego. W razie wyboru trybu minimalnego z art. 183 § 3 (9 tyg. na warunkach macierzyńskiego) przysługuje gwarantowane {reduced_par_ref} tyg. rodzicielskiego (art. 183 § 4²/§ 4⁵ KP)."
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

    # Podział macierzyńskiego (art. 180 § 4 i § 6 KP: min. 14 lub 8 tyg. PO porodzie dla matki; art. 183 § 2 KP dla adopcji/pieczy)
    if not p2_eligible:
        mother_mat = maternity_weeks
        father_mat = 0
    elif req.scenario == BenefitScenario.BIRTH:
        min_mother_after_birth = 8 if req.mother_early_transfer_8_weeks else params.maternity_min_mother_weeks
        min_mother_total = min(maternity_weeks, pre_weeks + min_mother_after_birth)
        mother_mat = req.mother_maternity_weeks if req.mother_maternity_weeks is not None else maternity_weeks
        if mother_mat < min_mother_total:
            extra_pre = f" (w tym {pre_weeks} tyg. przed porodem + min. {min_mother_after_birth} tyg. po porodzie)" if pre_weeks > 0 else ""
            warnings.append(
                f"Pierwsze {min_mother_after_birth} tygodni urlopu macierzyńskiego po porodzie matka musi wykorzystać osobiście{extra_pre}. Skorygowano wymiar matki do {min_mother_total} tyg."
            )
            mother_mat = min_mother_total
        mother_mat = min(mother_mat, maternity_weeks)
        father_mat = maternity_weeks - mother_mat
    else:
        mother_mat = min(req.mother_maternity_weeks, maternity_weeks) if req.mother_maternity_weeks is not None else maternity_weeks
        min_first_parent = min(
            maternity_weeks,
            8 if req.mother_early_transfer_8_weeks else params.maternity_min_mother_weeks,
        )
        if 0 < mother_mat < min_first_parent:
            warnings.append(
                f"Przy dzieleniu urlopu na warunkach urlopu macierzyńskiego pierwszy rodzic musi wykorzystać co najmniej {min_first_parent} tyg. przed rezygnacją na rzecz drugiego rodzica (art. 183 § 2 w zw. z art. 180 § 4/§ 6 KP oraz art. 29 ust. 4 ustawy zasiłkowej; aby całość przejął drugi rodzic od 1. dnia, wpisz 0 tyg. dla Rodzica 1). Skorygowano wymiar Rodzica 1 do {min_first_parent} tyg."
            )
            mother_mat = min_first_parent
        father_mat = max(0, maternity_weeks - mother_mat)

    # Podział rodzicielskiego (art. 182¹ᵃ § 4 KP: 9 tyg. nieprzenoszalnych z puli pierwotnej dla każdego rodzica)
    non_transferable = params.parental_non_transferable_weeks
    max_single_parent_parental = min(parental_base_weeks, max(0, original_parental_pool - non_transferable))

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
        if father_parental < non_transferable and original_parental_pool >= non_transferable and parental_base_weeks >= non_transferable:
            warnings.append(
                f"Drugiemu rodzicowi przysługuje {non_transferable} tyg. nieprzenoszalnego urlopu rodzicielskiego (art. 182¹ᵃ § 4 KP). Niewykorzystana część przepada."
            )

    default_mother_parental = max(0, min(max_single_parent_parental, parental_base_weeks - father_parental))
    if req.mother_takes_parental_weeks is not None:
        if req.mother_takes_parental_weeks > default_mother_parental:
            warnings.append(
                f"Wymiar urlopu rodzicielskiego Rodzica 1 skorygowano z {req.mother_takes_parental_weeks} do {default_mother_parental} tyg. (limit puli wspólnej i 9 tyg. nieprzenoszalnych)."
            )
        mother_parental = min(req.mother_takes_parental_weeks, default_mother_parental)
    else:
        mother_parental = default_mother_parental

    # Łączenie urlopu rodzicielskiego z pracą — wspólny limit wydłużenia (art. 182¹ᶠ § 1, § 1¹, § 4, § 7 KP)
    remaining_ext_cap_days = parental_base_weeks * 7
    if (
        req.scenario == BenefitScenario.ADOPTION
        and not apply_reduced_9_weeks_regime
        and weeks_until_age_limit is not None
    ):
        max_ext_until_14_days = max(
            0, (weeks_until_age_limit - maternity_weeks - supplementary_weeks - mother_parental - father_parental) * 7
        )
        if remaining_ext_cap_days > max_ext_until_14_days:
            remaining_ext_cap_days = max_ext_until_14_days
            if req.combine_parental_with_work or req.father_combine_parental_with_work:
                warnings.append(
                    "Wydłużenie urlopu rodzicielskiego z tytułu łączenia z pracą przy przysposobieniu ograniczono tak, aby łączny okres nie przekroczył ukończenia przez dziecko 14. roku życia (art. 183 § 4¹/§ 4⁴ KP)."
                )

    # Rodzic 1
    extended_days_p1 = 0
    effective_work_weeks_p1 = 0
    fte_p1 = 0.0
    if req.combine_parental_with_work and req.work_fte_fraction > 0 and req.combined_work_weeks > 0 and mother_parental > 0:
        if req.insurance_title != InsuranceTitle.UOP:
            warnings.append(
                "Łączenie urlopu rodzicielskiego z pracą (do 1/2 etatu) z proporcjonalnym wydłużeniem dotyczy pracowników na umowie o pracę (art. 182¹ᵉ § 1 KP)."
            )
        else:
            fte_p1 = min(req.work_fte_fraction, params.parental_work_max_fte)
            if req.combined_work_weeks > mother_parental:
                warnings.append(
                    f"Liczbę tygodni łączenia urlopu rodzicielskiego z pracą Rodzica 1 ograniczono z {req.combined_work_weeks} do {mother_parental} tyg. (wymiar urlopu Rodzica 1)."
                )
            effective_work_weeks_p1 = min(req.combined_work_weeks, mother_parental)
            extended_days_p1 = _calc_work_extension_days(
                effective_work_weeks_p1, fte_p1, req.work_during_extended_part, remaining_ext_cap_days
            )
            remaining_ext_cap_days = max(0, remaining_ext_cap_days - extended_days_p1)

    # Rodzic 2
    effective_work_weeks_p2 = 0
    fte_p2 = 0.0
    if (
        p2_eligible
        and req.father_combine_parental_with_work
        and req.father_work_fte_fraction > 0
        and req.father_combined_work_weeks > 0
        and father_parental > 0
    ):
        if req.second_parent_insurance_title != InsuranceTitle.UOP:
            warnings.append(
                "Łączenie urlopu rodzicielskiego z pracą dla drugiego rodzica z proporcjonalnym wydłużeniem przysługuje wyłącznie przy umowie o pracę (art. 182¹ᵉ § 1 KP)."
            )
        else:
            fte_p2 = min(req.father_work_fte_fraction, params.parental_work_max_fte)
            if req.father_combined_work_weeks > father_parental:
                warnings.append(
                    f"Liczbę tygodni łączenia urlopu rodzicielskiego z pracą Rodzica 2 ograniczono z {req.father_combined_work_weeks} do {father_parental} tyg. (wymiar urlopu Rodzica 2)."
                )
            effective_work_weeks_p2 = min(req.father_combined_work_weeks, father_parental)

    # Stawki procentowe
    if req.payment_variant == PaymentVariant.COMBINED_81_5:
        mat_rate = params.combined_21_days_rate
        mother_parental_rate = params.combined_21_days_rate
        father_shared_parental_rate = params.combined_21_days_rate
        father_non_transferable_rate = params.non_transferable_parental_rate
        warnings.append(
            f"Wariant 81,5% wymaga złożenia wniosku lub pisemnej deklaracji w nieprzekraczalnym terminie {params.combined_application_deadline_days} dni po porodzie/przyjęciu dziecka (art. 30a ustawy zasiłkowej). Część nieprzenoszalna drugiego rodzica ({non_transferable} tyg.) jest zawsze płatna {round(father_non_transferable_rate*100, 1)}%."
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
    m_total_paid = 0.0
    if mother_mat > 0:
        m_days = mother_mat * 7
        m_monthly, m_total_paid = _calc_amount_days(base_p1, mat_rate, m_days)
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop macierzyński" if req.scenario == BenefitScenario.BIRTH else "Urlop na warunkach urlopu macierzyńskiego",
                parent=p1_label,
                weeks=float(mother_mat),
                days=m_days,
                rate_percent=round(mat_rate * 100, 1),
                monthly_gross_pln=m_monthly,
                total_gross_pln=m_total_paid,
            )
        )

    fm_total_paid = 0.0
    if father_mat > 0:
        fm_days = father_mat * 7
        fm_monthly, fm_total_paid = _calc_amount_days(base_p2, mat_rate, fm_days)
        breakdown.append(
            LeaveBreakdownItem(
                label="Przejęta część urlopu macierzyńskiego" if req.scenario == BenefitScenario.BIRTH else "Część urlopu na warunkach macierzyńskiego",
                parent=p2_label,
                weeks=float(father_mat),
                days=fm_days,
                rate_percent=round(mat_rate * 100, 1),
                monthly_gross_pln=fm_monthly,
                total_gross_pln=fm_total_paid,
            )
        )

    # Wyrównanie do 100% (art. 31 ust. 4 ustawy zasiłkowej):
    # Przysługuje, gdy w 1. roku życia dziecka nie wykorzystano ani 1 dnia urlopu rodzicielskiego w stawce 81,5% (art. 31 ust. 3)
    # — tzn. mother_parental == 0 oraz ojciec nie korzystał z puli wspólnej (<= 9 tyg. nieprzenoszalnych @ 70%).
    equalization_to_100_pln = 0.0
    father_shared_used = max(0, father_parental - non_transferable)
    if (
        req.payment_variant == PaymentVariant.COMBINED_81_5
        and mother_parental == 0
        and father_shared_used == 0
        and (mother_mat > 0 or father_mat > 0)
    ):
        eq_p1 = 0.0
        if mother_mat > 0:
            _, m_100_total = _calc_amount_days(base_p1, params.maternity_rate_standard, mother_mat * 7, track_top_up=False)
            eq_p1 = max(0.0, round(m_100_total - m_total_paid, 2))
        eq_p2 = 0.0
        if father_mat > 0:
            _, fm_100_total = _calc_amount_days(base_p2, params.maternity_rate_standard, father_mat * 7, track_top_up=False)
            eq_p2 = max(0.0, round(fm_100_total - fm_total_paid, 2))
        equalization_to_100_pln = round(eq_p1 + eq_p2, 2)
        if equalization_to_100_pln > 0:
            warnings.append(
                f"Wyrównanie do 100% (art. 31 ust. 4 ustawy zasiłkowej): Ponieważ nie zaplanowano żadnego dnia urlopu rodzicielskiego w stawce 81,5% (art. 31 ust. 3) w pierwszym roku życia dziecka, na wniosek przysługuje jednorazowe wyrównanie pobranego zasiłku za urlop macierzyński do 100% w szacowanej kwocie {equalization_to_100_pln:.2f} zł brutto."
            )
        else:
            warnings.append(
                "Informacja (art. 31 ust. 4 i art. 31 ust. 3a): Nie zaplanowano urlopu rodzicielskiego w stawce 81,5%, lecz zasiłek macierzyński był już podwyższony do minimum 1 000,00 zł/mies. (100% podstawy nie przekracza wypłaconej kwoty — wyrównanie wynosi 0,00 zł)."
            )

    # 2. Uzupełniający urlop macierzyński (zawsze 100% — art. 31 ust. 1)
    if supplementary_weeks > 0:
        s_days = supplementary_weeks * 7
        s_monthly, s_total = _calc_amount_days(base_p1, params.supplementary_maternity_rate, s_days)
        supp_note = (
            "Udzielany jednorazowo bezpośrednio po urlopie macierzyńskim (wniosek do pracodawcy min. 21 dni przed końcem urlopu macierzyńskiego — art. 180² § 4 KP)."
            if req.insurance_title == InsuranceTitle.UOP
            else "Przysługuje jednorazowo bezpośrednio po zasiłku za okres urlopu macierzyńskiego (wniosek do płatnika/ZUS przed zakończeniem pobierania zasiłku macierzyńskiego — § 26 pkt 3 rozporządzenia)."
        )
        breakdown.append(
            LeaveBreakdownItem(
                label="Uzupełniający urlop macierzyński (wcześniak / hospitalizacja)",
                parent=p1_label,
                weeks=float(supplementary_weeks),
                days=s_days,
                rate_percent=round(params.supplementary_maternity_rate * 100, 1),
                monthly_gross_pln=s_monthly,
                total_gross_pln=s_total,
                notes=supp_note,
            )
        )

    # 3. Urlop rodzicielski rodzica 1
    if mother_parental > 0:
        _append_parental_segment(
            breakdown,
            p1_label,
            base_p1,
            mother_parental,
            mother_parental_rate,
            effective_work_weeks_p1,
            fte_p1,
            extended_days_p1,
            req.work_during_extended_part,
            "Urlop rodzicielski",
        )

    # 4. Urlop rodzicielski rodzica 2 (z poprawnym rozbiciem 81,5% / 70% także przy łączeniu z pracą!)
    extended_days_p2 = 0
    if father_parental > 0:
        if (
            req.payment_variant == PaymentVariant.COMBINED_81_5
            and father_parental > non_transferable
            and father_shared_parental_rate != father_non_transferable_rate
        ):
            shared_fw = father_parental - non_transferable
            work_shared = min(effective_work_weeks_p2, shared_fw)
            work_nontrans = max(0, effective_work_weeks_p2 - work_shared)

            total_ext_p2 = _calc_work_extension_days(
                effective_work_weeks_p2, fte_p2, req.father_work_during_extended_part, remaining_ext_cap_days
            )
            remaining_ext_cap_days = max(0, remaining_ext_cap_days - total_ext_p2)
            if effective_work_weeks_p2 > 0 and work_nontrans > 0:
                ext_days_shared = min(
                    total_ext_p2,
                    math.floor((total_ext_p2 * work_shared) / effective_work_weeks_p2 + 0.5),
                )
                ext_days_nontrans = total_ext_p2 - ext_days_shared
            else:
                ext_days_shared = total_ext_p2
                ext_days_nontrans = 0
            extended_days_p2 = total_ext_p2

            _append_parental_segment(
                breakdown,
                p2_label,
                base_p2,
                shared_fw,
                father_shared_parental_rate,
                work_shared,
                fte_p2,
                ext_days_shared,
                req.father_work_during_extended_part,
                "Urlop rodzicielski (część z puli wspólnej)",
            )
            _append_parental_segment(
                breakdown,
                p2_label,
                base_p2,
                non_transferable,
                father_non_transferable_rate,
                work_nontrans,
                fte_p2,
                ext_days_nontrans,
                req.father_work_during_extended_part,
                f"Urlop rodzicielski ({non_transferable} tyg. nieprzenoszalnych)",
            )
        else:
            extended_days_p2 = _calc_work_extension_days(
                effective_work_weeks_p2, fte_p2, req.father_work_during_extended_part, remaining_ext_cap_days
            )
            remaining_ext_cap_days = max(0, remaining_ext_cap_days - extended_days_p2)
            _append_parental_segment(
                breakdown,
                p2_label,
                base_p2,
                father_parental,
                father_non_transferable_rate,
                effective_work_weeks_p2,
                fte_p2,
                extended_days_p2,
                req.father_work_during_extended_part,
                f"Urlop rodzicielski (w tym do {non_transferable} tyg. nieprzenoszalnych)",
            )

    total_extended_days = extended_days_p1 + extended_days_p2

    # 5. Urlop ojcowski (art. 182³ KP)
    paternity_weeks = 0
    if req.father_takes_paternity_leave and p2_eligible:
        if req.scenario == BenefitScenario.FOSTER:
            warnings.append("Urlop ojcowski (2 tygodnie) przysługuje ojcu biologicznemu lub adopcyjnemu — nie dotyczy rodziny zastępczej.")
        else:
            paternity_weeks = params.paternity_weeks
            if req.scenario == BenefitScenario.ADOPTION and weeks_until_age_limit is not None and weeks_until_age_limit < paternity_weeks:
                paternity_weeks = weeks_until_age_limit
                warnings.append(
                    f"Urlop ojcowski przy przysposobieniu ograniczono do granicy 14. roku życia dziecka ({paternity_weeks} tyg. — art. 182³ § 1 pkt 2 KP)."
                )

    if paternity_weeks > 0:
        pat_days = paternity_weeks * 7
        pat_m, pat_t = _calc_amount_days(base_p2, params.paternity_rate, pat_days)
        pat_note = (
            "Wniosek do pracodawcy min. 7 dni przed rozpoczęciem (art. 182³ § 2 KP)."
            if req.second_parent_insurance_title == InsuranceTitle.UOP
            else "Dla niepracownika (JDG/zlecenie): wniosek ZAM złożony przed terminem rozpoczęcia korzystania z zasiłku (§ 33 ust. 1 pkt 3 rozporządzenia)."
        )
        breakdown.append(
            LeaveBreakdownItem(
                label="Urlop ojcowski",
                parent="Ojciec adopcyjny" if req.scenario == BenefitScenario.ADOPTION else p2_label,
                weeks=float(paternity_weeks),
                days=pat_days,
                rate_percent=round(params.paternity_rate * 100, 1),
                monthly_gross_pln=pat_m,
                total_gross_pln=pat_t,
                notes=pat_note,
            )
        )

    p2_claims_any_leave = (father_mat + father_parental + paternity_weeks) > 0
    p2_debt_suspended = p2_has_blocking_debt and p2_claims_any_leave
    payout_suspended_due_to_debt = p1_debt_suspended or p2_debt_suspended
    if p2_debt_suspended:
        warnings.append(
            f"UWAGA (art. 2a ustawy zasiłkowej): Zadłużenie ZUS Rodzica 2 na JDG ({req.second_parent_contribution_debt_pln:.2f} zł > {debt_threshold:.2f} zł) wstrzymuje wypłatę zasiłku dla 2. rodzica do czasu spłaty całości zadłużenia."
        )

    if top_up_applied:
        warnings.append(
            f"Zastosowano ustawowe podwyższenie zasiłku macierzyńskiego do wysokości świadczenia rodzicielskiego ({min_monthly_floor:.2f} zł/mies. netto — art. 31 ust. 3a–3c ustawy zasiłkowej; przy złożonym PIT-2 zaliczka PIT wynosi 0 zł do 2 500 zł/mies., więc netto = brutto; przy łączeniu z pracą limit podwyższenia jest zmniejszany proporcjonalnie do wymiaru urlopu)."
        )

    # Dokumenty (zgodne z rozporządzeniem z 27.09.2026 r.)
    if req.insurance_title == InsuranceTitle.UOP:
        docs.insert(0, "Wniosek do pracodawcy o udzielenie urlopu macierzyńskiego i rodzicielskiego")
        if p1_is_zus:
            docs.append("Zaświadczenie płatnika składek Z-3 (przesyła pracodawca do ZUS)")
    elif req.insurance_title == InsuranceTitle.ZLECENIE:
        docs.insert(0, "Wniosek o zasiłek macierzyński ZAM")
        if p1_is_zus:
            docs.append("Zaświadczenie płatnika składek Z-3a (przesyła zleceniodawca do ZUS)")
    else:
        docs.insert(0, "Wniosek o zasiłek macierzyński ZAM (składany bezpośrednio do ZUS przez PUE/eZUS)")

    if req.scenario == BenefitScenario.BIRTH:
        if p1_is_zus:
            docs.append("Dane dziecka (imię, nazwisko, PESEL, data i miejsce urodzenia) — przy płatniku ZUS nie trzeba składać odpisu aktu urodzenia (§ 13 ust. 2 rozporządzenia)")
        else:
            docs.append("Odpis skrócony aktu urodzenia dziecka (okazywany pracodawcy / płatnikowi składek)")
    elif req.scenario == BenefitScenario.ADOPTION:
        docs.append("Oświadczenie o dacie przyjęcia dziecka na wychowanie oraz zaświadczenie sądu opiekuńczego o dacie wystąpienia o przysposobienie z datą urodzenia dziecka (§ 16 ust. 1)")
    else:
        docs.append("Orzeczenie sądu opiekuńczego o umieszczeniu dziecka w rodzinie zastępczej niezawodowej lub umowa ze starostą oraz dokument potwierdzający wiek dziecka (§ 16 ust. 2)")
        if req.foster_deferred_school:
            docs.append("Kopia prawomocnej decyzji o odroczeniu obowiązku szkolnego (§ 16 ust. 2 pkt 3)")

    total_days = sum(item.days or int(round(item.weeks * 7)) for item in breakdown)
    total_weeks = round(total_days / 7.0, 2)
    total_gross = round(sum(item.total_gross_pln for item in breakdown) + equalization_to_100_pln, 2)

    return IntegratedCalculatorResponse(
        eligible=True,
        payout_suspended_due_to_debt=payout_suspended_due_to_debt,
        benefit_base_parent1=base_p1,
        benefit_base_parent2=base_p2,
        benefit_base_explanation=base_p1_expl,
        benefit_base_parent2_explanation=base_p2_expl,
        minimum_benefit_top_up_applied=top_up_applied,
        equalization_to_100_pln=equalization_to_100_pln,
        total_weeks=total_weeks,
        maternity_weeks=maternity_weeks,
        supplementary_maternity_weeks=supplementary_weeks,
        parental_weeks_total=round(((mother_parental + father_parental) * 7 + total_extended_days) / 7.0, 2),
        parental_weeks_extended_by_work=round(total_extended_days / 7.0, 2),
        paternity_weeks=paternity_weeks,
        payer=payer,
        breakdown=breakdown,
        total_estimated_gross_pln=total_gross,
        warnings=warnings,
        required_documents=docs,
    )
