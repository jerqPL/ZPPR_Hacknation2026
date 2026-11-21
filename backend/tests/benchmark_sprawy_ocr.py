"""
Benchmark i definicje oczekiwań (ground truth) dla wszystkich 87 rzeczywistych spraw ZUS w folderze Sprawy/.

ZASADA UCZCIWEGO TESTU:
- Parser otrzymuje zanonimizowaną nazwę pliku ("case_XX.pdf"), więc NIE MOŻE podglądać nazwy pliku z Sprawy/.
- Każda sprawa jest oceniana pod kątem:
  1. Poprawności OCR i wykrycia co najmniej jednego formularza ZUS.
  2. Domeny dokumentu (sickness_pregnancy vs maternity_parental).
  3. Statusu weryfikacji (odmowa vs brak fałszywej odmowy).
  4. Scenariusza (birth / adoption / foster — brak fałszywych adopcji/rodzin zastępczych).
  5. Zadłużenia składkowego (wykrycie w sprawach z art. 2a oraz brak fałszywego zadłużenia w pozostałych).
  6. Flag szczególnych właściwych dla danej sprawy (martwe urodzenie, wcześniak/uzupełniający, Za życiem,
     łączenie urlopu z pracą, urlop ojcowski, bliźnięta/trojaczki, matka nieubezpieczona, ustanie/likwidacja,
     tytuł ubezpieczenia gdy jawnie stanowi oś sprawy).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SPRAWY_DIR = REPO_ROOT / "Sprawy"

if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.models.guidance import PdfAnalysisResult  # noqa: E402
from app.services.pdf_parser_service import _analyze_extracted_content, analyze_pdf_bytes  # noqa: E402


@dataclass(frozen=True)
class SprawaExpectation:
    filename: str
    expected_domains: tuple[str, ...]
    expect_denied: bool = False
    expected_scenario: str | None = "birth"
    expect_debt: bool = False
    expect_stillbirth: bool = False
    expect_premature: bool = False
    expect_za_zyciem: bool = False
    expect_combine_work: bool = False
    expect_paternity: bool = False
    expect_mother_uninsured: bool = False
    expect_terminated_special: bool = False
    min_children: int | None = None
    expected_title: str | None = None
    extra_notes: str = ""


def build_sprawy_expectations() -> list[SprawaExpectation]:
    """Buduje deterministyczną specyfikację testową dla wszystkich 87 plików PDF w Sprawy/."""
    files = sorted(p.name for p in SPRAWY_DIR.glob("*.pdf"))
    specs: list[SprawaExpectation] = []

    for name in files:
        low = name.lower()

        is_pregnancy_only = (
            "chorobowy w ciąży" in low
            and "mac." not in low
            and "macierzyński" not in low
        )
        is_art30_wysokosci = "w wysokości" in low

        if is_pregnancy_only:
            domains = ("sickness_pregnancy",)
            scenario: str | None = None
        elif is_art30_wysokosci:
            domains = ("maternity_parental", "sickness_pregnancy")
            scenario = "birth"
        else:
            domains = ("maternity_parental",)
            if "rodzina zastępcza" in low:
                scenario = "foster"
            elif "przysposobienie" in low or "przyjęcie dziecka na wychowanie" in low:
                scenario = "adoption"
            else:
                scenario = "birth"

        # Julia No_4 zawiera w treści faktyczną decyzję odmowną ZUS ("ODMÓWIĆ PRAWA DO ZASIŁKU MACIERZYŃSKIEGO")
        expect_denied = "odmow" in low or name.startswith("Julia No_4_")
        expect_debt = "zadłużeni" in low
        expect_stillbirth = "martwe urodzenie" in low or "martwourodzone" in low
        expect_premature = (
            "wcześniak" in low
            or "uzupełniając" in low
            or "uzup." in low
            or "masa poniżej 1000" in low
        )
        expect_za_zyciem = "za życiem" in low
        expect_combine_work = "łączenie" in low or "łęczenie" in low or "łącznie urlop rodz. z pracą" in low
        expect_paternity = "urlop ojcowski" in low or "urlopu ojcowskiego" in low
        expect_mother_uninsured = "matka nieubezpieczona" in low
        expect_terminated_special = is_art30_wysokosci or "likwidacji" in low or "po ustaniu ubezp" in low

        min_children: int | None = None
        if "3 dzieci" in low:
            min_children = 3
        elif "bliźnięta" in low:
            min_children = 2

        expected_title: str | None = None
        if "umowa zlecenie" in low:
            expected_title = "zlecenie"
        elif "osoba współpracująca" in low or "osoba prowadząca działalność" in low:
            expected_title = "jdg"

        specs.append(
            SprawaExpectation(
                filename=name,
                expected_domains=domains,
                expect_denied=expect_denied,
                expected_scenario=scenario,
                expect_debt=expect_debt,
                expect_stillbirth=expect_stillbirth,
                expect_premature=expect_premature,
                expect_za_zyciem=expect_za_zyciem,
                expect_combine_work=expect_combine_work,
                expect_paternity=expect_paternity,
                expect_mother_uninsured=expect_mother_uninsured,
                expect_terminated_special=expect_terminated_special,
                min_children=min_children,
                expected_title=expected_title,
            )
        )

    return specs


def evaluate_result(spec: SprawaExpectation, res: PdfAnalysisResult) -> list[str]:
    """Zwraca listę błędów dla pojedynczej sprawy (pusta lista = TEST PASSED)."""
    errors: list[str] = []
    ef = res.extracted_fields

    if not ef.ocr_used or ef.ocr_required:
        errors.append(f"OCR failed (ocr_used={ef.ocr_used}, ocr_required={ef.ocr_required})")

    if not res.detected_forms:
        errors.append("No ZUS form detected")

    if res.document_domain not in spec.expected_domains:
        errors.append(f"domain={res.document_domain!r}, expected in {spec.expected_domains}")

    if spec.expect_denied:
        if res.verification_status != "denied":
            errors.append(f"expected status='denied', got {res.verification_status!r}")
    else:
        if res.verification_status == "denied":
            errors.append("FALSE DENIAL (verification_status='denied' on non-denied case)")

    if spec.expected_scenario is not None and ef.scenario != spec.expected_scenario:
        errors.append(f"scenario={ef.scenario!r}, expected {spec.expected_scenario!r}")

    if spec.expect_debt:
        if ef.has_contribution_debt is not True:
            errors.append(f"expected has_contribution_debt=True, got {ef.has_contribution_debt!r}")
    else:
        if ef.has_contribution_debt is True:
            errors.append("FALSE DEBT (has_contribution_debt=True on non-debt case)")

    if spec.expect_stillbirth and ef.stillbirth_or_early_death is not True:
        errors.append("missed stillbirth_or_early_death")

    if spec.expect_premature and ef.premature_or_hospitalized is not True:
        errors.append("missed premature_or_hospitalized")

    if spec.expect_za_zyciem and ef.has_za_zyciem is not True:
        errors.append("missed has_za_zyciem")

    if spec.expect_combine_work and ef.combine_parental_with_work is not True:
        errors.append("missed combine_parental_with_work")

    if spec.expect_paternity and ef.father_takes_paternity_leave is not True:
        errors.append("missed father_takes_paternity_leave")

    if spec.expect_mother_uninsured and ef.mother_uninsured_father_claim is not True:
        errors.append("missed mother_uninsured_father_claim")

    if spec.expect_terminated_special and ef.employment_terminated_special is not True:
        errors.append("missed employment_terminated_special")

    if spec.min_children is not None and (ef.children_count or 0) < spec.min_children:
        errors.append(f"children_count={ef.children_count!r}, expected >= {spec.min_children}")

    if spec.expected_title is not None and res.suggested_insurance_title != spec.expected_title:
        errors.append(f"insurance_title={res.suggested_insurance_title!r}, expected {spec.expected_title!r}")

    # Walidacja jakości kwot: nigdy nie może wyciągać 1000,00 zł ze stopki o świadczeniu rodzicielskim ani dat (np. 2025.07)
    if res.suggested_gross_salary is not None:
        if abs(res.suggested_gross_salary - 1000.0) < 0.01 and ef.extracted_amounts == [1000.0]:
            errors.append("FALSE SALARY: extracted 1000.00 zł (Kosiniakowe boilerplate)")
        if (
            len(ef.extracted_amounts) == 1
            and 2015.0 <= res.suggested_gross_salary <= 2035.12
            and round((res.suggested_gross_salary % 1) * 100) in range(1, 13)
        ):
            errors.append(f"FALSE SALARY: date-like amount {res.suggested_gross_salary}")

    return errors


def run_benchmark(cache_path: str | None = None, live_ocr: bool = False) -> tuple[int, int, list[tuple[str, list[str]]]]:
    specs = build_sprawy_expectations()
    cache: dict[str, Any] = {}
    if not live_ocr and cache_path and os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))

    passed = 0
    failures: list[tuple[str, list[str]]] = []

    for idx, spec in enumerate(specs, 1):
        neutral_name = f"case_{idx:02d}.pdf"
        if not live_ocr and spec.filename in cache:
            item = cache[spec.filename]
            res = _analyze_extracted_content(
                filename=neutral_name,
                file_kind="pdf",
                text=item["text"],
                ocr_used=bool(item.get("used", True)),
                ocr_required=len((item["text"] or "").strip()) < 20,
                page_count=int(item.get("page_count", 0)),
                ocr_pages_processed=int(item.get("ocr_pages", 0)),
            )
        else:
            raw = (SPRAWY_DIR / spec.filename).read_bytes()
            res = analyze_pdf_bytes(neutral_name, raw)

        errs = evaluate_result(spec, res)
        if not errs:
            passed += 1
        else:
            failures.append((spec.filename, errs))

    return passed, len(specs), failures


if __name__ == "__main__":
    default_cache = os.environ.get("SPRAWY_OCR_CACHE")
    live = os.environ.get("SPRAWY_LIVE_OCR") == "1"
    passed, total, failures = run_benchmark(cache_path=default_cache, live_ocr=live)
    pct = (passed / total * 100.0) if total else 0.0
    print(f"OCR Benchmark Result: {passed}/{total} PASSED ({pct:.1f}%)")
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for fn, errs in failures:
            print(f"  - {fn}")
            for e in errs:
                print(f"      * {e}")
    sys.exit(0 if pct >= 90.0 else 1)
