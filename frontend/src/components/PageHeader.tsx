interface PageHeaderProps {
  badge?: string;
  title: string;
  description: string;
}

export function PageHeader({ badge, title, description }: PageHeaderProps) {
  return (
    <div className="mb-8 border-b border-slate-200 pb-6 dark:border-emerald-950">
      {badge && (
        <span className="inline-block rounded-full bg-[#e6f4ec] px-3 py-1 text-xs font-semibold text-[#005a27] dark:bg-[#007834]/25 dark:text-emerald-300">
          {badge}
        </span>
      )}
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400 sm:text-base">
        {description}
      </p>
    </div>
  );
}
