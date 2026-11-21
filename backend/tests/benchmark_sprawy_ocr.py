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


def evaluate_categories(spec: SprawaExpectation, res: PdfAnalysisResult) -> list[tuple[str, bool, str]]:
    """
    Ocenia każdą właściwą kategorię dla pojedynczego pliku niezależnie.
    Zwraca listę krotek (nazwa_kategorii, czy_zdane, opis_bledu).
    """
    checks: list[tuple[str, bool, str]] = []
    ef = res.extracted_fields

    def _add(cat: str, ok: bool, err: str = "") -> None:
        checks.append((cat, ok, "" if ok else err))

    _add("ocr_ok", bool(ef.ocr_used and not ef.ocr_required), f"ocr_used={ef.ocr_used}, ocr_required={ef.ocr_required}")
    _add("forms_detected", bool(res.detected_forms), "No ZUS form detected")
    _add(
        "domain",
        res.document_domain in spec.expected_domains,
        f"domain={res.document_domain!r}, expected in {spec.expected_domains}",
    )

    if spec.expect_denied:
        _add("denial_status", res.verification_status == "denied", f"expected 'denied', got {res.verification_status!r}")
    else:
        _add("denial_status", res.verification_status != "denied", "FALSE DENIAL on non-denied case")

    if spec.expected_scenario is not None:
        _add(
            "scenario",
            ef.scenario == spec.expected_scenario,
            f"scenario={ef.scenario!r}, expected {spec.expected_scenario!r}",
        )

    if spec.expect_debt:
        _add("debt", ef.has_contribution_debt is True, f"expected debt=True, got {ef.has_contribution_debt!r}")
    else:
        _add("debt", ef.has_contribution_debt is not True, "FALSE DEBT on non-debt case")

    # Walidacja jakości kwot: nigdy 1000 zł ze stopki Kosiniakowego ani daty-jako-kwoty
    salary_ok = True
    salary_err = ""
    if res.suggested_gross_salary is not None:
        if abs(res.suggested_gross_salary - 1000.0) < 0.01 and ef.extracted_amounts == [1000.0]:
            salary_ok = False
            salary_err = "FALSE SALARY: extracted 1000.00 zł (Kosiniakowe boilerplate)"
        elif (
            len(ef.extracted_amounts) == 1
            and 2015.0 <= res.suggested_gross_salary <= 2035.12
            and round((res.suggested_gross_salary % 1) * 100) in range(1, 13)
        ):
            salary_ok = False
            salary_err = f"FALSE SALARY: date-like amount {res.suggested_gross_salary}"
    _add("salary_sanity", salary_ok, salary_err)

    # Brak fałszywego L4/kodów literowych w sprawach czysto macierzyńskich bez chorób
    if spec.expected_domains == ("maternity_parental",) and "chorobow" not in spec.filename.lower():
        _add(
            "no_false_ezla_codes",
            not ef.letter_codes,
            f"FALSE letter_codes={ef.letter_codes!r} on maternity-only case",
        )

    if spec.expect_stillbirth:
        _add("stillbirth", ef.stillbirth_or_early_death is True, "missed stillbirth_or_early_death")
    if spec.expect_premature:
        _add("premature", ef.premature_or_hospitalized is True, "missed premature_or_hospitalized")
    if spec.expect_za_zyciem:
        _add("za_zyciem", ef.has_za_zyciem is True, "missed has_za_zyciem")
    if spec.expect_combine_work:
        _add("combine_work", ef.combine_parental_with_work is True, "missed combine_parental_with_work")
    if spec.expect_paternity:
        _add("paternity", ef.father_takes_paternity_leave is True, "missed father_takes_paternity_leave")
    if spec.expect_mother_uninsured:
        _add("mother_uninsured", ef.mother_uninsured_father_claim is True, "missed mother_uninsured_father_claim")
    if spec.expect_terminated_special:
        _add("terminated_special", ef.employment_terminated_special is True, "missed employment_terminated_special")
    if spec.min_children is not None:
        _add(
            "children_count",
            (ef.children_count or 0) >= spec.min_children,
            f"children_count={ef.children_count!r}, expected >= {spec.min_children}",
        )
    if spec.expected_title is not None:
        _add(
            "insurance_title",
            res.suggested_insurance_title == spec.expected_title,
            f"insurance_title={res.suggested_insurance_title!r}, expected {spec.expected_title!r}",
        )

    return checks


def evaluate_result(spec: SprawaExpectation, res: PdfAnalysisResult) -> list[str]:
    """Zwraca listę błędów dla pojedynczej sprawy (pusta lista = wszystkie kategorie zdane)."""
    return [f"[{cat}] {err}" for cat, ok, err in evaluate_categories(spec, res) if not ok]


def run_benchmark(
    cache_path: str | None = None,
    live_ocr: bool = False,
) -> tuple[int, int, int, int, dict[str, list[int]], list[tuple[str, list[str]]]]:
    """
    Zwraca:
    (cat_passed, cat_total, files_passed, files_total, per_category_stats, file_failures)
    """
    specs = build_sprawy_expectations()
    cache: dict[str, Any] = {}
    if not live_ocr and cache_path and os.path.exists(cache_path):
        cache = json.load(open(cache_path, encoding="utf-8"))

    cat_passed = 0
    cat_total = 0
    files_passed = 0
    per_cat: dict[str, list[int]] = {}
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

        checks = evaluate_categories(spec, res)
        file_errs: list[str] = []
        for cat, ok, err in checks:
            cat_total += 1
            stat = per_cat.setdefault(cat, [0, 0])
            stat[1] += 1
            if ok:
                cat_passed += 1
                stat[0] += 1
            else:
                file_errs.append(f"[{cat}] {err}")

        if not file_errs:
            files_passed += 1
        else:
            failures.append((spec.filename, file_errs))

    return cat_passed, cat_total, files_passed, len(specs), per_cat, failures


if __name__ == "__main__":
    default_cache = os.environ.get("SPRAWY_OCR_CACHE")
    live = os.environ.get("SPRAWY_LIVE_OCR") == "1"
    cat_p, cat_t, f_p, f_t, per_cat, failures = run_benchmark(cache_path=default_cache, live_ocr=live)
    cat_pct = (cat_p / cat_t * 100.0) if cat_t else 0.0
    file_pct = (f_p / f_t * 100.0) if f_t else 0.0
    print(f"OCR Per-Category Accuracy: {cat_p}/{cat_t} PASSED ({cat_pct:.2f}%)")
    print(f"OCR Per-File (Strict All-Pass): {f_p}/{f_t} PASSED ({file_pct:.1f}%)")
    print("\nBreakdown by category:")
    for cat, (ok_n, tot_n) in sorted(per_cat.items()):
        print(f"  - {cat:22s}: {ok_n:3d}/{tot_n:3d} ({ok_n / tot_n * 100.0:5.1f}%)")
    if failures:
        print(f"\nFiles with any failed check ({len(failures)}):")
        for fn, errs in failures:
            print(f"  - {fn}")
            for e in errs:
                print(f"      * {e}")
    sys.exit(0 if cat_pct >= 95.0 else 1)
