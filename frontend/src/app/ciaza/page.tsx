"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LegacyPregnancyRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/kalkulator?mode=pregnancy");
  }, [router]);

  return (
    <div className="py-16 text-center text-sm text-slate-500 dark:text-slate-400">
      Przekierowywanie do zintegrowanego kalkulatora (zakładka Ciąża)...
    </div>
  );
}
