import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileCheck2,
  Loader2,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";

import { AxolotlLogo } from "@/components/brand/AxolotlLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { RecentPacksTable } from "@/features/style-guide/RecentPacksTable";
import { StyleGuideFlowProgress } from "@/features/style-guide/StyleGuideFlowProgress";
import type {
  StyleGuideOverview,
  StyleGuideStartIngestionResponse,
  StyleRule,
} from "@/features/style-guide/schema";
import { UploadGuideDialog } from "@/features/style-guide/UploadGuideDialog";
import { getStyleGuideOverview, startStyleGuideIngestion } from "@/lib/api";
import { formatAdminDateTime } from "@/lib/dateTime";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil",
  "Fiches produit",
  "Guide de style",
  "Paramètres",
];

const emptyStyleGuideOverview: StyleGuideOverview = {
  activePack: null,
  pendingDocumentSource: null,
  currentWorkflow: null,
  metrics: {
    activeRules: 0,
    needsReview: 0,
    disabledRules: 0,
    missingProvenance: 0,
  },
  rules: [],
  recentPacks: [],
};

type StyleGuideHomePageProps = {
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
  onOpenSettings: () => void;
  onOpenRulesReview: (returnTo?: string) => void;
};

type CurrentWorkflow = NonNullable<StyleGuideOverview["currentWorkflow"]>;
type PendingDocumentSource = NonNullable<StyleGuideOverview["pendingDocumentSource"]>;
type ExecutionMetadata = CurrentWorkflow["metadata"];

type OptimisticIngestion = {
  fileName: string;
  workflow: CurrentWorkflow;
};

export function StyleGuideHomePage({
  onOpenAdminHome,
  onOpenProductSheets,
  onOpenSettings,
  onOpenRulesReview,
}: StyleGuideHomePageProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [optimisticDocumentSource, setOptimisticDocumentSource] = useState<PendingDocumentSource | null>(null);
  const [optimisticIngestion, setOptimisticIngestion] = useState<OptimisticIngestion | null>(null);
  const dialog = searchParams.get("dialog");
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));
  const reuploadDocumentSourceId =
    dialog === "reupload" ? searchParams.get("documentSourceId") : null;
  const isUploadOpen = dialog === "upload" || dialog === "reupload";
  const { data, isPending, error } = useQuery({
    queryKey: ["style-guide-overview"],
    queryFn: getStyleGuideOverview,
    retry: false,
    refetchInterval: (query) => {
      const overview = query.state.data;
      const hasPackCandidate = overview?.activePack !== null && overview?.activePack !== undefined;
      const hasWorkflow = overview?.currentWorkflow !== null && overview?.currentWorkflow !== undefined;
      const hasOptimisticWorkflow = optimisticIngestion !== null && !hasPackCandidate;

      return hasWorkflow || hasOptimisticWorkflow ? 1_000 : false;
    },
  });
  const startIngestionMutation = useMutation({
    mutationFn: (documentSource: PendingDocumentSource) =>
      startStyleGuideIngestion(documentSource.documentSourceId),
    onSuccess: async (started, documentSource) => {
      setOptimisticDocumentSource(null);
      setOptimisticIngestion({
        fileName: documentSource.fileName,
        workflow: buildOptimisticWorkflow(started),
      });
      await queryClient.invalidateQueries({ queryKey: ["style-guide-overview"] });
    },
  });

  useEffect(() => {
    if (dialog === "reupload" && reuploadDocumentSourceId === null) {
      setSearchParams(buildStyleGuideSearchParams(returnTo), { replace: true });
    }
  }, [dialog, reuploadDocumentSourceId, returnTo, setSearchParams]);

  useEffect(() => {
    if (data?.currentWorkflow !== null && data?.currentWorkflow !== undefined) {
      setOptimisticIngestion(null);
      setOptimisticDocumentSource(null);
      return;
    }

    if (data?.activePack !== null && data?.activePack !== undefined) {
      setOptimisticIngestion(null);
      setOptimisticDocumentSource(null);
      return;
    }

    if (data?.pendingDocumentSource !== null && data?.pendingDocumentSource !== undefined) {
      setOptimisticDocumentSource(null);
    }
  }, [data?.activePack, data?.currentWorkflow, data?.pendingDocumentSource]);

  if (isPending && data === undefined) {
    return (
      <main className="grid min-h-screen place-items-center bg-[var(--color-ivory)] text-[var(--color-forest)]">
        <Loader2 className="size-10 animate-spin" aria-label="Chargement" />
      </main>
    );
  }

  const overview = data ?? emptyStyleGuideOverview;
  const activePack = overview.activePack;
  const isRuntimePackActive = activePack?.status === "ACTIF";
  const currentWorkflow =
    overview.currentWorkflow ?? (activePack === null ? optimisticIngestion?.workflow ?? null : null);
  const pendingDocumentSource =
    currentWorkflow === null ? overview.pendingDocumentSource ?? optimisticDocumentSource : null;
  const flowProgress = resolveStyleGuideFlowProgress({
    activePack,
    currentWorkflow,
    isRuntimePackActive,
    pendingDocumentSource,
  });

  function openUploadDialog() {
    setSearchParams(buildStyleGuideSearchParams(returnTo, { dialog: "upload" }));
  }

  function openReuploadDialog(documentSourceId: string) {
    setSearchParams(
      buildStyleGuideSearchParams(returnTo, {
        dialog: "reupload",
        documentSourceId,
      }),
    );
  }

  function closeUploadDialog() {
    setSearchParams(buildStyleGuideSearchParams(returnTo), { replace: true });
  }

  return (
    <main className="min-h-screen bg-[var(--color-ivory)] text-[var(--color-ink)]">
      <div className="grid min-h-screen grid-cols-[280px_1fr] max-xl:grid-cols-1">
        <aside className="sticky top-0 self-start h-screen overflow-x-hidden overflow-y-auto bg-[var(--color-forest)] px-6 py-8 text-white max-xl:hidden">
          <div className="absolute -right-24 top-24 size-64 rounded-full bg-white/10 blur-3xl" />
          <div className="relative">
            <div className="flex items-center gap-3">
              <div className="grid size-11 place-items-center rounded-2xl bg-white/12">
                <AxolotlLogo className="size-7" />
              </div>
              <div>
                <p className="font-serif text-xl font-semibold tracking-[-0.03em]">Axolotl</p>
                <p className="text-xs uppercase tracking-[0.2em] text-white/60">Factory Writer</p>
              </div>
            </div>

            <nav className="mt-12 space-y-2" aria-label="Navigation principale">
              {navItems.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={cn(
                    "flex w-full items-center justify-between rounded-full px-4 py-3 text-left text-sm font-semibold text-white/70 transition hover:bg-white/10 hover:text-white",
                    item === "Guide de style" && "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={
                    item === "Accueil"
                      ? onOpenAdminHome
                      : item === "Fiches produit"
                        ? onOpenProductSheets
                        : item === "Paramètres"
                          ? onOpenSettings
                        : undefined
                  }
                >
                  {item}
                  {item === "Accueil" ? <ArrowRight className="size-4" /> : null}
                  {item === "Fiches produit" ? <ArrowRight className="size-4" /> : null}
                  {item === "Guide de style" ? <ArrowRight className="size-4" /> : null}
                  {item === "Paramètres" ? <ArrowRight className="size-4" /> : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
                Gouvernance éditoriale
              </p>
              <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Guide de style
              </h1>
              {!isRuntimePackActive ? (
                <StyleGuideFlowProgress
                  className="mt-3"
                  currentStep={flowProgress.currentStep}
                  mode={flowProgress.mode}
                />
              ) : null}
            </div>
            <div className="flex flex-wrap gap-3">
              {isRuntimePackActive && returnTo !== null ? (
                <Button variant="secondary" onClick={() => navigate(returnTo)}>
                  <ArrowLeft className="size-4" />
                  Revenir à la fiche produit
                </Button>
              ) : null}
              {isRuntimePackActive ? (
                <Button variant="secondary" onClick={openUploadDialog}>
                  <UploadCloud className="size-4" />
                  Importer une nouvelle version
                </Button>
              ) : null}
            </div>
          </header>

          {error ? (
            <Card className="mt-6 border border-[var(--color-error-soft)] bg-[var(--color-error-soft)]/35 p-4">
              <p className="text-sm font-semibold text-[var(--color-error)]">
                Le service d’import est indisponible. Réessayez dans quelques instants.
              </p>
            </Card>
          ) : null}

          {currentWorkflow !== null ? (
            <IngestionProgressDashboard workflow={currentWorkflow} />
          ) : pendingDocumentSource !== null ? (
            <UploadedSourceDashboard
              documentSource={pendingDocumentSource}
              isStarting={startIngestionMutation.isPending}
              errorMessage={startIngestionMutation.error?.message ?? null}
              onReplaceGuide={() => openReuploadDialog(pendingDocumentSource.documentSourceId)}
              onStartIngestion={() => startIngestionMutation.mutate(pendingDocumentSource)}
            />
          ) : activePack === null ? (
            <EmptyStyleGuideDashboard onUploadGuide={openUploadDialog} />
          ) : !isRuntimePackActive ? (
            <IngestionProgressDashboard
              onOpenRulesReview={() => onOpenRulesReview(returnTo ?? undefined)}
              review={{
                rules: overview.rules,
              }}
              workflow={buildCandidateReadyWorkflow(activePack)}
            />
          ) : (
            <>
              <section className="mt-8">
                <Card className="border border-black/6 bg-[linear-gradient(180deg,rgba(255,253,248,0.94),rgba(245,247,242,0.96))] p-6">
                  <div>
                    <Badge tone="success">{packStatusLabel(activePack.status)}</Badge>
                    <h2 className="mt-4 font-serif text-3xl font-semibold tracking-[-0.04em] text-[var(--color-ink)] max-md:text-2xl">
                      Guide actuellement utilisé
                    </h2>
                    <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
                      Les prochaines fiches produit s’appuient sur ce pack. Toute évolution du guide passe par un
                      nouveau cycle d’import, d’analyse et de revue avant de remplacer cette référence.
                    </p>
                  </div>
                </Card>
              </section>

              <section className="mt-6">
                <Card>
                  <div className="mb-5">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                      Historique
                    </p>
                    <CardTitle className="mt-2">Packs récents</CardTitle>
                    <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
                      Les derniers packs produits pour ce guide restent consultables pour comparer les activations et
                      les versions précédentes.
                    </p>
                  </div>
                  <RecentPacksTable
                    packs={overview.recentPacks}
                    onRowClick={() => onOpenRulesReview(returnTo ?? undefined)}
                  />
                </Card>
              </section>

            </>
          )}
        </section>
      </div>

      <UploadGuideDialog
        open={isUploadOpen}
        mode={reuploadDocumentSourceId === null ? "upload" : "reupload"}
        replacedDocumentSourceId={reuploadDocumentSourceId}
        onClose={closeUploadDialog}
        onUploaded={(upload, fileName) => {
          setOptimisticIngestion(null);
          setOptimisticDocumentSource({
            documentSourceId: upload.documentSourceId,
            fileName,
            status: upload.status,
            storageUri: upload.storageUri,
            storageGeneration: upload.storageGeneration,
            storageMetageneration: upload.storageMetageneration,
            uploadedAt: upload.createdAt,
            updatedAt: upload.updatedAt,
          });
        }}
      />
    </main>
  );
}

function UploadedSourceDashboard({
  documentSource,
  isStarting,
  errorMessage,
  onReplaceGuide,
  onStartIngestion,
}: {
  documentSource: PendingDocumentSource;
  isStarting: boolean;
  errorMessage: string | null;
  onReplaceGuide: () => void;
  onStartIngestion: () => void;
}) {
  return (
    <>
      <section className="mt-8">
        <Card className="relative overflow-hidden bg-[linear-gradient(145deg,#fffdf7,#eef2ea)] p-8">
          <div className="absolute -right-20 -top-24 size-72 rounded-full bg-[var(--color-sage-soft)] blur-3xl" />
          <div className="relative grid grid-cols-[minmax(0,1fr)_24rem] items-start gap-8 max-2xl:grid-cols-1">
            <div className="min-w-0">
              <Badge tone="success">PDF importé</Badge>
              <h2 className="mt-4 max-w-2xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Vérifier le guide avant analyse
              </h2>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--color-muted)]">
                Le PDF est importé. L’analyse démarre uniquement après confirmation que ce document est la version
                officielle du guide de style Axolotl.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Button onClick={onStartIngestion} disabled={isStarting}>
                  {isStarting ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <PlayCircle className="size-4" />
                  )}
                  Lancer l’analyse du guide
                </Button>
                <Button variant="secondary" onClick={onReplaceGuide} disabled={isStarting}>
                  Remplacer le PDF
                </Button>
              </div>
              {errorMessage ? (
                <p className="mt-4 text-sm font-semibold text-[var(--color-error)]">{errorMessage}</p>
              ) : null}
            </div>

            <div className="w-full max-w-96 justify-self-end rounded-[1.5rem] bg-white/80 p-5 shadow-[0_16px_40px_rgba(27,28,26,0.07)] max-2xl:max-w-none">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
                Document sélectionné
              </p>
              <div className="mt-4 rounded-[1.35rem] bg-[var(--color-ivory)] p-1.5">
                <div className="grid gap-1.5" role="tablist" aria-label="Document du guide de style">
                  <button
                    type="button"
                    role="tab"
                    aria-selected="true"
                    className="flex min-w-0 items-center gap-3 rounded-[1.05rem] bg-white px-3 py-2.5 text-left text-[var(--color-forest)] shadow-[0_10px_24px_rgba(27,28,26,0.07)]"
                  >
                    <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
                      <FileCheck2 className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.68rem] font-bold uppercase tracking-[0.14em]">
                        PDF 1
                      </span>
                      <span className="block truncate text-sm font-semibold">
                        {documentSource.fileName}
                      </span>
                    </span>
                  </button>
                </div>
              </div>

              <details className="mt-5 rounded-2xl bg-[var(--color-ivory)] px-4 py-3 text-xs text-[var(--color-muted)]">
                <summary className="cursor-pointer font-semibold text-[var(--color-forest)]">
                  Champs document_source
                </summary>
                <dl className="mt-3 grid min-h-[24rem] gap-3">
                  <div>
                    <dt className="truncate font-semibold text-[var(--color-ink)]">
                      {documentSource.fileName}
                    </dt>
                    <dd className="mt-1 min-h-5 break-all leading-5">{documentSource.documentSourceId}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-[var(--color-ink)]">storage_uri</dt>
                    <dd className="mt-1 min-h-20 break-all leading-5">{documentSource.storageUri}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-[var(--color-ink)]">storage_generation</dt>
                    <dd className="mt-1 min-h-5 break-all leading-5">{formatNullable(documentSource.storageGeneration)}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-[var(--color-ink)]">storage_metageneration</dt>
                    <dd className="mt-1 min-h-5 break-all leading-5">{formatNullable(documentSource.storageMetageneration)}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold text-[var(--color-ink)]">created_at</dt>
                    <dd className="mt-1 min-h-5 leading-5">
                      {formatAdminDateTime(documentSource.uploadedAt)}
                    </dd>
                  </div>
                  {documentSource.updatedAt ? (
                    <div>
                      <dt className="font-semibold text-[var(--color-ink)]">updated_at</dt>
                      <dd className="mt-1 min-h-5 leading-5">
                        {formatAdminDateTime(documentSource.updatedAt)}
                      </dd>
                    </div>
                  ) : null}
                </dl>
              </details>
            </div>
          </div>
        </Card>
      </section>

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Vérification du guide
          </p>
          <CardTitle className="mt-2 text-xl">Confirmer le document source</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            Aucun traitement automatique n’a encore démarré. Cette étape permet de confirmer que le bon document sera
            transformé en règles de style.
          </p>

          <ol className="mt-6 space-y-4">
            <OnboardingStep
              icon={CheckCircle2}
              title="Version officielle"
              description="Le PDF correspond à la version validée du guide de style Axolotl."
            />
            <OnboardingStep
              icon={FileCheck2}
              title="Contenu exploitable"
              description="Le document contient la voix de marque, les tons, le lexique et les formulations interdites."
            />
            <OnboardingStep
              icon={ShieldCheck}
              title="Source de référence"
              description="Le PDF servira de source au pack candidat soumis à revue."
            />
          </ol>
        </Card>
      </section>
    </>
  );
}

function IngestionProgressDashboard({
  onOpenRulesReview,
  review,
  workflow,
}: {
  onOpenRulesReview?: () => void;
  review?: {
    rules: StyleRule[];
  };
  workflow: CurrentWorkflow;
}) {
  const isReviewReady = review !== undefined;
  const totalRules = review?.rules.length ?? 0;
  const reviewSummaryLabel = totalRules <= 1 ? `${totalRules} règle` : `${totalRules} règles`;

  return (
    <>
      <section className="mt-8">
        <Card className="relative overflow-hidden bg-[linear-gradient(135deg,#173124,#2d4739)] p-8 text-white">
          <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[#cde5d3]/18 blur-3xl" />
          <div className="relative max-w-3xl">
            <div>
              <Badge className="bg-white/15 text-white">Analyse en cours</Badge>
              <h2 className="mt-4 font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
                Analyse du guide en cours
              </h2>
              <p className="mt-5 max-w-xl text-sm leading-7 text-white/76">
                Le contenu du guide est analysé pour préparer le pack candidat à relire.
              </p>
            </div>
          </div>
        </Card>
      </section>

      <section className="mt-6">
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                Suivi de l’analyse
              </p>
              <CardTitle className="mt-2">Étapes du guide de style</CardTitle>
            </div>
            <Clock3 className="size-6 text-[var(--color-muted)]" />
          </div>

          <ol className="mt-7 space-y-4" aria-label="Étapes d’analyse du guide de style">
            {workflow.steps.map((step) => {
              const isReviewStepReady = isReviewReady && step.id === "editorial-review";
              const canOpenReview = isReviewStepReady && onOpenRulesReview !== undefined;
              const isRunningStep = step.status === "running" && !isReviewStepReady;
              const stepMetadata = metadataFieldsForWorkflowStep(step.id, workflow.metadata);

              return (
                <li
                  key={step.id}
                  className={cn(
                    "grid grid-cols-[42px_1fr] gap-4",
                    isReviewStepReady &&
                      "rounded-[1.5rem] border border-[var(--color-gold)]/25 bg-[linear-gradient(135deg,rgba(243,225,166,0.24),rgba(255,255,255,0.76))] px-4 py-4 shadow-[0_16px_32px_rgba(77,58,16,0.08)]",
                  )}
                >
                  <span
                    className={cn(
                      "mt-1 grid size-10 place-items-center rounded-2xl",
                      step.status === "completed" && "bg-[var(--color-sage-soft)] text-[var(--color-forest)]",
                      step.status === "running" && !isReviewStepReady && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
                      step.status === "pending" && !isReviewStepReady && "bg-[var(--color-stone)] text-[var(--color-muted)]",
                      step.status === "failed" && "bg-[var(--color-error-soft)] text-[var(--color-error)]",
                      isReviewStepReady && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
                    )}
                    aria-current={step.status === "running" || isReviewStepReady ? "step" : undefined}
                  >
                    {step.status === "running" && !isReviewStepReady ? (
                      <Loader2 className="size-5 animate-spin" />
                    ) : isReviewStepReady ? (
                      <ShieldCheck className="size-5" />
                    ) : (
                      <CheckCircle2 className="size-5" />
                    )}
                  </span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-[var(--color-ink)]">{step.label}</p>
                      <Badge tone={isReviewStepReady ? "warning" : stepStatusTone(step.status)}>
                        {isReviewStepReady ? "Prêt à relire" : stepStatusLabel(step.status)}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-[var(--color-muted)]">{step.description}</p>
                    <StepMetadata fields={stepMetadata} />
                    {canOpenReview ? (
                      <div className="mt-3 flex flex-wrap items-center gap-3">
                        <span className="rounded-full bg-white/82 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-[var(--color-teak)] shadow-[inset_0_0_0_1px_rgba(212,178,84,0.18)]">
                          {reviewSummaryLabel}
                        </span>
                        <Button size="sm" onClick={onOpenRulesReview}>
                          Relire maintenant
                          <ArrowRight className="size-4" />
                        </Button>
                      </div>
                    ) : null}
                    {step.eta && !isReviewStepReady ? (
                      <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs leading-5 text-[var(--color-muted)]">
                        <span>{step.eta}</span>
                        {isRunningStep ? (
                          <span className="inline-flex items-center gap-1.5">
                            <span aria-hidden="true">·</span>
                            <Clock3 className="size-3.5" />
                            <span>{formatWorkflowElapsedTime(workflow.elapsedTime)}</span>
                          </span>
                        ) : null}
                      </p>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ol>
        </Card>
      </section>
    </>
  );
}

function StepMetadata({ fields }: { fields: ExecutionMetadata["documentAi"] }) {
  if (fields.length === 0) {
    return null;
  }

  return (
    <details className="group mt-2 w-full max-w-2xl">
      <summary className="flex w-44 cursor-pointer list-none items-center gap-2 py-1 text-[0.72rem] font-bold uppercase tracking-[0.14em] text-[var(--color-teak)] transition-colors hover:text-[var(--color-forest)] [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden="true"
          className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open:rotate-90"
        />
        Détails techniques
      </summary>
      <dl className="mt-2 grid w-full grid-cols-2 gap-2 rounded-2xl bg-white/70 p-3 text-xs shadow-[inset_0_0_0_1px_rgba(23,49,36,0.08)] max-sm:grid-cols-1">
        {fields.map((field) => (
          <MetadataField key={field.label} label={field.label} value={field.value} />
        ))}
      </dl>
    </details>
  );
}

function MetadataField({ label, value }: { label: string; value: string }) {
  const { primary, secondary } = splitMetadataValue(value);

  return (
    <div className="min-w-0 rounded-xl bg-[var(--color-ivory)]/80 px-3 py-2">
      <dt className="text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
        {label}
      </dt>
      <dd className="mt-1 font-semibold leading-5 text-[var(--color-forest)]" title={value}>
        <span className={cn("block", secondary ? "whitespace-nowrap" : "break-words")}>
          {primary}
        </span>
        {secondary ? (
          <span className="mt-0.5 block text-[0.68rem] font-bold text-[var(--color-muted)]">
            {secondary}
          </span>
        ) : null}
      </dd>
    </div>
  );
}

function splitMetadataValue(value: string): { primary: string; secondary: string | null } {
  const match = value.match(/^(.*)\s(\(Gemini 3\.0 Flash\))$/);
  if (!match) {
    return { primary: value, secondary: null };
  }

  return { primary: match[1], secondary: match[2] };
}

function metadataFieldsForWorkflowStep(stepId: string, metadata: ExecutionMetadata) {
  if (stepId === "document-ai") {
    return metadata.documentAi;
  }

  if (stepId === "draft-pack") {
    return metadata.llm;
  }

  return [];
}

function EmptyStyleGuideDashboard({ onUploadGuide }: { onUploadGuide: () => void }) {
  return (
    <>
      <section className="mt-8">
        <Card className="relative min-h-[20rem] overflow-hidden bg-[linear-gradient(150deg,#173124_10%,#2f4f40_100%)] p-8 text-white">
          <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[#cde5d3]/18 blur-3xl" />
          <div className="relative max-w-3xl">
            <Badge className="bg-white/15 text-white">Aucun guide importé</Badge>
            <h2 className="mt-4 font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
              Importer le guide de style officiel
            </h2>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-white/76">
              Importez le guide officiel pour créer un pack de style approuvé avant toute génération avec la voix de
              marque Axolotl.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button
                className="h-11 rounded-full border border-white/55 bg-white/12 px-6 py-3 font-semibold !text-white hover:bg-white/18 hover:!text-white"
                onClick={onUploadGuide}
                aria-label="Importer le guide de style PDF"
              >
                <UploadCloud className="size-4" />
                Importer le guide de style (PDF)
              </Button>
            </div>
          </div>
        </Card>
      </section>

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Parcours du guide de style
          </p>
          <CardTitle className="mt-2 text-xl">De l’import à l’activation</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            Le PDF devient un pack de style seulement après import, vérification, analyse et revue éditoriale.
          </p>

          <ol className="mt-6 space-y-4">
            <OnboardingStep
              icon={UploadCloud}
              title="1. Importer le PDF"
              description="Le fichier devient le document source. Aucun traitement automatique ne démarre à cette étape."
            />
            <OnboardingStep
              icon={FileCheck2}
              title="2. Vérifier la source"
              description="Le PDF peut être confirmé ou remplacé avant l’analyse du guide."
            />
            <OnboardingStep
              icon={Sparkles}
              title="3. Analyser le guide"
              description="Le contenu du guide est extrait, puis transformé en pack candidat."
            />
            <OnboardingStep
              icon={ShieldCheck}
              title="4. Relire les règles"
              description="Les règles proposées sont corrigées, écartées ou approuvées avant activation."
            />
          </ol>
        </Card>
      </section>
    </>
  );
}

function OnboardingStep({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Sparkles;
  title: string;
  description: string;
}) {
  return (
    <li className="grid grid-cols-[42px_1fr] gap-4">
      <span className="grid size-10 place-items-center rounded-2xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
        <Icon className="size-5" />
      </span>
      <div>
        <p className="font-semibold text-[var(--color-ink)]">{title}</p>
        <p className="mt-1 text-sm leading-6 text-[var(--color-muted)]">{description}</p>
      </div>
    </li>
  );
}

function buildOptimisticWorkflow(started: StyleGuideStartIngestionResponse): CurrentWorkflow {
  return {
    workflowId: started.workflowId,
    documentSourceId: started.documentSourceId,
    ingestionRunId: started.ingestionRunId,
    status: "RUNNING",
    currentActivity: "Extraction du contenu",
    elapsedTime: "moins d’une minute",
    progress: 35,
    metadata: {
      documentAi: [],
      llm: [],
    },
    steps: [
      {
        id: "document-ai",
        label: "Extraction du contenu",
        description: "Le contenu du PDF est analysé et structuré pour préparer les règles.",
        status: "running",
        eta: "souvent 1 min",
      },
      {
        id: "draft-pack",
        label: "Pack candidat",
        description: "Les règles de voix, de ton et de formulation sont préparées pour la revue.",
        status: "pending",
        eta: "souvent 15 secondes",
      },
      {
        id: "editorial-review",
        label: "Revue éditoriale",
        description: "Les règles proposées sont relues, corrigées ou approuvées.",
        status: "pending",
      },
    ],
  };
}

function buildCandidateReadyWorkflow(
  pack: NonNullable<StyleGuideOverview["activePack"]>,
): CurrentWorkflow {
  return {
    workflowId: `style-guide-review-${pack.version}`,
    documentSourceId: pack.version,
    ingestionRunId: `review-${pack.version}`,
    status: "WAITING_FOR_REVIEW",
    currentActivity: "Revue éditoriale",
    elapsedTime: "analyse terminée",
    progress: 100,
    metadata: pack.metadata,
    steps: [
      {
        id: "document-ai",
        label: "Extraction du contenu",
        description: "Le contenu du PDF a été analysé et structuré pour préparer les règles.",
        status: "completed",
      },
      {
        id: "draft-pack",
        label: "Pack candidat",
        description: "Les règles de voix, de ton et de formulation sont prêtes.",
        status: "completed",
      },
      {
        id: "editorial-review",
        label: "Revue éditoriale",
        description: "Les règles proposées peuvent maintenant être relues et approuvées.",
        status: "running",
      },
    ],
  };
}

function resolveStyleGuideFlowProgress({
  activePack,
  currentWorkflow,
  isRuntimePackActive,
  pendingDocumentSource,
}: {
  activePack: StyleGuideOverview["activePack"];
  currentWorkflow: StyleGuideOverview["currentWorkflow"];
  isRuntimePackActive: boolean;
  pendingDocumentSource: StyleGuideOverview["pendingDocumentSource"];
}): { currentStep: "upload" | "verify" | "analyze" | "review"; mode?: "current" | "next" } {
  if (currentWorkflow !== null) {
    return { currentStep: "analyze" };
  }
  if (pendingDocumentSource !== null) {
    return { currentStep: "verify" };
  }
  if (activePack !== null) {
    return isRuntimePackActive ? { currentStep: "review" } : { currentStep: "analyze" };
  }
  return { currentStep: "upload" };
}

function packStatusLabel(status: NonNullable<StyleGuideOverview["activePack"]>["status"]) {
  if (status === "ACTIF") {
    return "Actif";
  }
  if (status === "ARCHIVE") {
    return "Archivé";
  }
  return "À relire";
}

function formatWorkflowElapsedTime(value: string) {
  const secondsOnlyMatch = value.match(/^(\d+)\s*s$/);
  if (secondsOnlyMatch === null) {
    return value;
  }

  const elapsedSeconds = Number(secondsOnlyMatch[1]);
  if (!Number.isFinite(elapsedSeconds) || elapsedSeconds < 60) {
    return value;
  }

  if (elapsedSeconds < 3600) {
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    if (seconds === 0) {
      return `${minutes} min`;
    }
    return `${minutes} min ${seconds.toString().padStart(2, "0")} s`;
  }

  const hours = Math.floor(elapsedSeconds / 3600);
  const minutes = Math.floor((elapsedSeconds % 3600) / 60);
  if (minutes === 0) {
    return `${hours} h`;
  }
  return `${hours} h ${minutes.toString().padStart(2, "0")} min`;
}

function formatNullable(value: string | null) {
  return value && value.length > 0 ? value : "Non renseigné";
}

function sanitizeReturnTo(value: string | null) {
  if (value !== null && value.startsWith("/product-sheets/") && !value.startsWith("//")) {
    return value;
  }

  return null;
}

function buildStyleGuideSearchParams(
  returnTo: string | null,
  values: Record<string, string> = {},
) {
  return returnTo === null ? values : { ...values, returnTo };
}

function stepStatusLabel(status: CurrentWorkflow["steps"][number]["status"]) {
  if (status === "completed") {
    return "Terminé";
  }
  if (status === "running") {
    return "En cours";
  }
  if (status === "failed") {
    return "Erreur";
  }
  return "À venir";
}

function stepStatusTone(status: CurrentWorkflow["steps"][number]["status"]) {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running") {
    return "warning";
  }
  return "neutral";
}
