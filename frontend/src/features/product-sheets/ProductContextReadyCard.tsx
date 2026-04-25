import { Lock, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { ProductOverview } from "@/features/product-sheets/schema";

type ProductContextReadyCardProps = {
  overview: ProductOverview;
};

export function ProductContextReadyCard({ overview }: ProductContextReadyCardProps) {
  const isReady = overview.product_context_snapshot !== null;

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-start justify-between gap-4 p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
            Génération
          </p>
          <CardTitle className="mt-2">
            {isReady ? "Prêt à générer" : "Contexte en préparation"}
          </CardTitle>
        </div>
        <Badge tone={isReady ? "success" : "neutral"}>
          {isReady ? "Contexte prêt" : "À venir"}
        </Badge>
      </div>

      <div className="grid grid-cols-3 gap-3 border-t border-[var(--color-stone)] p-6 max-md:grid-cols-1">
        <Metric label="Faits validés" value={String(overview.facts.length)} />
        <Metric
          label="Signaux marketing"
          value={overview.commercial_signal_snapshot === null ? "À vérifier" : "Disponibles"}
        />
        <Metric
          label="Pack de style"
          value={overview.product_context_snapshot === null ? "À assembler" : "Attaché"}
        />
      </div>

      <div className="border-t border-[var(--color-stone)] bg-[var(--color-surface-raised)]/45 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-serif text-2xl font-semibold tracking-[-0.04em]">
              Générer la fiche produit
            </p>
            <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
              Disponible à l’étape suivante.
            </p>
          </div>
          <Button disabled>
            <Sparkles className="size-4" />
            Générer la fiche produit
          </Button>
        </div>
        {!isReady ? (
          <p className="mt-4 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
            <Lock className="size-4" />
            Le contexte doit être prêt avant génération.
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] bg-white px-4 py-4">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-[var(--color-ink)]">{value}</p>
    </div>
  );
}
