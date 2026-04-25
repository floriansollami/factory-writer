import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Flower2,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { RulesManagementPanel } from "@/features/style-guide/RulesManagementPanel";
import { StyleGuideFlowProgress } from "@/features/style-guide/StyleGuideFlowProgress";
import type {
  StyleGuideOverview,
  StyleRule,
} from "@/features/style-guide/schema";
import {
  approveStylePack,
  getStyleGuideOverview,
  patchStyleRule,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil admin",
  "Guide de style",
  "Fiches produit",
  "Signaux marketing",
];

type StyleGuideReviewPageProps = {
  onBack: () => void;
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
};

export function StyleGuideReviewPage({
  onBack,
  onOpenAdminHome,
  onOpenProductSheets,
}: StyleGuideReviewPageProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));
  const { data, isPending, error } = useQuery({
    queryKey: ["style-guide-overview"],
    queryFn: getStyleGuideOverview,
  });

  useEffect(() => {
    if (!isPending && !error && data?.activePack === null) {
      navigate(styleGuidePathForReturnTo(returnTo), { replace: true });
    }
  }, [data?.activePack, error, isPending, navigate, returnTo]);

  if (isPending) {
    return (
      <StyleGuideReviewShell
        onBack={onBack}
        onOpenAdminHome={onOpenAdminHome}
        onOpenProductSheets={onOpenProductSheets}
      >
        <div className="grid min-h-[70vh] place-items-center text-[var(--color-forest)]">
          <Loader2 className="size-10 animate-spin" aria-label="Chargement" />
        </div>
      </StyleGuideReviewShell>
    );
  }

  if (error) {
    return (
      <StyleGuideReviewShell
        onBack={onBack}
        onOpenAdminHome={onOpenAdminHome}
        onOpenProductSheets={onOpenProductSheets}
      >
        <Card className="max-w-lg">
          <CardTitle>Impossible de charger la revue des règles</CardTitle>
          <p className="mt-3 text-[var(--color-muted)]">{error.message}</p>
          <Button className="mt-5" variant="secondary" onClick={onBack}>
            Retour
          </Button>
        </Card>
      </StyleGuideReviewShell>
    );
  }

  if (data.activePack === null) {
    return (
      <StyleGuideReviewShell
        onBack={onBack}
        onOpenAdminHome={onOpenAdminHome}
        onOpenProductSheets={onOpenProductSheets}
      >
        <div className="grid min-h-[70vh] place-items-center text-[var(--color-forest)]">
          <Loader2 className="size-10 animate-spin" aria-label="Redirection" />
        </div>
      </StyleGuideReviewShell>
    );
  }

  return (
    <StyleGuideReviewShell
      onBack={onBack}
      onOpenAdminHome={onOpenAdminHome}
      onOpenProductSheets={onOpenProductSheets}
    >
      <StyleGuideReviewWorkspace
        initialRules={data.rules}
        pack={data.activePack}
      />
    </StyleGuideReviewShell>
  );
}

function StyleGuideReviewShell({
  children,
  onBack,
  onOpenAdminHome,
  onOpenProductSheets,
}: {
  children: ReactNode;
  onBack: () => void;
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
}) {
  return (
    <main className="min-h-screen bg-[var(--color-ivory)] text-[var(--color-ink)]">
      <div className="grid min-h-screen grid-cols-[280px_1fr] max-xl:grid-cols-1">
        <aside className="sticky top-0 self-start h-screen overflow-x-hidden overflow-y-auto bg-[var(--color-forest)] px-6 py-8 text-white max-xl:hidden">
          <div className="absolute -right-24 top-24 size-64 rounded-full bg-white/10 blur-3xl" />
          <div className="relative">
            <div className="flex items-center gap-3">
              <div className="grid size-11 place-items-center rounded-2xl bg-white/12">
                <Flower2 className="size-6" />
              </div>
              <div>
                <p className="font-serif text-xl font-semibold tracking-[-0.03em]">
                  Axolotl
                </p>
                <p className="text-xs uppercase tracking-[0.2em] text-white/60">
                  Factory Writer
                </p>
              </div>
            </div>

            <nav className="mt-12 space-y-2" aria-label="Navigation principale">
              {navItems.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={cn(
                    "flex w-full items-center justify-between rounded-full px-4 py-3 text-left text-sm font-semibold text-white/70 transition hover:bg-white/10 hover:text-white",
                    item === "Guide de style" &&
                      "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={navigationHandlerForReviewItem({
                    item,
                    onBack,
                    onOpenAdminHome,
                    onOpenProductSheets,
                  })}
                >
                  {item}
                  {item === "Accueil admin" ? (
                    <ArrowRight className="size-4" />
                  ) : null}
                  {item === "Fiches produit" ? (
                    <ArrowRight className="size-4" />
                  ) : null}
                  {item === "Guide de style" ? (
                    <ArrowRight className="size-4" />
                  ) : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">{children}</section>
      </div>
    </main>
  );
}

function StyleGuideReviewWorkspace({
  initialRules,
  pack,
}: {
  initialRules: StyleRule[];
  pack: NonNullable<StyleGuideOverview["activePack"]>;
}) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));
  const queryClient = useQueryClient();
  const [rules, setRules] = useState(initialRules);
  const isRuntimePackActive = pack.status === "ACTIF";
  const isEditable = pack.status === "BROUILLON";
  const isApprovalOpen = searchParams.get("dialog") === "approve";
  const taxonomyOptions = pack.scopes.filter((scope) => scope !== "Global");

  useEffect(() => {
    setRules(initialRules);
  }, [initialRules]);

  useEffect(() => {
    if (!isEditable && isApprovalOpen) {
      navigate(returnTo ?? "/style-guide", { replace: true });
    }
  }, [isApprovalOpen, isEditable, navigate, returnTo]);

  const patchRuleMutation = useMutation({
    mutationFn: ({
      ruleId,
      payload,
    }: {
      ruleId: string;
      payload: Parameters<typeof patchStyleRule>[2];
    }) => patchStyleRule(pack.id, ruleId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["style-guide-overview"],
      });
    },
  });

  const approvePackMutation = useMutation({
    mutationFn: () => approveStylePack(pack.id),
    onSuccess: () => {
      navigate(returnTo ?? "/style-guide", { replace: true });
      void queryClient.invalidateQueries({
        queryKey: ["style-guide-overview"],
      });
    },
  });

  const pendingRules = rules.filter(
    (rule) => rule.decisionEditoriale === "A_VALIDER",
  ).length;
  const approvedRules = rules.filter(
    (rule) => rule.decisionEditoriale === "APPROUVEE",
  ).length;
  const disabledRules = rules.filter(
    (rule) => rule.decisionEditoriale === "DESACTIVEE",
  ).length;
  const canActivate = isEditable && rules.length > 0 && pendingRules === 0;
  const isPendingMutation =
    patchRuleMutation.isPending || approvePackMutation.isPending;
  const mutationError =
    patchRuleMutation.error?.message ??
    approvePackMutation.error?.message ??
    null;

  async function handleUpdateRule(rule: StyleRule) {
    await patchRuleMutation.mutateAsync({
      ruleId: rule.id,
      payload: {
        texteRegle: rule.texteRegle,
        typeRegle: rule.typeRegle,
        niveauContrainte: rule.niveauContrainte,
        taxonomieCode: rule.taxonomieCode,
      },
    });
  }

  async function handleApproveRule(ruleId: string) {
    await patchRuleMutation.mutateAsync({
      ruleId,
      payload: { decisionEditoriale: "APPROUVEE", estActif: true },
    });
  }

  async function handleDisableRule(ruleId: string) {
    await patchRuleMutation.mutateAsync({
      ruleId,
      payload: { decisionEditoriale: "DESACTIVEE", estActif: false },
    });
  }

  async function handleRestoreRule(ruleId: string) {
    await patchRuleMutation.mutateAsync({
      ruleId,
      payload: { decisionEditoriale: "A_VALIDER", estActif: true },
    });
  }

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
            Gouvernance éditoriale
          </p>
          <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
            Guide de style
          </h1>
          <StyleGuideFlowProgress className="mt-3" currentStep="review" />
        </div>
      </header>

      <section className="mt-8">
        <Card className="relative overflow-hidden bg-[linear-gradient(145deg,#fffdf7,#eef2ea)] p-8">
          <div className="absolute -right-20 -top-24 size-72 rounded-full bg-[var(--color-sage-soft)] blur-3xl" />
          <div className="relative max-w-3xl">
            <Badge tone={packStatusTone(pack.status)}>
              {packStatusLabel(pack.status)}
            </Badge>
            <h2 className="mt-4 max-w-2xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
              {isRuntimePackActive
                ? "Contrôler les règles actives"
                : "Traiter les règles extraites"}
            </h2>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--color-muted)]">
              {isRuntimePackActive
                ? "Ce pack est disponible pour la génération des fiches produit. Les règles restent consultables mais ne sont plus modifiables dans cette phase."
                : "Le pack candidat est prêt pour revue. Passez les règles une à une, consultez leur source et tranchez avant l’activation."}
            </p>
          </div>
        </Card>
      </section>

      {mutationError ? (
        <Card className="mt-6 border border-[var(--color-error-soft)] bg-[var(--color-error-soft)]/35 p-4">
          <p className="text-sm font-semibold text-[var(--color-error)]">
            {mutationError}
          </p>
        </Card>
      ) : null}

      <RulesManagementPanel
        documentSourcePdf={pack.documentSourcePdf}
        isPending={isPendingMutation}
        onApproveRule={handleApproveRule}
        onDisableRule={handleDisableRule}
        onRestoreRule={handleRestoreRule}
        onUpdateRule={handleUpdateRule}
        readOnly={!isEditable}
        rules={rules}
        taxonomyOptions={taxonomyOptions}
      />

      {canActivate ? (
        <section className="sticky bottom-4 z-20 mt-6 rounded-[1.5rem] border border-[var(--color-gold-soft)] bg-[rgba(255,251,240,0.94)] p-4 shadow-[0_18px_50px_rgba(27,28,26,0.10)] backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-[var(--color-ink)]">
                Le pack est prêt à être activé.
              </p>
              <p className="mt-1 text-sm text-[var(--color-muted)]">
                {approvedRules} approuvée{approvedRules > 1 ? "s" : ""}
                {disabledRules > 0
                  ? ` · ${disabledRules} écartée${disabledRules > 1 ? "s" : ""}`
                  : ""}
              </p>
            </div>
            <Button
              disabled={isPendingMutation}
              onClick={() =>
                setSearchParams(buildStyleGuideReviewSearchParams(returnTo, { dialog: "approve" }))
              }
            >
              <ShieldCheck className="size-4" />
              Activer le pack
            </Button>
          </div>
        </section>
      ) : null}

      {isApprovalOpen ? (
        <ApprovalDialog
          approvedRules={approvedRules}
          disabledRules={disabledRules}
          isPending={approvePackMutation.isPending}
          onApprove={() => approvePackMutation.mutate()}
          onClose={() =>
            setSearchParams(buildStyleGuideReviewSearchParams(returnTo), { replace: true })
          }
          totalRules={rules.length}
        />
      ) : null}
    </>
  );
}

function ApprovalDialog({
  approvedRules,
  disabledRules,
  isPending,
  onApprove,
  onClose,
  totalRules,
}: {
  approvedRules: number;
  disabledRules: number;
  isPending: boolean;
  onApprove: () => void;
  onClose: () => void;
  totalRules: number;
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.22)] p-6 backdrop-blur-sm">
      <Card className="w-full max-w-xl bg-[var(--color-ivory)] p-6">
        <CardTitle className="mt-4">Activer le pack candidat</CardTitle>
        <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
          Toutes les règles ont maintenant une décision. Vous pouvez activer ce
          pack pour en faire la référence de style utilisée pour la génération.
        </p>
        <dl className="mt-5 grid grid-cols-3 gap-3 text-center">
          <div className="rounded-2xl bg-white/75 p-3">
            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
              Règles
            </dt>
            <dd className="mt-1 text-xl font-semibold text-[var(--color-ink)]">
              {totalRules}
            </dd>
          </div>
          <div className="rounded-2xl bg-white/75 p-3">
            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
              Approuvées
            </dt>
            <dd className="mt-1 text-xl font-semibold text-[var(--color-ink)]">
              {approvedRules}
            </dd>
          </div>
          <div className="rounded-2xl bg-white/75 p-3">
            <dt className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
              Écartées
            </dt>
            <dd className="mt-1 text-xl font-semibold text-[var(--color-ink)]">
              {disabledRules}
            </dd>
          </div>
        </dl>
        <div className="mt-6 grid gap-2 sm:grid-cols-2">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={isPending}
            className="w-full min-w-0"
          >
            Retour
          </Button>
          <Button
            onClick={onApprove}
            disabled={isPending}
            className="w-full min-w-0"
          >
            <ShieldCheck className="size-4" />
            Activer
          </Button>
        </div>
      </Card>
    </div>
  );
}

function packStatusTone(
  status: NonNullable<StyleGuideOverview["activePack"]>["status"],
) {
  if (status === "ACTIF") {
    return "success";
  }
  if (status === "ARCHIVE") {
    return "neutral";
  }
  return "warning";
}

function navigationHandlerForReviewItem({
  item,
  onBack,
  onOpenAdminHome,
  onOpenProductSheets,
}: {
  item: string;
  onBack: () => void;
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
}) {
  if (item === "Accueil admin") {
    return onOpenAdminHome;
  }

  if (item === "Fiches produit") {
    return onOpenProductSheets;
  }

  if (item === "Guide de style") {
    return onBack;
  }

  return undefined;
}

function packStatusLabel(
  status: NonNullable<StyleGuideOverview["activePack"]>["status"],
) {
  if (status === "ACTIF") {
    return "Actif";
  }
  if (status === "ARCHIVE") {
    return "Archivé";
  }
  return "À relire";
}

function sanitizeReturnTo(value: string | null) {
  if (value !== null && value.startsWith("/product-sheets/") && !value.startsWith("//")) {
    return value;
  }

  return null;
}

function buildStyleGuideReviewSearchParams(
  returnTo: string | null,
  values: Record<string, string> = {},
) {
  return returnTo === null ? values : { ...values, returnTo };
}

function styleGuidePathForReturnTo(returnTo: string | null) {
  return returnTo === null ? "/style-guide" : `/style-guide?returnTo=${encodeURIComponent(returnTo)}`;
}
