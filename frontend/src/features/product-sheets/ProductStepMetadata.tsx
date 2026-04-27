export type ProductStepMetadataField = { label: string; value: string };

export function CompactProviderMetadata({ fields }: { fields: ProductStepMetadataField[] }) {
  if (fields.length === 0) {
    return null;
  }

  return (
    <details className="group/technical-metadata mt-2">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-1 py-1 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] transition-colors hover:text-[var(--color-forest)] [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden="true"
          className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open/technical-metadata:rotate-90"
        />
        Détails techniques
      </summary>
      <dl className="mt-1 grid gap-2 rounded-2xl bg-white/55 px-3 py-2.5 text-xs">
        {fields.map((field) => (
          <div key={field.label} className="grid gap-0.5">
            <dt className="text-[0.62rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
              {field.label}
            </dt>
            <dd
              className="break-words font-semibold leading-5 text-[var(--color-forest)]"
              title={field.value}
            >
              {field.value}
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
