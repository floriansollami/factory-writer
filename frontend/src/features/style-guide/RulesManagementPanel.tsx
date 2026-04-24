import {
  Check,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  Pencil,
  RotateCcw,
} from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { RuleEditorDialog } from "@/features/style-guide/RuleEditorDialog";
import type { StyleRule } from "@/features/style-guide/schema";
import { cn } from "@/lib/utils";

const SourcePdfPreview = lazy(() =>
  import("@/features/style-guide/SourcePdfDialog").then((module) => ({
    default: module.SourcePdfPreview,
  })),
);

type RulesManagementPanelProps = {
  documentSourcePdf: string;
  rules: StyleRule[];
  taxonomyOptions: string[];
  readOnly?: boolean;
  isPending?: boolean;
  onUpdateRule: (rule: StyleRule) => void | Promise<void>;
  onApproveRule: (ruleId: string) => void | Promise<void>;
  onDisableRule: (ruleId: string) => void | Promise<void>;
  onRestoreRule: (ruleId: string) => void | Promise<void>;
};

export function RulesManagementPanel({
  documentSourcePdf,
  rules,
  taxonomyOptions,
  readOnly = false,
  isPending = false,
  onUpdateRule,
  onApproveRule,
  onDisableRule,
  onRestoreRule,
}: RulesManagementPanelProps) {
  const [activeRuleIndex, setActiveRuleIndex] = useState(0);
  const [editedRule, setEditedRule] = useState<StyleRule | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);

  const summary = useMemo(
    () => ({
      pending: rules.filter((rule) => rule.decisionEditoriale === "A_VALIDER")
        .length,
      approved: rules.filter((rule) => rule.decisionEditoriale === "APPROUVEE")
        .length,
      disabled: rules.filter((rule) => rule.decisionEditoriale === "DESACTIVEE")
        .length,
    }),
    [rules],
  );

  useEffect(() => {
    if (rules.length === 0) {
      setActiveRuleIndex(0);
      return;
    }

    setActiveRuleIndex((current) =>
      Math.min(Math.max(current, 0), rules.length - 1),
    );
  }, [rules]);

  const currentIndex = useMemo(() => {
    if (rules.length === 0) {
      return -1;
    }
    return Math.min(Math.max(activeRuleIndex, 0), rules.length - 1);
  }, [activeRuleIndex, rules]);

  const currentRule = currentIndex >= 0 ? rules[currentIndex] : null;
  const previousRule = currentIndex > 0 ? rules[currentIndex - 1] : null;
  const nextRule =
    currentIndex >= 0 && currentIndex < rules.length - 1
      ? rules[currentIndex + 1]
      : null;

  function openEditDialog(rule: StyleRule) {
    setEditedRule(rule);
    setIsEditorOpen(true);
  }

  async function saveRule(savedRule: StyleRule) {
    await onUpdateRule(savedRule);
  }

  function focusNextRuleAfter(
    currentPosition: number,
    nextDecision?: StyleRule["decisionEditoriale"],
  ) {
    const projectedRules =
      nextDecision === undefined
        ? rules
        : rules.map((rule, index) =>
            index === currentPosition
              ? { ...rule, decisionEditoriale: nextDecision }
              : rule,
          );

    if (projectedRules.length === 0) {
      setActiveRuleIndex(0);
      return;
    }

    if (currentPosition < 0 || currentPosition >= projectedRules.length) {
      setActiveRuleIndex(0);
      return;
    }

    const nextPending = projectedRules
      .slice(currentPosition + 1)
      .findIndex((rule) => rule.decisionEditoriale === "A_VALIDER");

    if (nextPending !== -1) {
      setActiveRuleIndex(currentPosition + 1 + nextPending);
      return;
    }

    const wrappedPending = projectedRules
      .slice(0, currentPosition)
      .findIndex((rule) => rule.decisionEditoriale === "A_VALIDER");
    if (wrappedPending !== -1) {
      setActiveRuleIndex(wrappedPending);
      return;
    }

    setActiveRuleIndex(Math.min(currentPosition, projectedRules.length - 1));
  }

  async function handleApproveCurrentRule() {
    if (currentRule === null) {
      return;
    }

    await onApproveRule(currentRule.id);
    focusNextRuleAfter(currentIndex, "APPROUVEE");
  }

  async function handleDisableCurrentRule() {
    if (currentRule === null) {
      return;
    }

    await onDisableRule(currentRule.id);
    focusNextRuleAfter(currentIndex, "DESACTIVEE");
  }

  async function handleRestoreCurrentRule() {
    if (currentRule === null) {
      return;
    }

    await onRestoreRule(currentRule.id);
  }

  return (
    <section id="style-rules-review" className="mt-6">
      <Card className="overflow-hidden p-0">
        <div className="border-b border-black/5 bg-[linear-gradient(145deg,rgba(255,253,248,0.96),rgba(238,242,234,0.9))] p-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Revue des regles
            </p>
            <CardTitle className="mt-2">
              {readOnly
                ? "Relecture du pack actif"
                : "Revue sequentielle du pack candidat"}
            </CardTitle>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2 text-sm">
            <ReviewSummaryChip
              label="A traiter"
              value={summary.pending}
              tone="warning"
            />
            <ReviewSummaryChip
              label="Approuvees"
              value={summary.approved}
              tone="success"
            />
            <ReviewSummaryChip
              label="Ecartees"
              value={summary.disabled}
              tone="neutral"
            />
          </div>
        </div>

        {currentRule ? (
          <div className="bg-[linear-gradient(180deg,rgba(255,253,248,0.72),rgba(251,249,245,0.48))] p-4 sm:p-5">
            <div className="grid gap-4 xl:grid-cols-[minmax(19rem,23rem)_minmax(0,1fr)] xl:h-[calc(100vh-24rem)] xl:min-h-[34rem] xl:max-h-[40rem] xl:overflow-hidden">
              <div className="flex min-h-0 flex-col overflow-hidden rounded-[1.5rem] border border-black/6 bg-[rgba(255,255,255,0.88)] shadow-[0_18px_40px_rgba(27,28,26,0.08)]">
                <div className="flex items-center justify-between gap-3 border-b border-black/6 px-4 py-4">
                  <div>
                    <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                      Progression
                    </p>
                    <p className="mt-1 text-sm text-[var(--color-muted)]">
                      Regle {currentIndex + 1} sur {rules.length}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        previousRule && setActiveRuleIndex(currentIndex - 1)
                      }
                      disabled={previousRule === null || isPending}
                    >
                      <ChevronLeft className="size-4" />
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        nextRule && setActiveRuleIndex(currentIndex + 1)
                      }
                      disabled={nextRule === null || isPending}
                    >
                      <ChevronRight className="size-4" />
                    </Button>
                  </div>
                </div>

                <div className="flex min-h-0 flex-1 flex-col">
                  <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5 sm:py-5">
                    <div className="flex flex-wrap gap-2">
                      <EnumPill tone="neutral">
                        {scopeLabel(currentRule.taxonomieCode)}
                      </EnumPill>
                      <EnumPill tone={ruleTypeTone(currentRule.typeRegle)}>
                        {currentRule.typeRegle}
                      </EnumPill>
                      <EnumPill
                        tone={
                          currentRule.niveauContrainte === "HARD"
                            ? "danger"
                            : "neutral"
                        }
                      >
                        {currentRule.niveauContrainte}
                      </EnumPill>
                    </div>

                    <div className="mt-4 rounded-[1.35rem] border border-black/6 bg-[linear-gradient(180deg,#fffdf7,#f4f1e8)] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
                      <p className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                        Regle proposee
                      </p>
                      <p className="mt-3 font-serif text-[1.9rem] font-semibold leading-tight tracking-[-0.04em] text-[var(--color-ink)]">
                        {currentRule.texteRegle}
                      </p>
                    </div>
                  </div>

                  {!readOnly ? (
                    <div className="border-t border-black/6 bg-white/92 px-4 py-4 backdrop-blur sm:px-5">
                      <div className="grid gap-2 sm:grid-cols-2">
                        {currentRule.decisionEditoriale === "DESACTIVEE" ? (
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => void handleRestoreCurrentRule()}
                            disabled={isPending}
                          >
                            <RotateCcw className="size-4" />
                            Restaurer
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={() => void handleDisableCurrentRule()}
                            disabled={isPending}
                          >
                            Ecarter
                          </Button>
                        )}

                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => openEditDialog(currentRule)}
                          disabled={isPending}
                        >
                          <Pencil className="size-4" />
                          Modifier
                        </Button>
                      </div>

                      {currentRule.decisionEditoriale !== "APPROUVEE" ? (
                        <Button
                          className="mt-2 w-full"
                          type="button"
                          onClick={() => void handleApproveCurrentRule()}
                          disabled={isPending}
                        >
                          <Check className="size-4" />
                          Approuver cette regle
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>

              <Suspense fallback={<PdfFallback />}>
                <SourcePdfPreview
                  className="min-h-[20rem] xl:h-full"
                  fileName={documentSourcePdf}
                  excerpt={currentRule.provenance.extrait}
                  pageStart={currentRule.provenance.pageStart}
                  pageEnd={currentRule.provenance.pageEnd}
                />
              </Suspense>
            </div>
          </div>
        ) : (
          <div className="grid place-items-center gap-2 px-6 py-14 text-center text-sm text-[var(--color-muted)]">
            <FileSearch className="size-7" />
            Aucune regle a relire pour le moment.
          </div>
        )}
      </Card>

      {!readOnly && editedRule ? (
        <RuleEditorDialog
          open={isEditorOpen}
          rule={editedRule}
          taxonomyOptions={taxonomyOptions}
          onClose={() => setIsEditorOpen(false)}
          onSave={saveRule}
        />
      ) : null}
    </section>
  );
}

function ReviewSummaryChip({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "success" | "warning" | "neutral" | "danger";
  value: number;
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]",
        reviewSummaryChipClass(tone),
      )}
    >
      <span className="text-[0.68rem] font-bold uppercase tracking-[0.16em] text-current/78">
        {label}
      </span>
      <span className="font-serif text-lg font-semibold tracking-[-0.03em] text-[var(--color-ink)]">
        {value}
      </span>
    </div>
  );
}

function PdfFallback() {
  return (
    <div className="grid min-h-[24rem] place-items-center rounded-[1.25rem] border border-black/6 bg-white text-[var(--color-muted)]">
      Chargement du PDF…
    </div>
  );
}

function scopeLabel(taxonomieCode: StyleRule["taxonomieCode"]) {
  if (!taxonomieCode) {
    return "Globale";
  }

  return taxonomieCode.replaceAll("_", " ");
}

function ruleTypeTone(typeRegle: StyleRule["typeRegle"]) {
  if (typeRegle === "PROMESSE_INTERDITE") {
    return "danger";
  }
  if (typeRegle === "TON") {
    return "warning";
  }
  return "neutral";
}

type EnumPillProps = {
  children: string;
  inverted?: boolean;
  tone: "success" | "warning" | "neutral" | "danger";
};

function EnumPill({ children, inverted = false, tone }: EnumPillProps) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center gap-2 rounded-full border px-2.5 py-1 text-[0.68rem] font-bold uppercase tracking-[0.11em]",
        inverted
          ? "border-white/16 bg-white/8 text-white/88"
          : enumPillClass(tone),
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full",
          inverted ? "bg-white/58" : enumPillDotClass(tone),
        )}
        aria-hidden="true"
      />
      {children}
    </span>
  );
}

function enumPillClass(tone: EnumPillProps["tone"]) {
  if (tone === "danger") {
    return "border-[rgba(159,39,39,0.18)] bg-[rgba(159,39,39,0.045)] text-[var(--color-error)]";
  }
  if (tone === "warning") {
    return "border-[rgba(141,77,50,0.18)] bg-[rgba(212,179,116,0.10)] text-[var(--color-teak)]";
  }
  if (tone === "success") {
    return "border-[rgba(23,49,36,0.16)] bg-[rgba(220,233,222,0.42)] text-[var(--color-forest)]";
  }
  return "border-black/10 bg-white/55 text-[var(--color-muted)]";
}

function enumPillDotClass(tone: EnumPillProps["tone"]) {
  if (tone === "danger") {
    return "bg-[var(--color-error)]";
  }
  if (tone === "warning") {
    return "bg-[var(--color-gold)]";
  }
  if (tone === "success") {
    return "bg-[var(--color-forest)]";
  }
  return "bg-[var(--color-muted)]";
}

function reviewSummaryChipClass(tone: EnumPillProps["tone"]) {
  if (tone === "warning") {
    return "border-[rgba(212,179,116,0.18)] bg-[rgba(255,244,214,0.74)] text-[var(--color-teak)]";
  }
  if (tone === "success") {
    return "border-[rgba(23,49,36,0.12)] bg-[rgba(220,233,222,0.58)] text-[var(--color-forest)]";
  }
  return "border-black/8 bg-[rgba(244,240,232,0.72)] text-[var(--color-muted)]";
}
