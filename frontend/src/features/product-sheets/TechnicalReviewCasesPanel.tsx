import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, Pencil, X } from "lucide-react";
import { type FormEvent, useEffect, useId, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type {
  TechnicalReviewCase,
  TechnicalReviewResolutionAction,
} from "@/features/product-sheets/schema";
import { formatCode } from "@/features/product-sheets/productSheetUtils";
import { resolveTechnicalReviewCase } from "@/lib/api";

type TechnicalReviewCasesPanelProps = {
  productId: string;
  reviewCases: TechnicalReviewCase[];
};

type ReviewDecisionState = {
  action: TechnicalReviewResolutionAction;
  correctedValue: string;
  correctedUnit: string;
  comment: string;
};

export function TechnicalReviewCasesPanel({
  productId,
  reviewCases,
}: TechnicalReviewCasesPanelProps) {
  const [selectedCase, setSelectedCase] = useState<TechnicalReviewCase | null>(null);
  const openCases = reviewCases.filter((reviewCase) =>
    ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
  );

  if (reviewCases.length === 0) {
    return (
      <Card>
        <div className="flex items-start gap-4">
          <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
            <CheckCircle2 className="size-6" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Contrôle
            </p>
            <CardTitle className="mt-2">Aucun blocage technique</CardTitle>
            <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
              Les faits extraits ne demandent pas de décision humaine pour le moment.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-start justify-between gap-4 p-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Contrôle
            </p>
            <CardTitle className="mt-2">Points bloquants</CardTitle>
          </div>
          <Badge tone={openCases.length > 0 ? "danger" : "success"}>
            {openCases.length > 0 ? `${openCases.length} à traiter` : "Traité"}
          </Badge>
        </div>

        <div className="grid gap-3 border-t border-[var(--color-stone)] p-6">
          {reviewCases.map((reviewCase) => (
            <article
              key={reviewCase.id}
              className="rounded-[1.35rem] border border-[var(--color-stone)] bg-white p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={reviewCase.severity === "BLOCKING" ? "danger" : "warning"}>
                      {reviewCase.status === "A_TRAITER" ? "À traiter" : formatCode(reviewCase.status)}
                    </Badge>
                    <span className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
                      {reviewCase.field_name === null
                        ? "Document"
                        : formatCode(reviewCase.field_name)}
                    </span>
                  </div>
                  <h3 className="mt-3 font-serif text-xl font-semibold tracking-[-0.035em]">
                    {reviewCase.title}
                  </h3>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
                    {reviewCase.description}
                  </p>
                  {reviewCase.detected_value !== null ? (
                    <p className="mt-3 text-sm font-semibold text-[var(--color-ink)]">
                      Valeur détectée : {reviewCase.detected_value}
                      {reviewCase.detected_unit ? ` ${reviewCase.detected_unit}` : ""}
                    </p>
                  ) : null}
                </div>
                {["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status) ? (
                  <Button size="sm" variant="secondary" onClick={() => setSelectedCase(reviewCase)}>
                    <Pencil className="size-4" />
                    Décider
                  </Button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </Card>

      <ResolveReviewCaseDialog
        onOpenChange={(open) => {
          if (!open) {
            setSelectedCase(null);
          }
        }}
        open={selectedCase !== null}
        productId={productId}
        reviewCase={selectedCase}
      />
    </>
  );
}

function ResolveReviewCaseDialog({
  open,
  onOpenChange,
  productId,
  reviewCase,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
  reviewCase: TechnicalReviewCase | null;
}) {
  const titleId = useId();
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState<ReviewDecisionState>({
    action: "APPROVE_DETECTED_VALUE",
    correctedValue: "",
    correctedUnit: "",
    comment: "",
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (reviewCase === null) {
        throw new Error("Point de revue introuvable.");
      }

      return resolveTechnicalReviewCase(productId, reviewCase.id, {
        action: decision.action,
        resolvedBy: "admin",
        correctedValue:
          decision.action === "CORRECT_VALUE" ? emptyToNull(decision.correctedValue) : null,
        correctedUnit:
          decision.action === "CORRECT_VALUE" ? emptyToNull(decision.correctedUnit) : null,
        comment: emptyToNull(decision.comment),
      });
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["products"] }),
        queryClient.invalidateQueries({ queryKey: ["product-overview", productId] }),
      ]);
      onOpenChange(false);
    },
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setDecision({
      action: "APPROVE_DETECTED_VALUE",
      correctedValue: "",
      correctedUnit: "",
      comment: "",
    });
    mutation.reset();
  }, [open, reviewCase?.id]);

  if (!open || reviewCase === null) {
    return null;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.42)] px-4 py-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="w-full max-w-xl overflow-hidden rounded-[2rem] bg-[var(--color-surface-card)] shadow-[0_28px_80px_rgba(27,28,26,0.24)]">
        <div className="flex items-start justify-between gap-6 border-b border-[var(--color-stone)] px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Décision technique
            </p>
            <h2
              id={titleId}
              className="mt-2 font-serif text-2xl font-semibold tracking-[-0.04em]"
            >
              {reviewCase.title}
            </h2>
          </div>
          <button
            type="button"
            className="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--color-surface-raised)] text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]"
            aria-label="Fermer"
            onClick={() => onOpenChange(false)}
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="grid gap-5 px-6 py-6" onSubmit={submit}>
          <div className="rounded-[1.25rem] bg-[var(--color-surface-raised)]/65 p-4 text-sm leading-6 text-[var(--color-muted)]">
            <AlertTriangle className="mb-2 size-5 text-[var(--color-teak)]" />
            {reviewCase.description}
          </div>

          <label className="grid gap-2">
            <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
              Décision
            </span>
            <select
              className={inputClassName}
              onChange={(event) =>
                setDecision((current) => ({
                  ...current,
                  action: event.target.value as TechnicalReviewResolutionAction,
                }))
              }
              value={decision.action}
            >
              <option value="APPROVE_DETECTED_VALUE">Accepter la valeur détectée</option>
              <option value="CORRECT_VALUE">Corriger la valeur</option>
              <option value="REJECT_VALUE">Écarter la valeur</option>
              <option value="REQUEST_NEW_DOCUMENT">Demander un nouveau document</option>
            </select>
          </label>

          {decision.action === "CORRECT_VALUE" ? (
            <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
              <label className="grid gap-2">
                <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
                  Valeur corrigée
                </span>
                <input
                  className={inputClassName}
                  onChange={(event) =>
                    setDecision((current) => ({
                      ...current,
                      correctedValue: event.target.value,
                    }))
                  }
                  placeholder={reviewCase.suggested_value ?? reviewCase.detected_value ?? "Valeur"}
                  value={decision.correctedValue}
                />
              </label>
              <label className="grid gap-2">
                <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
                  Unité
                </span>
                <input
                  className={inputClassName}
                  onChange={(event) =>
                    setDecision((current) => ({
                      ...current,
                      correctedUnit: event.target.value,
                    }))
                  }
                  placeholder={reviewCase.suggested_unit ?? reviewCase.detected_unit ?? "cm"}
                  value={decision.correctedUnit}
                />
              </label>
            </div>
          ) : null}

          <label className="grid gap-2">
            <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
              Commentaire
            </span>
            <textarea
              className={`${inputClassName} min-h-28 py-3`}
              onChange={(event) =>
                setDecision((current) => ({
                  ...current,
                  comment: event.target.value,
                }))
              }
              placeholder="Optionnel"
              value={decision.comment}
            />
          </label>

          {mutation.error ? (
            <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/50 p-4 text-sm font-semibold text-[var(--color-error)]">
              {mutation.error.message}
            </div>
          ) : null}

          <div className="flex flex-wrap justify-end gap-3 border-t border-[var(--color-stone)] pt-5">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CheckCircle2 className="size-4" />
              )}
              Enregistrer
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

const inputClassName =
  "rounded-2xl border border-[var(--color-stone)] bg-white px-4 text-sm font-semibold text-[var(--color-ink)] outline-none transition placeholder:text-[var(--color-muted)]/55 focus:border-[var(--color-forest)] focus:ring-4 focus:ring-[var(--color-sage-soft)]";

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();

  return trimmed.length > 0 ? trimmed : null;
}
