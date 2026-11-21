interface PageHeaderProps {
  badge?: string;
  title: string;
  description: string;
}

export function PageHeader({ badge, title, description }: PageHeaderProps) {
  return (
    <div className="mb-8 border-b border-slate-200/90 pb-6 dark:border-emerald-950/90">
      {badge && (
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#007834]/20 bg-[#e6f4ec] px-3 py-1 text-xs font-semibold tracking-wide text-[#005a27] dark:border-emerald-800/50 dark:bg-[#007834]/20 dark:text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-[#007834] dark:bg-emerald-400" />
          {badge}
        </span>
      )}
      <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
        {description}
      </p>
    </div>
  );
}
