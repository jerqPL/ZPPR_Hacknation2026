interface PageHeaderProps {
  badge?: string;
  title: string;
  description: string;
}

export function PageHeader({ badge, title, description }: PageHeaderProps) {
  return (
    <div className="mb-8 border-b border-[#CCC5B9] pb-6">
      {badge && (
        <span className="inline-block rounded-full border border-[#CCC5B9] bg-[#F5F1E6] px-3 py-1 text-xs font-semibold tracking-wide text-[#000000]">
          {badge}
        </span>
      )}
      <h1 className="mt-3 text-2xl font-bold tracking-tight text-[#000000] sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#403D39] sm:text-base">
        {description}
      </p>
    </div>
  );
}
