"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CalendarClock,
  CheckCircle2,
  Coins,
  Eye,
  EyeOff,
  Lock,
  Percent,
  RotateCcw,
  Save,
  Search,
  ShieldAlert,
  SlidersHorizontal,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { LegalParameters } from "@/lib/types";

type AdminTab = "financial" | "rates" | "leaves" | "pregnancy_adoption";

interface FieldDef {
  field: keyof LegalParameters;
  label: string;
  unit: string;
  hint: string;
  isRate?: boolean;
}

const TAB_FIELDS: Record<AdminTab, FieldDef[]> = {
  financial: [
    { field: "year", label: "Rok obowiązywania", unit: "rok", hint: "Rok referencyjny dla parametrów ustawowych" },
    { field: "minimum_wage_gross", label: "Płaca minimalna brutto", unit: "zł", hint: "Podstawa wyliczenia minimum z art. 45 ustawy zasiłkowej" },
    { field: "employee_social_security_rate", label: "Składki społeczne pracownika", unit: "%", hint: "Standardowo 13,71% (0.1371) odliczane od brutto", isRate: true },
    { field: "voluntary_sickness_max_monthly_gross", label: "Limit dobrowolnego chorobowego (250%)", unit: "zł", hint: "Maksymalna miesięczna podstawa dla JDG i umów zlecenia" },
    { field: "post_employment_sickness_cap_monthly_gross", label: "Pułap podstawy po ustaniu (art. 46)", unit: "zł", hint: "100% przeciętnego wynagrodzenia po ustaniu zatrudnienia" },
    { field: "jdg_standard_min_base_gross", label: "JDG — minimalna podstawa (Duży ZUS)", unit: "zł", hint: "60% prognozowanego przeciętnego wynagrodzenia" },
    { field: "jdg_preferential_min_base_gross", label: "JDG — podstawa preferencyjna (30%)", unit: "zł", hint: "30% minimalnego wynagrodzenia dla nowych firm" },
    { field: "parental_benefit_minimum_monthly", label: "Minimalny zasiłek macierzyński", unit: "zł/mies.", hint: "Gwarantowane podwyższenie z art. 31 ust. 3a (Kosiniakowe)" },
    { field: "debt_threshold_min_wage_fraction", label: "Próg zadłużenia JDG (art. 2a)", unit: "%", hint: "Domyślnie 1% (0.01) płacy minimalnej", isRate: true },
    { field: "payer_employee_threshold", label: "Próg płatnika składek (art. 61)", unit: "osób", hint: "Powyżej tej liczby zasiłki wypłaca pracodawca" },
    { field: "funeral_grant_pln", label: "Zasiłek pogrzebowy", unit: "zł", hint: "Kwota zasiłku pogrzebowego (m.in. przy martwym urodzeniu)" },
    { field: "claim_limitation_months", label: "Przedawnienie roszczeń", unit: "mies.", hint: "Art. 67 i art. 2a ust. 2 ustawy zasiłkowej" },
  ],
  rates: [
    { field: "sickness_benefit_pregnancy_rate", label: "Chorobowy w ciąży (kod B)", unit: "%", hint: "Art. 11 ust. 2 pkt 1 — standardowo 100%", isRate: true },
    { field: "sickness_benefit_standard_rate", label: "Chorobowy standardowy", unit: "%", hint: "Art. 11 ust. 1 — standardowo 80%", isRate: true },
    { field: "maternity_rate_standard", label: "Urlop macierzyński (standard)", unit: "%", hint: "Wariant 100% + 70%", isRate: true },
    { field: "parental_rate_standard", label: "Urlop rodzicielski (standard)", unit: "%", hint: "Wariant 100% + 70%", isRate: true },
    { field: "combined_21_days_rate", label: "Wariant łączony (wniosek w 21 dni)", unit: "%", hint: "Art. 30a — równa stawka za cały okres (81,5%)", isRate: true },
    { field: "non_transferable_parental_rate", label: "Część nieprzenoszalna (9 tyg.)", unit: "%", hint: "Art. 31 ust. 3f — zawsze 70% dla drugiego rodzica", isRate: true },
    { field: "paternity_rate", label: "Urlop ojcowski", unit: "%", hint: "100% podstawy wymiaru", isRate: true },
    { field: "supplementary_maternity_rate", label: "Uzupełniający urlop macierzyński", unit: "%", hint: "Wcześniaki / hospitalizacja — 100%", isRate: true },
    { field: "rehabilitation_benefit_pregnancy_rate", label: "Świadczenie rehabilitacyjne w ciąży", unit: "%", hint: "100% podstawy wymiaru w okresie ciąży", isRate: true },
  ],
  leaves: [
    { field: "parental_weeks_single", label: "Urlop rodzicielski — 1 dziecko", unit: "tyg.", hint: "Łączna pula dla obojga rodziców" },
    { field: "parental_weeks_multiple", label: "Urlop rodzicielski — 2+ dzieci", unit: "tyg.", hint: "Łączna pula przy porodzie mnogim" },
    { field: "parental_weeks_za_zyciem_single", label: "„Za życiem” — 1 dziecko", unit: "tyg.", hint: "Wydłużony urlop rodzicielski" },
    { field: "parental_weeks_za_zyciem_multiple", label: "„Za życiem” — 2+ dzieci", unit: "tyg.", hint: "Wydłużony urlop przy porodzie mnogim" },
    { field: "parental_non_transferable_weeks", label: "Część nieprzenoszalna rodzica", unit: "tyg.", hint: "Art. 182¹ᵃ § 4 KP — wyłączne prawo każdego rodzica" },
    { field: "parental_max_parts", label: "Maks. liczba części rodzicielskiego", unit: "części", hint: "Do wykorzystania do końca roku ukończenia 6 lat" },
    { field: "parental_work_max_fte", label: "Maks. etat przy łączeniu z pracą", unit: "etatu", hint: "Art. 182¹ᵉ KP — maks. 0.5 (pół etatu)" },
    { field: "paternity_weeks", label: "Urlop ojcowski", unit: "tyg.", hint: "Do 12. miesiąca życia dziecka (lub adopcji)" },
    { field: "combined_application_deadline_days", label: "Termin na wniosek o 81,5%", unit: "dni", hint: "Liczony od dnia porodu / przyjęcia dziecka" },
    { field: "maternity_min_mother_weeks", label: "Obowiązkowy urlop matki po porodzie", unit: "tyg.", hint: "Minimalny wymiar przed przekazaniem ojcu" },
    { field: "maternity_pre_birth_max_weeks", label: "Maks. macierzyński przed porodem", unit: "tyg.", hint: "Art. 180 § 2 KP — do 6 tygodni przed datą porodu" },
    { field: "supplementary_maternity_max_weeks_extreme", label: "Uzupełniający (<28 tyg. / ≤1000 g)", unit: "tyg.", hint: "Maksymalny limit hospitalizacji skrajnego wcześniaka" },
    { field: "supplementary_maternity_max_weeks_standard", label: "Uzupełniający (standard)", unit: "tyg.", hint: "Maksymalny limit dla pozostałych przypadków" },
  ],
  pregnancy_adoption: [
    { field: "sickness_benefit_pregnancy_max_days", label: "Okres zasiłkowy w ciąży", unit: "dni", hint: "Art. 8 ustawy zasiłkowej — maksymalnie 270 dni" },
    { field: "waiting_period_mandatory_days", label: "Wyczekiwanie (obowiązkowe)", unit: "dni", hint: "Umowa o pracę — 30 dni" },
    { field: "waiting_period_voluntary_days", label: "Wyczekiwanie (dobrowolne)", unit: "dni", hint: "JDG i umowa zlecenie — 90 dni" },
    { field: "sickness_pay_employer_days_under_50", label: "Wynagr. chorobowe (<50 lat)", unit: "dni", hint: "Płacone przez pracodawcę w roku kalendarzowym" },
    { field: "sickness_pay_employer_days_over_50", label: "Wynagr. chorobowe (50+ lat)", unit: "dni", hint: "Płacone przez pracodawcę po 50. roku życia" },
    { field: "rehabilitation_benefit_max_days", label: "Świadczenie rehabilitacyjne", unit: "dni", hint: "Maksymalnie 12 miesięcy (360 dni)" },
    { field: "stillbirth_maternity_weeks", label: "Urodzenie martwego dziecka", unit: "tyg.", hint: "Art. 180¹ § 1 KP — 8 tygodni po porodzie" },
    { field: "child_death_min_days", label: "Min. zasiłek po zgonie dziecka", unit: "dni", hint: "Nie krócej niż 7 dni od dnia zgonu" },
    { field: "foster_max_child_age", label: "Limit wieku: rodzina zastępcza", unit: "lat", hint: "Standardowo do 7. roku życia" },
    { field: "foster_deferred_school_max_child_age", label: "Limit wieku: odroczenie szkoły", unit: "lat", hint: "Przy decyzji o odroczeniu obowiązku szkolnego" },
    { field: "adoption_max_child_age", label: "Limit wieku: przysposobienie", unit: "lat", hint: "Do 14. roku życia dziecka" },
    { field: "adoption_foster_min_maternity_weeks", label: "Min. urlop przy granicy wieku", unit: "tyg.", hint: "Gwarancja 9 tygodni z art. 183 § 3 KP" },
    { field: "adoption_foster_reduced_parental_weeks", label: "Rodzicielski przy granicy wieku", unit: "tyg.", hint: "38 tygodni z art. 183 § 4 pkt 3 KP" },
    { field: "adoption_foster_reduced_parental_weeks_za_zyciem", label: "Rodzicielski „Za życiem” (granica)", unit: "tyg.", hint: "62 tygodnie przy zaświadczeniu „Za życiem”" },
  ],
};

const TABS: { id: AdminTab; label: string; icon: typeof Coins }[] = [
  { id: "financial", label: "Podstawy i progi", icon: Coins },
  { id: "rates", label: "Stawki procentowe", icon: Percent },
  { id: "leaves", label: "Urlopy i wymiary", icon: CalendarClock },
  { id: "pregnancy_adoption", label: "Ciąża i adopcja", icon: SlidersHorizontal },
];

export default function AdminPanelPage() {
  const [params, setParams] = useState<LegalParameters | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState<string>("");
  const [activeTab, setActiveTab] = useState<AdminTab>("financial");
  const [search, setSearch] = useState("");
  const [adminKey, setAdminKey] = useState("zppr-admin-2026");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getParameters()
      .then((data) => {
        setParams(data);
        setSavedSnapshot(JSON.stringify(data));
      })
      .catch((e) => setError(String(e)));
  }, []);

  const isDirty = useMemo(
    () => Boolean(params && savedSnapshot && JSON.stringify(params) !== savedSnapshot),
    [params, savedSnapshot]
  );

  const visibleFields = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return TAB_FIELDS[activeTab];
    return Object.values(TAB_FIELDS)
      .flat()
      .filter((f) => f.label.toLowerCase().includes(q) || f.hint.toLowerCase().includes(q));
  }, [activeTab, search]);

  const handleSave = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!params) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.updateParameters(params, adminKey);
      setParams(updated);
      setSavedSnapshot(JSON.stringify(updated));
      setMessage("Zapisano parametry prawne. Wszystkie kalkulatory korzystają już z nowych wartości.");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Błąd autoryzacji lub zapisu (sprawdź klucz dostępu)"
      );
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const reset = await api.resetParameters(adminKey);
      setParams(reset);
      setSavedSnapshot(JSON.stringify(reset));
      setMessage("Przywrócono ustawowe wartości domyślne dla roku 2026.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd resetu (sprawdź klucz dostępu)");
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    if (!savedSnapshot) return;
    setParams(JSON.parse(savedSnapshot) as LegalParameters);
    setMessage(null);
    setError(null);
  };

  const updateNum = (field: keyof LegalParameters, value: string) => {
    if (!params) return;
    setParams({ ...params, [field]: Number(value) });
  };

  const updateMaternityByChildren = (childKey: string, value: string) => {
    if (!params) return;
    setParams({
      ...params,
      maternity_weeks_by_children: {
        ...params.maternity_weeks_by_children,
        [childKey]: Number(value),
      },
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        badge="Panel Administracyjny"
        title="Zarządzanie parametrami prawnymi"
        description="Centralny rejestr stawek, progów finansowych i wymiarów urlopów. Zmiany wchodzą w życie natychmiast we wszystkich kalkulatorach i są utrwalane w wolumenie danych."
      />

      {!params ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500 dark:border-emerald-950 dark:bg-[#111c17]">
          Ładowanie konfiguracji z serwera...
        </div>
      ) : (
        <>
          {/* KPI Summary Strip */}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Rok prawny
              </p>
              <p className="mt-1 text-2xl font-extrabold text-slate-900 dark:text-white">
                {params.year}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Płaca minimalna brutto
              </p>
              <p className="mt-1 text-2xl font-extrabold text-[#007834] dark:text-emerald-400">
                {params.minimum_wage_gross.toLocaleString("pl-PL")} zł
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Wariant łączony (21 dni)
              </p>
              <p className="mt-1 text-2xl font-extrabold text-slate-900 dark:text-white">
                {(params.combined_21_days_rate * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Status konfiguracji
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-sm font-bold">
                {isDirty ? (
                  <span className="inline-flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                    <ShieldAlert className="h-4 w-4" />
                    Niezapisane zmiany
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-[#007834] dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    Zsynchronizowano
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Auth & Search Toolbar */}
          <div className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs dark:border-emerald-950 dark:bg-[#111c17] lg:grid-cols-12">
            <div className="lg:col-span-5">
              <label className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                <Lock className="h-3.5 w-3.5 text-[#007834] dark:text-emerald-400" />
                Klucz autoryzacji administratora
              </label>
              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  value={adminKey}
                  onChange={(e) => setAdminKey(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 py-2 pr-10 pl-3 text-sm dark:border-slate-700"
                  placeholder="Wpisz klucz administratora"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute top-1/2 right-2.5 -translate-y-1/2 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  aria-label="Pokaż lub ukryj klucz"
                >
                  {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="lg:col-span-4">
              <label className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                <Search className="h-3.5 w-3.5 text-slate-400" />
                Szybkie wyszukiwanie parametru
              </label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="np. płaca minimalna, 21 dni, adopcja..."
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-700"
              />
            </div>

            <div className="flex items-end justify-end gap-2 lg:col-span-3">
              <button
                type="button"
                disabled={saving}
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-[#111c17] dark:text-slate-300 dark:hover:bg-[#1e3328]"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Domyślne 2026
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={() => handleSave()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#007834] px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-[#005a27] disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                {saving ? "Zapis..." : "Zapisz"}
              </button>
            </div>
          </div>

          {message && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs font-medium text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-200">
              {message}
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs font-medium text-red-800 dark:border-red-800/60 dark:bg-red-950/40 dark:text-red-200">
              {error}
            </div>
          )}

          {/* Category Tabs */}
          {!search.trim() && (
            <div className="flex flex-wrap gap-2">
              {TABS.map((t) => {
                const Icon = t.icon;
                const active = activeTab === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setActiveTab(t.id)}
                    className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-semibold transition ${
                      active
                        ? "border-[#007834] bg-[#007834] text-white shadow-xs"
                        : "border-slate-200 bg-white text-slate-700 hover:border-[#007834]/50 hover:bg-slate-50 dark:border-emerald-950 dark:bg-[#111c17] dark:text-slate-300 dark:hover:border-emerald-700 dark:hover:bg-[#1e3328]"
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {t.label}
                  </button>
                );
              })}
            </div>
          )}

          {/* Parameters Grid */}
          <form onSubmit={handleSave} className="space-y-6">
            {activeTab === "leaves" && !search.trim() && (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs dark:border-emerald-950 dark:bg-[#111c17]">
                <h2 className="text-sm font-bold text-slate-900 dark:text-white">
                  Wymiar urlopu macierzyńskiego według liczby dzieci (tygodnie)
                </h2>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  Art. 180 § 1 Kodeksu pracy — wymiar przy urodzeniu lub jednoczesnym przyjęciu dzieci.
                </p>
                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {["1", "2", "3", "4", "5"].map((k) => (
                    <div
                      key={k}
                      className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 dark:border-emerald-950 dark:bg-[#16241d]"
                    >
                      <label className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                        {k === "5" ? "5+ dzieci" : `${k} ${k === "1" ? "dziecko" : "dzieci"}`}
                      </label>
                      <div className="mt-2 flex items-center gap-1.5">
                        <input
                          type="number"
                          min={1}
                          step="any"
                          value={params.maternity_weeks_by_children[k] ?? 20}
                          onChange={(e) => updateMaternityByChildren(k, e.target.value)}
                          className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm font-bold dark:border-slate-700 dark:bg-[#0e1914]"
                        />
                        <span className="text-xs text-slate-500 dark:text-slate-400">tyg.</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {visibleFields.map((item) => {
                const rawVal = Number(params[item.field] ?? 0);
                return (
                  <div
                    key={String(item.field)}
                    className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-[#007834]/40 dark:border-emerald-950 dark:bg-[#111c17]"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <label className="text-xs font-bold text-slate-900 dark:text-slate-100">
                          {item.label}
                        </label>
                        {item.isRate ? (
                          <span className="shrink-0 rounded-full bg-[#e6f4ec] px-2 py-0.5 font-mono text-[11px] font-bold text-[#005a27] dark:bg-[#007834]/25 dark:text-emerald-300">
                            {(rawVal * 100).toFixed(2).replace(/\.00$/, "")}%
                          </span>
                        ) : (
                          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                            {item.unit}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-[11px] leading-snug text-slate-500 dark:text-slate-400">
                        {item.hint}
                      </p>
                    </div>
                    <input
                      type="number"
                      step="any"
                      value={rawVal}
                      onChange={(e) => updateNum(item.field, e.target.value)}
                      className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-700"
                    />
                  </div>
                );
              })}
            </div>

            {isDirty && (
              <div className="sticky bottom-4 z-30 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#007834]/40 bg-white/95 px-5 py-3.5 shadow-lg backdrop-blur dark:border-emerald-700/60 dark:bg-[#0f1914]/95">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Wykryto niezapisane zmiany w parametrach prawnych.
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleDiscard}
                    className="rounded-lg border border-slate-300 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-[#1e3328]"
                  >
                    Odrzuć zmiany
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-[#007834] px-4 py-2 text-xs font-semibold text-white hover:bg-[#005a27] disabled:opacity-50"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {saving ? "Zapisywanie..." : "Zapisz konfigurację"}
                  </button>
                </div>
              </div>
            )}
          </form>
        </>
      )}
    </div>
  );
}
