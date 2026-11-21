"""
Automatyczne testy dokładności lokalnego OCR (Tesseract PL) na rzeczywistych sprawach ZUS z folderu Sprawy/.

Zasady:
- Każdy plik PDF jest przekazywany do `analyze_pdf_bytes()` pod zanonimizowaną nazwą (`case_XX.pdf`),
  więc parser jest testowany wyłącznie na rzeczywistej treści odczytanej przez OCR.
- Domyślnie `pytest` uruchamia przekrojowy zestaw 12 reprezentatywnych spraw (wszystkie główne kategorie ZUS)
  z pełnym OCR na żywo i wymaga skuteczności >= 90%.
- Ustawienie `ZPPR_FULL_OCR_BENCHMARK=1` uruchamia pełny test na żywo dla wszystkich 87 plików PDF (wymagane >= 90%).
"""
from __future__ import annotations

import os
import pytest

from app.services.pdf_parser_service import analyze_pdf_bytes, is_tesseract_available
from tests.benchmark_sprawy_ocr import (
    SPRAWY_DIR,
    build_sprawy_expectations,
    evaluate_categories,
    run_benchmark,
)

STRATIFIED_SAMPLE_FILES: tuple[str, ...] = (
    "Agata Go_1_zas. mac. za okres urlopu macierzyńskiego.pdf",
    "Agnieszka Poz._zas.mac. za okres mac., uzup., rodz. - skrajny wcześniak masa poniżej 1000 - decyzja przyznająca.pdf",
    "Agnieszka Wa_05_zas. mac. łęczenie urlopu rodzicielskiego z pracą.pdf",
    "Alina Wa I_1_zas. mac. martwe urodzenie.pdf",
    "Joanna Łód_3_Zasiłek w wysokości zas. mac. i macierzyński z powodu likwidacji - przyznanie prawa.pdf",
    "Jolanta Go_5_zas. mac.-przyjęcia dziecka w wychowaniu_rodzina zastępcza.pdf",
    "Julia Gd._01_zas. macierzyński_przyjęcie dziecka na wychowanie_przysposobienie.pdf",
    "Justyna Toruńska_5_zas. macierzyński, bliźnięta, wcześniaki, zaśw. za życiem.pdf",
    "Małgorzata Rze_3_zas. macierzyński_umowa zlecenie bez chorobowego_odmowa.pdf",
    "Piotr Cho_5_zas. mac. za okres urlopu ojcowskiego, odmowa z powodu zadłużenia, osoba prowadząca działalność.pdf",
    "Piotr Rze_1_zas. macierzyński - urlop ojcowski.pdf",
    "Zuzanna Le_zas. chorobowy w ciąży.pdf",
)


@pytest.mark.skipif(not SPRAWY_DIR.exists(), reason="Brak folderu Sprawy/ w repozytorium.")
@pytest.mark.skipif(not is_tesseract_available(), reason="Brak zainstalowanego tesseract-ocr.")
def test_sprawy_stratified_live_ocr_accuracy_over_95_percent():
    """Test na żywo (prawdziwy OCR) dla 12 przekrojowych spraw ZUS — wymagane >= 95% poprawności kategorii."""
    spec_by_name = {s.filename: s for s in build_sprawy_expectations()}
    cat_passed = 0
    cat_total = 0
    failures: list[tuple[str, list[str]]] = []

    for idx, filename in enumerate(STRATIFIED_SAMPLE_FILES, 1):
        spec = spec_by_name[filename]
        raw = (SPRAWY_DIR / filename).read_bytes()
        # Zanonimizowana nazwa pliku — parser nie może korzystać z nazwy sprawy!
        res = analyze_pdf_bytes(f"case_{idx:02d}.pdf", raw)
        checks = evaluate_categories(spec, res)
        errs = [f"[{cat}] {err}" for cat, ok, err in checks if not ok]
        cat_total += len(checks)
        cat_passed += sum(1 for _, ok, _ in checks if ok)
        if errs:
            failures.append((filename, errs))

    accuracy = (cat_passed / cat_total * 100.0) if cat_total else 0.0
    assert accuracy >= 95.0, (
        f"Skuteczność kategorii OCR ({cat_passed}/{cat_total} = {accuracy:.2f}%) < 95%. "
        f"Błędy: {failures}"
    )


@pytest.mark.skipif(not SPRAWY_DIR.exists(), reason="Brak folderu Sprawy/ w repozytorium.")
@pytest.mark.skipif(not is_tesseract_available(), reason="Brak zainstalowanego tesseract-ocr.")
@pytest.mark.skipif(
    os.environ.get("ZPPR_FULL_OCR_BENCHMARK") != "1",
    reason="Pełny test 87 plików PDF na żywo uruchamiany z ZPPR_FULL_OCR_BENCHMARK=1.",
)
def test_sprawy_all_87_pdfs_live_ocr_accuracy_over_95_percent():
    """Pełny benchmark OCR na żywo dla wszystkich 87 spraw w Sprawy/ — wymagane >= 95% poprawności kategorii."""
    cat_p, cat_t, f_p, f_t, _, failures = run_benchmark(live_ocr=True)
    accuracy = (cat_p / cat_t * 100.0) if cat_t else 0.0
    assert accuracy >= 95.0, (
        f"Pełna skuteczność kategorii OCR ({cat_p}/{cat_t} = {accuracy:.2f}%, pliki {f_p}/{f_t}) < 95%. "
        f"Liczba plików z błędem: {len(failures)}; pierwsze 10: {failures[:10]}"
    )
