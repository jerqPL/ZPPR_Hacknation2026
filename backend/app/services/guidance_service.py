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
            name="Fundacja Poronienie / Stowarzyszenie Rodziców po Poronieniu",
            category="strata_dziecka",
            description="Grupy wsparcia oraz rzetelne przewodniki dotyczące praw rodziców po stracie dziecka (w tym 8 tyg. urlopu macierzyńskiego).",
            website="https://poronilam.pl",
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
