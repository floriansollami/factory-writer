import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2, Pencil, X } from "lucide-react";
import { type FormEvent, useEffect, useId, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { technicalFactLabelDescription } from "@/features/product-sheets/TechnicalExtractionResultsDisclosure";
import type {
  TechnicalReviewCase,
  TechnicalReviewResolutionAction,
} from "@/features/product-sheets/schema";
import {
  formatCode,
  technicalDocumentTypeLabel,
} from "@/features/product-sheets/productSheetUtils";
import { resolveTechnicalReviewCase } from "@/lib/api";
import { cn } from "@/lib/utils";

const DOCUMENT_TYPE_OPTIONS = [
  "TECHNICAL_SHEET",
  "MATERIAL_SPECIFICATION",
  "ASSEMBLY_NOTICE",
  "UNKNOWN",
];

type TechnicalReviewCasesPanelProps = {
  productId: string;
  reviewCases: TechnicalReviewCase[];
};

type ReviewDecisionState = {
  action: TechnicalReviewResolutionAction;
  correctedValue: string;
  correctedUnit: string;
  selectedCandidateId: string;
  comment: string;
};

type ReviewCandidateOption = {
  id: string;
  normalizedValue: string | null;
  reason: string | null;
  scoreLabel: string;
  sourceLabel: string;
  value: string;
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
                      {isClassificationReviewCase(reviewCase)
                        ? "Classification"
                        : reviewCase.field_name === null
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
                      {isClassificationReviewCase(reviewCase)
                        ? "Type détecté"
                        : "Valeur détectée"}{" "}
                      :{" "}
                      {isClassificationReviewCase(reviewCase)
                        ? technicalDocumentTypeLabel(reviewCase.detected_value)
                        : formatCode(reviewCase.detected_value)}
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

      <ResolveTechnicalReviewCaseDialog
        onOpenChange={(open) => {
          if (!open) {
            setSelectedCase(null);
          }
        }}
        open={selectedCase !== null}
        productId={productId}
        relatedReviewCases={relatedReviewCases(selectedCase, reviewCases)}
        reviewCase={selectedCase}
      />
    </>
  );
}

export function ResolveTechnicalReviewCaseDialog({
  open,
  onOpenChange,
  productId,
  relatedReviewCases = [],
  reviewCase,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
  relatedReviewCases?: TechnicalReviewCase[];
  reviewCase: TechnicalReviewCase | null;
}) {
  const titleId = useId();
  const queryClient = useQueryClient();
  const relatedReviewCaseKey = relatedReviewCases.map((item) => item.id).join("|");
  const isClassificationCase =
    reviewCase !== null && isClassificationReviewCase(reviewCase);
  const canApproveDetectedClassification =
    isClassificationCase && isRoutableDocumentType(reviewCase.detected_value);
  const [decision, setDecision] = useState<ReviewDecisionState>({
    action: "APPROVE_DETECTED_VALUE",
    correctedValue: "",
    correctedUnit: "",
    selectedCandidateId: "",
    comment: "",
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (reviewCase === null) {
        throw new Error("Point de revue introuvable.");
      }

      const targetCases = resolutionTargetCases(reviewCase, relatedReviewCases);
      let lastResult = null;

      for (const targetCase of targetCases) {
        lastResult = await resolveTechnicalReviewCase(productId, targetCase.id, {
          action: decision.action,
          resolvedBy: "admin",
          correctedValue:
            decision.action === "CORRECT_VALUE" ? emptyToNull(decision.correctedValue) : null,
          correctedUnit:
            decision.action === "CORRECT_VALUE" && !isClassificationReviewCase(reviewCase)
              ? emptyToNull(decision.correctedUnit)
              : null,
          selectedCandidateId:
            decision.action === "APPROVE_DETECTED_VALUE"
              ? emptyToNull(decision.selectedCandidateId)
              : null,
          comment: emptyToNull(decision.comment),
        });
      }

      return lastResult;
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

    const targetCases =
      reviewCase === null ? [] : resolutionTargetCases(reviewCase, relatedReviewCases);
    setDecision({
      action:
        isClassificationReviewCase(reviewCase) &&
        !isRoutableDocumentType(reviewCase?.detected_value)
            ? "REQUEST_NEW_DOCUMENT"
          : !isClassificationReviewCase(reviewCase) &&
              firstReviewCandidateIdForCases(targetCases) === "" &&
              reviewCase?.detected_value === null
            ? "CORRECT_VALUE"
          : "APPROVE_DETECTED_VALUE",
      correctedValue: isClassificationReviewCase(reviewCase)
        ? nextRoutableDocumentType(reviewCase?.detected_value)
        : "",
      correctedUnit: "",
      selectedCandidateId: firstReviewCandidateIdForCases(targetCases),
      comment: "",
    });
    mutation.reset();
  }, [open, reviewCase?.id, relatedReviewCaseKey]);

  if (!open || reviewCase === null) {
    return null;
  }

  const classificationMetadata = isClassificationCase
    ? getClassificationReviewMetadata(reviewCase)
    : null;
  const candidateOptions = getReviewCandidateOptionsForCases(
    resolutionTargetCases(reviewCase, relatedReviewCases),
  );
  const reviewThreshold = reviewCaseThreshold(reviewCase);
  const isBlockingCase = reviewCase.severity === "BLOCKING";
  const isContradictionCase = reviewCase.case_type === "CONTRADICTION";
  const canApproveDetectedFact =
    !isClassificationCase &&
    (candidateOptions.length > 0 || reviewCase.detected_value !== null);
  const fieldContext = reviewCase.field_name
    ? technicalFactLabelDescription(
        reviewCase.field_name,
        reviewCaseDocumentType(reviewCase),
      )
    : null;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.42)] px-4 py-3 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="max-h-[96vh] w-full max-w-2xl overflow-hidden rounded-[2rem] bg-[var(--color-surface-card)] shadow-[0_28px_80px_rgba(27,28,26,0.24)]">
        <div className="flex items-start justify-between gap-6 border-b border-[var(--color-stone)] px-6 py-4">
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

        <form className="grid max-h-[calc(96vh-5rem)] gap-3 overflow-y-auto px-6 py-4" onSubmit={submit}>
          <div className="grid gap-3">
            <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/35 p-3 text-sm leading-5 text-[var(--color-muted)]">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 size-5 shrink-0 text-[var(--color-error)]" />
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-error)]">
                    Problème
                  </p>
                  <p className="mt-1 font-semibold text-[var(--color-ink)]">
                    {reviewCase.description}
                    {reviewThreshold !== null ? (
                      <>
                        {" "}
                        Seuil requis : {formatConfidence(reviewThreshold)}.
                      </>
                    ) : null}
                  </p>
                </div>
              </div>
              {classificationMetadata !== null ? (
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-[var(--color-ink)]">
                  <div className="rounded-xl bg-white/70 px-3 py-2">
                    <dt className="font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
                      Score
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {formatConfidence(classificationMetadata.confidence)}
                    </dd>
                  </div>
                  <div className="rounded-xl bg-white/70 px-3 py-2">
                    <dt className="font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
                      Seuil
                    </dt>
                    <dd className="mt-1 font-semibold">
                      {formatConfidence(classificationMetadata.threshold)}
                    </dd>
                  </div>
                </dl>
              ) : null}
            </div>
            {fieldContext !== null ? (
              <div className="rounded-[1.25rem] bg-[var(--color-surface-raised)]/65 p-3 text-sm leading-5">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
                  Contexte du label
                </p>
                <p className="mt-2 font-semibold text-[var(--color-ink)]">
                  {reviewCase.field_name}
                </p>
                <p className="mt-1 text-[var(--color-muted)]">
                  {fieldContext}
                </p>
              </div>
            ) : null}
          </div>

          <div className="grid gap-2">
            <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
              Décision
            </span>
            <div className="grid gap-2">
              {(isClassificationCase ? canApproveDetectedClassification : canApproveDetectedFact) ? (
                <DecisionCard
                  checked={decision.action === "APPROVE_DETECTED_VALUE"}
                  label={
                    isClassificationCase
                      ? "Confirmer le type de document"
                      : isContradictionCase && candidateOptions.length > 0
                        ? "Choisir une valeur détectée"
                        : "Valider une valeur détectée"
                  }
                  onSelect={() =>
                    setDecision((current) => ({
                      ...current,
                      action: "APPROVE_DETECTED_VALUE",
                      selectedCandidateId:
                        current.selectedCandidateId ||
                        firstReviewCandidateIdForCases(
                          resolutionTargetCases(reviewCase, relatedReviewCases),
                        ),
                    }))
                  }
                />
              ) : null}
              <DecisionCard
                checked={decision.action === "CORRECT_VALUE"}
                label={isClassificationCase ? "Corriger le type" : "Corriger manuellement"}
                onSelect={() =>
                  setDecision((current) => ({
                    ...current,
                    action: "CORRECT_VALUE",
                  }))
                }
              />
              {!isClassificationCase && !isBlockingCase ? (
                <DecisionCard
                  checked={decision.action === "REJECT_VALUE"}
                  label="Écarter la valeur"
                  onSelect={() =>
                    setDecision((current) => ({
                      ...current,
                      action: "REJECT_VALUE",
                    }))
                  }
                />
              ) : null}
              {isClassificationCase ? (
                <DecisionCard
                  checked={decision.action === "REQUEST_NEW_DOCUMENT"}
                  label="Demander un nouveau PDF"
                  onSelect={() =>
                    setDecision((current) => ({
                      ...current,
                      action: "REQUEST_NEW_DOCUMENT",
                    }))
                  }
                />
              ) : null}
            </div>
          </div>

          {decision.action === "APPROVE_DETECTED_VALUE" &&
          !isClassificationCase &&
          candidateOptions.length > 0 ? (
            <div className="grid gap-2">
              <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
                Valeur à retenir
              </span>
              <div className="grid gap-2">
                {candidateOptions.map((candidate) => (
                  <button
                    key={candidate.id}
                    type="button"
                    className={cn(
                      "rounded-2xl border bg-white px-4 py-3 text-left transition",
                      decision.selectedCandidateId === candidate.id
                        ? "border-[var(--color-forest)] shadow-[0_0_0_4px_rgba(148,164,132,0.22)]"
                        : "border-[var(--color-stone)] hover:border-[var(--color-sage)]",
                    )}
                    onClick={() =>
                      setDecision((current) => ({
                        ...current,
                        selectedCandidateId: candidate.id,
                      }))
                    }
                  >
                    <span className="block text-sm font-semibold leading-5 text-[var(--color-ink)]">
                      {candidate.value}
                    </span>
                    <span className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs font-semibold text-[var(--color-muted)]">
                      <span>{candidate.sourceLabel}</span>
                      <span>{candidate.scoreLabel}</span>
                      {candidate.normalizedValue ? (
                        <span>Normalisé : {candidate.normalizedValue}</span>
                      ) : null}
                      {candidate.reason ? (
                        <span className="text-[var(--color-teak)]">{candidate.reason}</span>
                      ) : null}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {decision.action === "CORRECT_VALUE" && isClassificationCase ? (
            <label className="grid gap-2">
              <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
                Type corrigé
              </span>
              <select
                className={inputClassName}
                onChange={(event) =>
                  setDecision((current) => ({
                    ...current,
                    correctedValue: event.target.value,
                  }))
                }
                value={decision.correctedValue}
              >
                {DOCUMENT_TYPE_OPTIONS.map((documentType) => (
                  <option key={documentType} value={documentType}>
                    {technicalDocumentTypeLabel(documentType)}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          {decision.action === "CORRECT_VALUE" && !isClassificationCase ? (
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

          <div className="flex flex-wrap justify-end gap-3 border-t border-[var(--color-stone)] pt-3">
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

function DecisionCard({
  checked,
  label,
  onSelect,
}: {
  checked: boolean;
  label: string;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "rounded-2xl border bg-white px-4 py-2.5 text-left transition",
        checked
          ? "border-[var(--color-forest)] shadow-[0_0_0_4px_rgba(148,164,132,0.22)]"
          : "border-[var(--color-stone)] hover:border-[var(--color-sage)]",
      )}
      onClick={onSelect}
    >
      <span className="flex items-start gap-3">
        <span
          className={cn(
            "mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border",
            checked ? "border-[var(--color-forest)]" : "border-[var(--color-muted)]/45",
          )}
          aria-hidden="true"
        >
          {checked ? (
            <span className="size-2 rounded-full bg-[var(--color-forest)]" />
          ) : null}
        </span>
        <span>
          <span className="block text-sm font-semibold text-[var(--color-ink)]">
            {label}
          </span>
        </span>
      </span>
    </button>
  );
}

const inputClassName =
  "rounded-2xl border border-[var(--color-stone)] bg-white px-4 text-sm font-semibold text-[var(--color-ink)] outline-none transition placeholder:text-[var(--color-muted)]/55 focus:border-[var(--color-forest)] focus:ring-4 focus:ring-[var(--color-sage-soft)]";

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();

  return trimmed.length > 0 ? trimmed : null;
}

function isClassificationReviewCase(reviewCase: TechnicalReviewCase | null): boolean {
  return reviewCase?.case_type === "CLASSIFICATION_UNCERTAIN";
}

function getClassificationReviewMetadata(
  reviewCase: TechnicalReviewCase,
): { confidence: number | null; threshold: number | null } | null {
  const metadata = reviewCase.metadata_json;
  if (metadata === null || typeof metadata !== "object" || Array.isArray(metadata)) {
    return null;
  }

  return {
    confidence: toNullableNumber((metadata as Record<string, unknown>).confidence),
    threshold: toNullableNumber((metadata as Record<string, unknown>).threshold),
  };
}

function reviewCaseThreshold(reviewCase: TechnicalReviewCase) {
  const metadata = reviewCase.metadata_json;
  if (metadata === null || typeof metadata !== "object" || Array.isArray(metadata)) {
    return null;
  }

  return toNullableNumber((metadata as Record<string, unknown>).threshold);
}

function relatedReviewCases(
  reviewCase: TechnicalReviewCase | null,
  reviewCases: TechnicalReviewCase[],
) {
  if (reviewCase === null || reviewCase.field_name === null) {
    return reviewCase === null ? [] : [reviewCase];
  }

  const relatedCases = reviewCases.filter(
    (candidateReviewCase) =>
      candidateReviewCase.field_name === reviewCase.field_name &&
      candidateReviewCase.status === reviewCase.status &&
      !isClassificationReviewCase(candidateReviewCase),
  );

  return relatedCases.length > 0 ? relatedCases : [reviewCase];
}

function resolutionTargetCases(
  reviewCase: TechnicalReviewCase,
  relatedCases: TechnicalReviewCase[],
) {
  if (isClassificationReviewCase(reviewCase)) {
    return [reviewCase];
  }

  const openRelatedCases = relatedCases.filter(
    (candidateReviewCase) =>
      candidateReviewCase.field_name === reviewCase.field_name &&
      ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(candidateReviewCase.status),
  );

  return openRelatedCases.length > 0 ? openRelatedCases : [reviewCase];
}

function getReviewCandidateOptionsForCases(
  reviewCases: TechnicalReviewCase[],
): ReviewCandidateOption[] {
  const candidatesById = new Map<string, ReviewCandidateOption>();

  for (const reviewCase of reviewCases) {
    for (const candidate of getReviewCandidateOptions(reviewCase)) {
      candidatesById.set(candidate.id, candidate);
    }
  }

  return Array.from(candidatesById.values()).sort(
    (left, right) => candidateScoreValue(right) - candidateScoreValue(left),
  );
}

function getReviewCandidateOptions(reviewCase: TechnicalReviewCase | null): ReviewCandidateOption[] {
  const metadata = reviewCase?.metadata_json;
  if (metadata === null || typeof metadata !== "object" || Array.isArray(metadata)) {
    return [];
  }

  const candidates = (metadata as Record<string, unknown>).candidates;
  if (!Array.isArray(candidates)) {
    const candidateId = (metadata as Record<string, unknown>).candidate_id;
    if (typeof candidateId !== "string" || candidateId.length === 0) {
      return [];
    }
    return [
      reviewCandidateOption(candidateId, metadata as Record<string, unknown>),
    ];
  }

  return candidates
    .map((candidate) => {
      if (candidate === null || typeof candidate !== "object" || Array.isArray(candidate)) {
        return null;
      }
      const candidateRecord = candidate as Record<string, unknown>;
      const candidateId = candidateRecord.candidate_id;
      if (typeof candidateId !== "string" || candidateId.length === 0) {
        return null;
      }
      return reviewCandidateOption(candidateId, candidateRecord);
    })
    .filter((candidate): candidate is ReviewCandidateOption => candidate !== null);
}

function firstReviewCandidateIdForCases(reviewCases: TechnicalReviewCase[]): string {
  return getReviewCandidateOptionsForCases(reviewCases)[0]?.id ?? "";
}

function reviewCandidateOption(
  candidateId: string,
  candidate: Record<string, unknown>,
): ReviewCandidateOption {
  const rawValue =
    stringValue(candidate.raw_value) ??
    stringValue(candidate.detected_value) ??
    stringValue(candidate.normalized_value) ??
    "Valeur détectée";
  const normalizedValue = stringValue(candidate.normalized_value);
  const unit = stringValue(candidate.unit);
  const confidence = toNullableNumber(candidate.confidence ?? candidate.extractor_confidence);
  const threshold = toNullableNumber(candidate.threshold);
  const sourceDocumentType = stringValue(candidate.source_document_type);
  return {
    id: candidateId,
    normalizedValue:
      normalizedValue !== null && normalizedValue !== rawValue ? normalizedValue : null,
    reason:
      confidence !== null && threshold !== null && confidence < threshold
        ? `Sous le seuil ${formatConfidence(threshold)}`
        : null,
    scoreLabel: confidence === null ? "Score non renseigné" : formatConfidence(confidence),
    sourceLabel: technicalDocumentTypeLabel(sourceDocumentType),
    value: `${rawValue}${unit && !rawValue.includes(unit) ? ` ${unit}` : ""}`,
  };
}

function reviewCaseDocumentType(reviewCase: TechnicalReviewCase) {
  const metadata = reviewCase.metadata_json;
  if (metadata === null || typeof metadata !== "object" || Array.isArray(metadata)) {
    return null;
  }

  return stringValue((metadata as Record<string, unknown>).source_document_type);
}

function candidateScoreValue(candidate: ReviewCandidateOption): number {
  const match = /^(\d+(?:\.\d+)?) %$/.exec(candidate.scoreLabel);
  return match ? Number(match[1]) : -1;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function toNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatConfidence(value: number | null): string {
  return value === null
    ? "Non disponible"
    : `${truncateDecimal(value * 100, 2).toFixed(2)} %`;
}

function truncateDecimal(value: number, decimals: number) {
  const factor = 10 ** decimals;
  return Math.trunc(value * factor) / factor;
}

function isRoutableDocumentType(value: string | null | undefined): boolean {
  return (
    value === "TECHNICAL_SHEET" ||
    value === "MATERIAL_SPECIFICATION" ||
    value === "ASSEMBLY_NOTICE"
  );
}

function nextRoutableDocumentType(value: string | null | undefined): string {
  return value !== null && value !== undefined && isRoutableDocumentType(value)
    ? value
    : "TECHNICAL_SHEET";
}
