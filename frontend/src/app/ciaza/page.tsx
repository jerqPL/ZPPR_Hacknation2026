"use client";

import { PageHeader } from "@/components/PageHeader";
import { PregnancyCalculatorPanel } from "@/components/PregnancyCalculatorPanel";

export default function PregnancyPage() {
  return (
    <div>
      <PageHeader
        badge="Okres ciąży"
        title="Świadczenia w czasie ciąży"
        description="Sprawdź uprawnienia do zasiłku chorobowego (kod literowy B = 100% do 270 dni), świadczenia rehabilitacyjnego (100% do 12 miesięcy) oraz świadczeń po ustaniu zatrudnienia w ciąży (art. 7, art. 30 i art. 46 ustawy zasiłkowej)."
      />
      <PregnancyCalculatorPanel />
    </div>
  );
}
