from app.models.guidance import OfficialLink, RiskItem, SupportOrganization


def get_risks() -> list[RiskItem]:
    return [
        RiskItem(
            id="pozornosc_umowy",
            title="Zawarcie umowy lub założenie działalności gospodarczej dla pozoru",
            severity="high",
            description=(
                "Zgłoszenie się do ubezpieczenia chorobowego wyłącznie w celu uzyskania zasiłków (bez faktycznego "
                "świadczenia pracy lub prowadzenia działalności) może skutkować kontrolą ZUS i decyzją o niepodleganiu ubezpieczeniom."
            ),
            how_to_avoid="Dokumentuj realne wykonywanie pracy lub prowadzenie działalności (umowy, faktury, efekty pracy, korespondencja).",
            applies_to=["Umowa o pracę", "Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="zawyzenie_podstawy",
            title="Sztuczne podwyższenie podstawy wymiaru składek w ciąży",
            severity="high",
            description=(
                "Nagłe, nieuzasadnione podniesienie wynagrodzenia lub deklarowanej podstawy składek w okresie ciąży "
                "może zostać zakwestionowane przez ZUS, który w drodze decyzji ustali niższą podstawę zasiłku."
            ),
            how_to_avoid="Zmiany wynagrodzenia powinny wynikać z realnego zwiększenia zakresu obowiązków, awansu lub siatki płac w firmie.",
            applies_to=["Umowa o pracę", "JDG"],
        ),
        RiskItem(
            id="brak_ubezpieczenia_porod",
            title="Niepodleganie ubezpieczeniu chorobowemu w dniu porodu",
            severity="high",
            description=(
                "Nieprzystąpienie do dobrowolnego ubezpieczenia chorobowego (zlecenie/JDG) albo zakończenie umowy / "
                "zamknięcie działalności przed porodem pozbawia prawa do zasiłku macierzyńskiego z ZUS."
            ),
            how_to_avoid="Sprawdź status ubezpieczenia chorobowego na PUE/eZUS oraz nie wyrejestrowuj się przed dniem porodu.",
            applies_to=["Umowa zlecenie", "JDG", "Umowa o pracę na czas określony"],
        ),
        RiskItem(
            id="zadluzenie_jdg",
            title="Zadłużenie z tytułu składek ZUS (dla prowadzących działalność)",
            severity="high",
            description=(
                "Zadłużenie z tytułu składek przekraczające 1% minimalnego wynagrodzenia powoduje wstrzymanie wypłaty zasiłku "
                "do czasu uregulowania zaległości (a po 6 miesiącach utratę prawa do świadczenia)."
            ),
            how_to_avoid="Regularnie sprawdzaj saldo składek na PUE/eZUS przed powstaniem prawa do zasiłku.",
            applies_to=["JDG"],
        ),
        RiskItem(
            id="termin_21_dni",
            title="Przekroczenie terminu 21 dni na wniosek o zasiłek 81,5%",
            severity="medium",
            description=(
                "Złożenie wniosku o pełny wymiar urlopu macierzyńskiego i rodzicielskiego po upływie 21 dni od porodu "
                "skutkuje rozliczeniem w wariancie 100% (macierzyński) + 70% (rodzicielski) bez możliwości wyboru równej stawki 81,5%."
            ),
            how_to_avoid="Ustaw przypomnienie zaraz po narodzinach dziecka i złóż wniosek u pracodawcy lub w ZUS (ZAM) w ciągu 21 dni.",
            applies_to=["Umowa o pracę", "Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="ochrona_kp_vs_brak",
            title="Brak ochrony z Kodeksu pracy dla zleceniobiorców i JDG",
            severity="info",
            description=(
                "Szczególna ochrona przed wypowiedzeniem w ciąży i automatyczne przedłużenie umowy na czas określony "
                "do dnia porodu (po 3. miesiącu ciąży) przysługują wyłącznie pracownikom na umowie o pracę."
            ),
            how_to_avoid="Jeśli pracujesz na zleceniu lub JDG, zadbaj o ciągłość dobrowolnego ubezpieczenia chorobowego.",
            applies_to=["Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="wykorzystywanie_ezla_art17",
            title="Praca zarobkowa lub aktywność niezgodna z celem zwolnienia e-ZLA (art. 17)",
            severity="high",
            description=(
                "Wykonywanie pracy zarobkowej w okresie orzeczonej niezdolności do pracy albo podejmowanie aktywności "
                "utrudniającej lub wydłużającej proces leczenia (niezgodnej z celem zwolnienia) skutkuje utratą prawa "
                "do zasiłku chorobowego za cały okres tego zwolnienia. Zgodnie z art. 17 ust. 1a–1b ustawy zasiłkowej "
                "(2026 r.) wyłączone są jednak zwykłe czynności dnia codziennego (np. zakupy, spacer, wizyta w przychodni) "
                "oraz czynności incydentalne, których podjęcia wymagają istotne okoliczności (np. podpisanie pilnej faktury "
                "lub odpowiedź na maila — istotną okolicznością nie może być polecenie pracodawcy)."
            ),
            how_to_avoid="Podczas e-ZLA powstrzymaj się od regularnej pracy zarobkowej i przestrzegaj zaleceń lekarskich; dopuszczalne są wyłącznie zwykłe czynności codzienne oraz niezbędne czynności incydentalne niebędące poleceniem pracodawcy.",
            applies_to=["Umowa o pracę", "Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="zmiana_etatu_lub_pracodawcy_art40",
            title="Zmiana wymiaru czasu pracy lub pracodawcy w trakcie ciąży (art. 40)",
            severity="high",
            description=(
                "Zmiana wymiaru etatu w okresie, z którego ustalana jest podstawa zasiłku (np. zmniejszenie etatu w ciąży), "
                "powoduje wyliczenie podstawy wyłącznie z wynagrodzenia ustalonego dla nowego wymiaru czasu pracy. "
                "Z kolei zmiana pracodawcy w ciąży wiąże się z nową podstawą wymiaru i koniecznością zachowania ciągłości ubezpieczenia (przerwa ≤ 30 dni)."
            ),
            how_to_avoid="Przed zmianą etatu lub pracodawcy w ciąży przelicz wpływ na podstawę wymiaru zasiłku i upewnij się, że nie powstanie przerwa w ubezpieczeniu dłuższa niż 30 dni.",
            applies_to=["Umowa o pracę"],
        ),
        RiskItem(
            id="wyrejestrowanie_dobrowolne_zua",
            title="Automatyczne wyrejestrowanie z dobrowolnego chorobowego po rozpoczęciu macierzyńskiego",
            severity="medium",
            description=(
                "Rozpoczęcie pobierania zasiłku macierzyńskiego przez osobę na JDG lub umowie zleceniu powoduje ustanie "
                "dobrowolnego ubezpieczenia chorobowego. Brak ponownego zgłoszenia po zakończeniu zasiłku oznacza brak ochrony przy kolejnym L4."
            ),
            how_to_avoid="Po zakończeniu pobierania zasiłku macierzyńskiego złóż ponownie zgłoszenie ZUS ZUA do dobrowolnego ubezpieczenia chorobowego w terminie 7 dni (aby zachować ciągłość bez ponownego 90-dniowego wyczekiwania).",
            applies_to=["Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="przedawnienie_i_ojcowski",
            title="Przedawnienie roszczenia o zasiłek po 6 miesiącach (art. 67) i wygasanie urlopu ojcowskiego",
            severity="medium",
            description=(
                "Roszczenie o wypłatę zasiłku przedawnia się po 6 miesiącach od ostatniego dnia okresu, za który przysługuje "
                "(także gdy wypłata była wstrzymana z powodu zadłużenia JDG z art. 2a). Urlop ojcowski (2 tyg.) przepada, "
                "jeśli nie zostanie wykorzystany do ukończenia przez dziecko 12 miesięcy życia (lub 12 mies. od uprawomocnienia adopcji, maks. do 14 r.ż.)."
            ),
            how_to_avoid="Składaj wnioski niezwłocznie, spłać ewentualne zadłużenie JDG w ciągu 6 miesięcy oraz zaplanuj urlop ojcowski przed 1. urodzinami dziecka.",
            applies_to=["Umowa o pracę", "Umowa zlecenie", "JDG"],
        ),
        RiskItem(
            id="ochrona_trwalosci_art177_kp",
            title="Szczególna ochrona trwałości stosunku pracy — art. 177 Kodeksu pracy",
            severity="info",
            description=(
                "W okresie ciąży, urlopów rodzicielskich oraz od dnia złożenia wniosku o urlop (najwcześniej 14 dni przed "
                "częścią macierzyńskiego, 21 dni przed uzupełniającym/rodzicielskim, 7 dni przed ojcowskim) pracodawca nie "
                "może prowadzić nawet przygotowań do wypowiedzenia umowy ani jej rozwiązać (poza upadłością/likwidacją lub dyscyplinarką za zgodą związków). "
                "Uwaga na wyjątki: automatyczne przedłużenie do dnia porodu (art. 177 § 3 KP) nie dotyczy umowy na zastępstwo ani umowy na okres próbny ≤ 1 miesiąca."
            ),
            how_to_avoid="Złóż wniosek o urlop w ustawowych terminach (14/21/7 dni) i sprawdź rodzaj swojej umowy na czas określony; w razie naruszenia przysługuje odwołanie do sądu pracy i ochrona zasiłkowa z art. 30 ustawy zasiłkowej.",
            applies_to=["Umowa o pracę"],
        ),
    ]


def get_support_organizations() -> list[SupportOrganization]:
    return [
        SupportOrganization(
            name="Fundacja Wcześniak Rodzice-Rodzicom",
            category="wcześniaki",
            description="Wsparcie merytoryczne, psychologiczne i edukacyjne dla rodziców dzieci urodzonych przedwcześnie.",
            website="https://wczesniak.pl",
            charitable_only=True,
        ),
        SupportOrganization(
            name="Fundacja Koalicja dla Wcześniaka",
            category="wcześniaki",
            description="Działania na rzecz wcześniaków i ich rodzin, informatory medyczne i prawne (m.in. uzupełniający urlop macierzyński).",
            website="https://koalicjadlawczesniaka.pl",
            charitable_only=True,
        ),
        SupportOrganization(
            name="Fundacja Ernesta",
            category="strata_dziecka",
            description="Bezpłatna pomoc psychologiczna i prawna dla rodzin po stracie dziecka (poronienie, urodzenie martwego dziecka).",
            website="https://fundacjaernesta.pl",
            charitable_only=True,
        ),
        SupportOrganization(
            name="Fundacja Nagle Sami (OPP, KRS 0000398530)",
            category="strata_dziecka",
            description="Bezpłatne wsparcie psychologiczne i grupy wsparcia dla rodziców i rodzin w żałobie (w tym po poronieniu i stracie dziecka) oraz bezpłatny Telefon Wsparcia 800 108 108.",
            website="https://naglesami.org.pl",
            helpline="800 108 108",
            charitable_only=True,
        ),
        SupportOrganization(
            name="Fundacja Gajusz (Hospicjum Perinatalne)",
            category="dziecko_chore",
            description="Opieka perinatalna, wsparcie psychologiczne i socjalne dla rodziców dzieci ciężko i nieuleczalnie chorych.",
            website="https://gajusz.org.pl",
            charitable_only=True,
        ),
        SupportOrganization(
            name="Fundacja Rodzić po Ludzku",
            category="wsparcie_rodziny",
            description="Wsparcie kobiet w ciąży i okresie okołoporodowym, informacja o prawach pacjentki i matki.",
            website="https://rodzicpoludzku.pl",
            charitable_only=True,
        ),
    ]


def get_official_links() -> list[OfficialLink]:
    return [
        OfficialLink(
            institution="ZUS",
            title="Zakład Ubezpieczeń Społecznych — Zasiłki i formularze",
            url="https://www.zus.pl",
            description="Oficjalny portal ZUS, wzory formularzy (ZAM, Z-3, Z-3a, ZAS-53) oraz PUE/eZUS.",
        ),
        OfficialLink(
            institution="MRPiPS",
            title="Ministerstwo Rodziny, Pracy i Polityki Społecznej — Urlop rodzicielski",
            url="https://www.gov.pl/web/rodzina/urlop-rodzicielski",
            description="Informacje rządowe o uprawnieniach pracowniczych i urlopach związanych z rodzicielstwem.",
        ),
        OfficialLink(
            institution="PIP",
            title="Państwowa Inspekcja Pracy — Porady prawne: Rodzicielstwo",
            url="https://www.pip.gov.pl/dla-pracodawcow/porady-prawne/rodzicielstwo",
            description="Szczegółowe wyjaśnienia Kodeksu pracy, ochrony kobiet w ciąży i łączenia urlopu z pracą.",
        ),
        OfficialLink(
            institution="gov.pl / USC",
            title="Rejestr Stanu Cywilnego — Odpis aktu urodzenia",
            url="https://www.gov.pl/web/cyfryzacja/rejestr-stanu-cywilnego",
            description="Informacje o rejestracji dziecka i uzyskaniu odpisu skróconego lub zupełnego aktu stanu cywilnego.",
        ),
    ]
