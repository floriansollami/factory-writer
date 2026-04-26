import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileCheck2,
  FileText,
  Loader2,
  PlayCircle,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { type ReactNode, useCallback, useEffect, useState } from "react";

import { AxolotlLogo } from "@/components/brand/AxolotlLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ProductSheetFlowProgress } from "@/features/product-sheets/ProductSheetFlowProgress";
import {
  ResolveTechnicalReviewCaseDialog,
  TechnicalReviewCasesPanel,
} from "@/features/product-sheets/TechnicalReviewCasesPanel";
import { TechnicalSourcesUploadDialog } from "@/features/product-sheets/TechnicalSourcesUploadDialog";
import {
  loadTechnicalSourcePdf,
  loadTechnicalSourcePdfByFileName,
} from "@/features/product-sheets/technicalSourcePdfStore";
import type {
  TechnicalFactCandidate,
  TechnicalClassification,
  ProductOverview,
  ProductSheet,
  TechnicalRun,
  TechnicalReviewCase,
  TechnicalSource,
} from "@/features/product-sheets/schema";
import {
  formatCode,
  formatNullableCode,
  isProductAnalysisActive,
  resolveProductFlowStep,
  technicalFactFieldLabel,
  technicalDocumentTypeLabel,
} from "@/features/product-sheets/productSheetUtils";
import { SourcePdfPreview } from "@/features/style-guide/SourcePdfDialog";
import { getProductOverview, listProducts, startTechnicalIngestion } from "@/lib/api";
import { formatAdminDateTime } from "@/lib/dateTime";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil",
  "Fiches produit",
  "Guide de style",
  "Paramètres",
];
const navigableNavItems = new Set([
  "Accueil",
  "Fiches produit",
  "Guide de style",
  "Paramètres",
]);

type ProductSheetDetailPageProps = {
  onBack: () => void;
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
  onOpenSettings: () => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  productId: string;
};

export function ProductSheetDetailPage({
  onBack,
  onOpenAdminHome,
  onOpenProductSheets,
  onOpenSettings,
  onOpenStyleGuide,
  productId,
}: ProductSheetDetailPageProps) {
  const [isUploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [uploadDialogMode, setUploadDialogMode] = useState<"upload" | "replace-lot">(
    "upload",
  );
  const queryClient = useQueryClient();
  const { data, error, isPending } = useQuery({
    queryKey: ["product-overview", productId],
    queryFn: () => getProductOverview(productId),
    refetchInterval: (query) => {
      const overview = query.state.data;

      return overview !== undefined && isProductAnalysisActive(overview.run) ? 3000 : false;
    },
    retry: false,
  });
  const { data: productsData } = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    retry: false,
  });
  const listedProduct =
    productsData?.products.find((product) => product.id === productId) ?? null;
  const startMutation = useMutation({
    mutationFn: () => startTechnicalIngestion(productId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["products"] }),
        queryClient.invalidateQueries({ queryKey: ["product-overview", productId] }),
      ]);
    },
  });

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
                    item === "Fiches produit" &&
                      "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={
                    item === "Accueil"
                      ? onOpenAdminHome
                      : item === "Guide de style"
                        ? () => onOpenStyleGuide()
                        : item === "Fiches produit"
                          ? onOpenProductSheets
                          : item === "Paramètres"
                            ? onOpenSettings
                          : undefined
                  }
                >
                  {item}
                  {navigableNavItems.has(item) && item !== "Fiches produit" ? (
                    <ArrowRight className="size-4" />
                  ) : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          {isPending ? (
            <LoadingState onBack={onBack} />
          ) : error || data === undefined ? (
            <ErrorState error={error} onBack={onBack} />
          ) : (
            <ProductDetailWorkspace
              isStartingIngestion={startMutation.isPending}
              onBack={onBack}
              onImportSources={() => {
                setUploadDialogMode("upload");
                setUploadDialogOpen(true);
              }}
              onOpenStyleGuide={onOpenStyleGuide}
              onReplaceSources={() => {
                setUploadDialogMode("replace-lot");
                setUploadDialogOpen(true);
              }}
              onStartIngestion={() => startMutation.mutate()}
              overview={data}
              product={listedProduct}
              startError={startMutation.error}
            />
          )}
        </section>
      </div>

      <TechnicalSourcesUploadDialog
        mode={uploadDialogMode}
        open={isUploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        productId={productId}
      />
    </main>
  );
}

function ProductDetailWorkspace({
  isStartingIngestion,
  onBack,
  onImportSources,
  onOpenStyleGuide,
  onReplaceSources,
  onStartIngestion,
  overview,
  product,
  startError,
}: {
  isStartingIngestion: boolean;
  onBack: () => void;
  onImportSources: () => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  onReplaceSources: () => void;
  onStartIngestion: () => void;
  overview: ProductOverview;
  product: ProductSheet | null;
  startError: Error | null;
}) {
  const currentStep = resolveProductFlowStep(overview);
  const returnTo = `/product-sheets/${overview.product.id}`;
  const hasStyleGuide = product?.styleGuideReady ?? true;
  const hasCommercialSignals = product?.commercialSignalsReady ?? true;

  return (
    <>
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft className="size-4" />
            Fiches produit
          </Button>
          <p className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
            Fiche produit
          </p>
          <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
            {overview.product.name}
          </h1>
          <ProductSheetFlowProgress className="mt-3" currentStep={currentStep} />
        </div>
        <div className="flex flex-wrap gap-3">
          {!hasStyleGuide ? (
            <Button variant="secondary" onClick={() => onOpenStyleGuide(returnTo)}>
              Importer le guide de style
            </Button>
          ) : null}
        </div>
      </header>

      {startError ? (
        <Card className="mt-5 border border-[var(--color-error-soft)] bg-[var(--color-error-soft)]/35 p-4">
          <p className="text-sm font-semibold text-[var(--color-error)]">
            {startError.message}
          </p>
        </Card>
      ) : null}

      <ProductDetailStage
        hasCommercialSignals={hasCommercialSignals}
        hasStyleGuide={hasStyleGuide}
        isStartingIngestion={isStartingIngestion}
        onImportSources={onImportSources}
        onOpenStyleGuide={() => onOpenStyleGuide(returnTo)}
        onReplaceSources={onReplaceSources}
        onStartIngestion={onStartIngestion}
        overview={overview}
      />
    </>
  );
}

function ProductDetailStage({
  hasCommercialSignals,
  hasStyleGuide,
  isStartingIngestion,
  onImportSources,
  onOpenStyleGuide,
  onReplaceSources,
  onStartIngestion,
  overview,
}: {
  hasCommercialSignals: boolean;
  hasStyleGuide: boolean;
  isStartingIngestion: boolean;
  onImportSources: () => void;
  onOpenStyleGuide: () => void;
  onReplaceSources: () => void;
  onStartIngestion: () => void;
  overview: ProductOverview;
}) {
  const hasOpenReviewCases = overview.review_cases.some(
    (reviewCase) => reviewCase.status === "A_TRAITER",
  );

  if (!hasStyleGuide) {
    return <StyleGuideRequiredDashboard onOpenStyleGuide={onOpenStyleGuide} />;
  }

  if (overview.sources.length === 0) {
    return <TechnicalSourcesEmptyDashboard onImportSources={onImportSources} />;
  }

  if (overview.run === null) {
    return (
      <TechnicalSourcesReadyDashboard
        isStartingIngestion={isStartingIngestion}
        onImportSources={onImportSources}
        onStartIngestion={onStartIngestion}
        overview={overview}
      />
    );
  }

  if (overview.run.statut === "ERREUR") {
    return <TechnicalAnalysisFailedDashboard overview={overview} />;
  }

  if (isProductAnalysisActive(overview.run)) {
    return (
      <TechnicalAnalysisDashboard
        onReplaceSources={onReplaceSources}
        overview={overview}
      />
    );
  }

  if (hasOpenReviewCases) {
    return <TechnicalReviewDashboard overview={overview} />;
  }

  if (!hasCommercialSignals) {
    return <CommercialSignalsWaitingDashboard overview={overview} />;
  }

  if (overview.product_context_snapshot !== null) {
    return <GenerationReadyDashboard overview={overview} />;
  }

  return <ContextPreparingDashboard overview={overview} />;
}

function StyleGuideRequiredDashboard({ onOpenStyleGuide }: { onOpenStyleGuide: () => void }) {
  return (
    <>
      <ProductStageHero
        badge="Guide manquant"
        title="Importer le guide de style officiel"
        description="Le guide est une référence globale. Importez-le une fois, puis revenez à cette fiche pour ajouter les dossiers techniques."
        action={
          <Button
            className="h-11 rounded-full border border-white/55 bg-white/12 px-6 py-3 font-semibold !text-white hover:bg-white/18 hover:!text-white"
            onClick={onOpenStyleGuide}
          >
            Importer le guide de style
            <ArrowRight className="size-4" />
          </Button>
        }
      />

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Étape globale
          </p>
          <CardTitle className="mt-2 text-xl">Même logique que le guide de style</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            La fiche produit ne demande pas de choisir le style à chaque fois. Elle utilise automatiquement le pack actif.
          </p>
          <ol className="mt-6 space-y-4">
            <OnboardingStep
              icon={UploadCloud}
              title="1. Importer le PDF du guide"
              description="Le document de marque reste géré dans l’onglet Guide de style."
            />
            <OnboardingStep
              icon={ShieldCheck}
              title="2. Relire et activer le pack"
              description="Les règles doivent être validées avant d’être utilisées par les fiches produit."
            />
            <OnboardingStep
              icon={ArrowRight}
              title="3. Revenir à cette fiche"
              description="Une fois le guide actif, l’action suivante sera l’import des dossiers techniques."
            />
          </ol>
        </Card>
      </section>
    </>
  );
}

function TechnicalSourcesEmptyDashboard({ onImportSources }: { onImportSources: () => void }) {
  return (
    <>
      <ProductStageHero
        badge="Dossiers attendus"
        title="Importer les dossiers techniques du produit"
        description="Ajoutez les PDFs usine, dimensions, matériaux ou certifications. Aucun traitement ne démarre tant que vous n’avez pas confirmé l’analyse."
        action={
          <Button
            className="h-11 rounded-full border border-white/55 bg-white/12 px-6 py-3 font-semibold !text-white hover:bg-white/18 hover:!text-white"
            onClick={onImportSources}
          >
            <UploadCloud className="size-4" />
            Importer les dossiers techniques
          </Button>
        }
      />

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Parcours des dossiers techniques
          </p>
          <CardTitle className="mt-2 text-xl">De l’import à la génération</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            Le produit avance écran par écran, comme le guide de style : import, confirmation, analyse, contrôle, puis génération.
          </p>
          <ol className="mt-6 space-y-4">
            <OnboardingStep
              icon={UploadCloud}
              title="1. Importer les PDFs"
              description="Fiches techniques, notices, dimensions, matériaux ou certifications."
            />
            <OnboardingStep
              icon={FileText}
              title="2. Vérifier les fichiers"
              description="Les documents importés restent visibles avant de lancer l’analyse."
            />
            <OnboardingStep
              icon={Sparkles}
              title="3. Extraire les faits"
              description="L’analyse prépare les informations techniques nécessaires à la fiche."
            />
            <OnboardingStep
              icon={ShieldCheck}
              title="4. Corriger si besoin"
              description="Les points ambigus sont traités avant d’assembler le contexte produit."
            />
          </ol>
        </Card>
      </section>
    </>
  );
}

function TechnicalSourcesReadyDashboard({
  isStartingIngestion,
  onImportSources,
  onStartIngestion,
  overview,
}: {
  isStartingIngestion: boolean;
  onImportSources: () => void;
  onStartIngestion: () => void;
  overview: ProductOverview;
}) {
  return (
    <>
      <section className="mt-8">
        <Card className="relative overflow-hidden bg-[linear-gradient(145deg,#fffdf7,#eef2ea)] p-8">
          <div className="absolute -right-20 -top-24 size-72 rounded-full bg-[var(--color-sage-soft)] blur-3xl" />
          <div className="relative grid grid-cols-[minmax(0,0.85fr)_minmax(38rem,1fr)] items-start gap-8 max-xl:grid-cols-1">
            <div className="min-w-0">
              <Badge tone="success">PDFs importés</Badge>
              <h2 className="mt-4 max-w-2xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Vérifier les dossiers avant analyse
              </h2>
              <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--color-muted)]">
                Les fichiers sont bien attachés à ce produit. Lancez l’analyse uniquement si ces documents correspondent à la bonne version technique.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Button onClick={onStartIngestion} disabled={isStartingIngestion}>
                  {isStartingIngestion ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <PlayCircle className="size-4" />
                  )}
                  Lancer l’analyse technique
                </Button>
                <Button variant="secondary" onClick={onImportSources} disabled={isStartingIngestion}>
                  Remplacer les PDFs
                </Button>
              </div>
            </div>

            <SourcesSummaryCard overview={overview} />
          </div>
        </Card>
      </section>

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Vérification produit
          </p>
          <CardTitle className="mt-2 text-xl">Confirmer les documents source</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            Cette étape évite de lancer une analyse sur le mauvais PDF ou une ancienne version de dossier technique.
          </p>

          <ol className="mt-6 space-y-4">
            <OnboardingStep
              icon={CheckCircle2}
              title="Produit correct"
              description="Les PDFs correspondent bien au SKU affiché en haut de page."
            />
            <OnboardingStep
              icon={FileText}
              title="Documents exploitables"
              description="Les fichiers contiennent les dimensions, matériaux, usages, contraintes ou certifications."
            />
            <OnboardingStep
              icon={Sparkles}
              title="Analyse contrôlée"
              description="L’extraction démarre seulement après cette confirmation."
            />
          </ol>
        </Card>
      </section>
    </>
  );
}

function TechnicalAnalysisDashboard({
  onReplaceSources,
  overview,
}: {
  onReplaceSources: () => void;
  overview: ProductOverview;
}) {
  const steps = buildTechnicalAnalysisSteps(overview);
  const now = useProductAnalysisNow(isProductAnalysisActive(overview.run));
  const elapsedTime = formatTechnicalRunElapsedTime(overview.run, now);
  const blockingClassifications = overview.technical_classifications.filter(
    (classification) => classification.is_blocking,
  );
  const hasBlockingClassifications = blockingClassifications.length > 0;

  return (
    <>
      <ProductStageHero
        badge="Analyse en cours"
        title="Analyse des dossiers en cours"
        description="Les documents sont lus et contrôlés. Les étapes détaillent l’avancement de l’analyse technique."
      />

      <section className="mt-6">
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                Suivi de l’analyse
              </p>
              <CardTitle className="mt-2">Étapes des dossiers techniques</CardTitle>
            </div>
            <Clock3 className="size-6 text-[var(--color-muted)]" />
          </div>

          <ol className="mt-7 space-y-4" aria-label="Étapes d’analyse des dossiers techniques">
            {steps.map((step) => (
              <ProductAnalysisStepItem
                key={step.id}
                classificationResults={
                  step.id === "document-classification" &&
                  overview.technical_classifications.length > 0
                    ? overview.technical_classifications
                    : undefined
                }
                defaultOpenClassificationResults={false}
                elapsedTime={elapsedTime}
                extractionResults={
                  step.id === "fact-extraction" && overview.fact_candidates.length > 0
                    ? overview.fact_candidates
                    : undefined
                }
                extractionSources={overview.sources}
                generationReadiness={
                  step.id === "deterministic-validation"
                    ? overview.generation_readiness
                    : undefined
                }
                productId={overview.product.id}
                validationReviewCases={
                  step.id === "deterministic-validation"
                    ? overview.review_cases.filter(
                        (reviewCase) => reviewCase.case_type !== "CLASSIFICATION_UNCERTAIN",
                      )
                    : []
                }
                hideStepMetadata={
                  step.id === "document-classification" ||
                  (step.id === "fact-extraction" && overview.fact_candidates.length > 0)
                }
                onReplaceSources={
                  step.id === "document-classification" && hasBlockingClassifications
                    ? onReplaceSources
                    : undefined
                }
                step={step}
              />
            ))}
          </ol>
        </Card>
      </section>
    </>
  );
}

function TechnicalAnalysisFailedDashboard({ overview }: { overview: ProductOverview }) {
  return (
    <>
      <ProductStageHero
        badge="Analyse arrêtée"
        title="L’analyse technique a échoué"
        description="Le workflow s’est arrêté avant de préparer le contexte produit. Consultez les logs backend pour identifier la cause."
      />

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <SourcesSummaryCard overview={overview} />
        <FactsCard overview={overview} />
      </section>
    </>
  );
}

function TechnicalReviewDashboard({ overview }: { overview: ProductOverview }) {
  return (
    <>
      <ProductStageHero
        badge="Contrôle requis"
        title="Corriger les points techniques bloquants"
        description="Certaines informations détectées demandent une décision humaine avant d’assembler le contexte produit."
      />

      <section className="mt-6 grid grid-cols-[1fr] gap-6">
        <TechnicalReviewCasesPanel
          productId={overview.product.id}
          reviewCases={overview.review_cases}
        />
        {overview.generation_readiness ? (
          <GenerationReadinessSummary generationReadiness={overview.generation_readiness} />
        ) : null}
      </section>
    </>
  );
}

function CommercialSignalsWaitingDashboard({ overview }: { overview: ProductOverview }) {
  return (
    <>
      <ProductStageHero
        badge="Signaux manquants"
        title="En attente des signaux commerciaux compatibles"
        description="Les faits techniques sont prêts. Le contexte final attend automatiquement un snapshot ventes et retours correspondant à la famille, la saison et le segment du produit."
      />

      <section className="mt-6 grid grid-cols-[1.15fr_0.85fr] gap-6 max-2xl:grid-cols-1">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-muted)]">
            Attente backend
          </p>
          <CardTitle className="mt-2 text-xl">Aucune action produit à faire</CardTitle>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
            Dès qu’un snapshot compatible est disponible en base, le workflow peut reprendre sans réimporter les dossiers techniques.
          </p>
          <dl className="mt-6 grid gap-3 text-sm">
            <ProductCriteriaRow label="Famille" value={formatCode(overview.product.famille_code)} />
            <ProductCriteriaRow label="Saison" value={formatNullableCode(overview.product.season_code)} />
            <ProductCriteriaRow label="Segment" value={formatNullableCode(overview.product.segment_prix_code)} />
          </dl>
        </Card>
        <FactsCard overview={overview} />
      </section>
    </>
  );
}

function ContextPreparingDashboard({ overview }: { overview: ProductOverview }) {
  return (
    <>
      <ProductStageHero
        badge="Contexte en préparation"
        title="Assemblage du contexte produit"
        description="Les faits techniques sont disponibles. Le backend assemble maintenant les données nécessaires à la future génération."
      />

      <section className="mt-6">
        <FactsCard overview={overview} />
      </section>
    </>
  );
}

function GenerationReadyDashboard({ overview }: { overview: ProductOverview }) {
  return (
    <>
      <ProductStageHero
        badge="Contexte prêt"
        title="La fiche est prête pour la génération"
        description="Le contexte produit est assemblé avec les faits techniques, le guide de style actif et les signaux commerciaux compatibles."
      />
      <GenerationCard overview={overview} />
    </>
  );
}

function ProductStageHero({
  action,
  badge,
  description,
  title,
}: {
  action?: ReactNode;
  badge: string;
  description: string;
  title: string;
}) {
  return (
    <section className="mt-8">
      <Card className="relative overflow-hidden bg-[linear-gradient(135deg,#173124,#2d4739)] p-8 text-white">
        <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[#cde5d3]/18 blur-3xl" />
        <div className="relative max-w-3xl">
          <Badge className="bg-white/15 text-white">{badge}</Badge>
          <h2 className="mt-4 font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
            {title}
          </h2>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-white/76">{description}</p>
          {action ? <div className="mt-8 flex flex-wrap gap-3">{action}</div> : null}
        </div>
      </Card>
    </section>
  );
}

function SourcesSummaryCard({ overview }: { overview: ProductOverview }) {
  const sources = dedupeTechnicalSources(overview.sources);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(
    sources[0]?.id ?? null,
  );
  const selectedSource =
    sources.find((source) => source.id === selectedSourceId) ?? sources[0] ?? null;

  return (
    <div className="w-full max-w-[42rem] justify-self-end rounded-[1.5rem] bg-white/80 p-5 shadow-[0_16px_40px_rgba(27,28,26,0.07)] max-xl:max-w-none">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
        Documents sélectionnés
      </p>
      <div className="mt-4 grid grid-cols-[minmax(13rem,0.82fr)_minmax(16rem,1fr)] items-start gap-4 max-lg:grid-cols-1">
        <div className="rounded-[1.35rem] bg-[var(--color-ivory)] p-1.5">
          <div className="grid gap-1.5" role="tablist" aria-label="Documents techniques">
            {sources.map((source, index) => {
              const isSelected = selectedSource?.id === source.id;

              return (
                <button
                  key={source.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className={cn(
                    "flex min-w-0 items-center gap-3 rounded-[1.05rem] px-3 py-2.5 text-left transition",
                    isSelected
                      ? "bg-white text-[var(--color-forest)] shadow-[0_10px_24px_rgba(27,28,26,0.07)]"
                      : "text-[var(--color-muted)] hover:bg-white/55 hover:text-[var(--color-ink)]",
                  )}
                  onClick={() => setSelectedSourceId(source.id)}
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
                    <FileCheck2 className="size-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[0.68rem] font-bold uppercase tracking-[0.14em]">
                      PDF {index + 1}
                    </span>
                    <span className="block truncate text-sm font-semibold">
                      {source.original_file_name}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {selectedSource ? (
          <details className="rounded-2xl bg-[var(--color-ivory)] px-4 py-3 text-xs text-[var(--color-muted)]">
            <summary className="cursor-pointer font-semibold text-[var(--color-forest)]">
              Champs document_source
            </summary>
            <div className="mt-3 min-h-[24rem]">
              <dl className="grid gap-3">
                <div>
                  <dt className="truncate font-semibold text-[var(--color-ink)]">
                    {selectedSource.original_file_name}
                  </dt>
                  <dd className="mt-1 min-h-5 break-all leading-5">{selectedSource.id}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-[var(--color-ink)]">storage_uri</dt>
                  <dd className="mt-1 min-h-20 break-all leading-5">
                    {selectedSource.storage_uri}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-[var(--color-ink)]">storage_generation</dt>
                  <dd className="mt-1 min-h-5 break-all leading-5">
                    {formatNullable(selectedSource.storage_generation)}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-[var(--color-ink)]">storage_metageneration</dt>
                  <dd className="mt-1 min-h-5 break-all leading-5">
                    {formatNullable(selectedSource.storage_metageneration)}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-[var(--color-ink)]">created_at</dt>
                  <dd className="mt-1 min-h-5 leading-5">
                    {formatAdminDateTime(selectedSource.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="font-semibold text-[var(--color-ink)]">updated_at</dt>
                  <dd className="mt-1 min-h-5 leading-5">
                    {formatAdminDateTime(selectedSource.updated_at)}
                  </dd>
                </div>
              </dl>
            </div>
          </details>
        ) : null}
      </div>
    </div>
  );
}

function TechnicalClassificationResultsDisclosure({
  classifications,
  defaultOpen,
  metadata,
  onReplaceSources,
  status,
}: {
  classifications: TechnicalClassification[];
  defaultOpen: boolean;
  metadata: ProductStepMetadataField[];
  onReplaceSources?: () => void;
  status: ProductAnalysisStepStatus;
}) {
  const blockingCount = classifications.filter(
    (classification) => classification.is_blocking,
  ).length;
  const hasOutOfScopeClassification = classifications.some(isOutOfScopeClassification);
  const hasMixedClassification = classifications.some(isMixedTechnicalDossierClassification);
  const isClassificationRunning = status === "running";
  const isClassificationCompleted = status === "completed";
  const summaryTone =
    blockingCount > 0
      ? "danger"
      : isClassificationRunning
        ? "warning"
        : isClassificationCompleted && classifications.length > 0
          ? "success"
          : "neutral";
  const summaryLabel =
    blockingCount > 0
      ? `${blockingCount} bloquant${blockingCount > 1 ? "s" : ""}`
      : isClassificationRunning
        ? "En cours"
        : isClassificationCompleted && classifications.length > 0
          ? "Tous acceptés"
          : "En attente";

  return (
    <details className="group mt-3 w-full max-w-5xl" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 rounded-2xl bg-[var(--color-surface-raised)]/55 px-4 py-2.5 text-sm font-semibold text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]/55 [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden="true"
          className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open:rotate-90"
        />
        Résultats de classification
        <Badge tone={summaryTone} className="ml-auto">
          {summaryLabel}
        </Badge>
      </summary>

      <div className="mt-3 rounded-[1.35rem] bg-[var(--color-surface-raised)]/35 p-2.5 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
        {blockingCount > 0 ? (
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white/65 px-3 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <AlertTriangle
                className={cn(
                  "size-4 shrink-0",
                  hasOutOfScopeClassification
                    ? "text-[var(--color-error)]"
                    : "text-[var(--color-teak)]",
                )}
              />
              <p className="truncate text-sm font-semibold text-[var(--color-ink)]">
                {hasOutOfScopeClassification
                  ? "Lot bloqué par un document hors périmètre"
                  : hasMixedClassification
                    ? "Lot bloqué par un dossier technique mélangé"
                  : "Lot bloqué par une classification faible"}
              </p>
            </div>
            {onReplaceSources ? (
              <Button
                className="shrink-0"
                size="sm"
                variant="secondary"
                onClick={onReplaceSources}
              >
                <UploadCloud className="size-4" />
                Remplacer le lot
              </Button>
            ) : null}
          </div>
        ) : null}

        {classifications.length === 0 ? (
          <div className="rounded-[1.2rem] bg-white/65 p-4 text-sm leading-6 text-[var(--color-muted)]">
            Les résultats apparaîtront dès que la classification aura répondu.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl bg-white/60 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
            <div className="grid grid-cols-[minmax(24rem,1fr)_11rem_5.5rem_9rem] gap-3 border-b border-black/5 px-3 py-2 text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:hidden">
              <span>Document</span>
              <span>Type détecté</span>
              <span>Score</span>
              <span className="text-right">Statut</span>
            </div>
            {classifications.map((classification) => (
              <TechnicalClassificationResultItem
                key={classification.source_id}
                classification={classification}
              />
            ))}
          </div>
        )}

        <CompactProviderMetadata fields={metadata} />
      </div>
    </details>
  );
}

function CompactProviderMetadata({ fields }: { fields: ProductStepMetadataField[] }) {
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

function TechnicalClassificationResultItem({
  classification,
}: {
  classification: TechnicalClassification;
}) {
  const status = technicalClassificationStatus(classification);

  return (
    <div
      className={cn(
        "grid grid-cols-[minmax(24rem,1fr)_11rem_5.5rem_9rem] items-center gap-3 border-b border-black/5 px-3 py-2.5 last:border-b-0 max-lg:grid-cols-[minmax(0,1fr)_auto] max-lg:gap-y-2",
        status.tone === "danger"
          ? "bg-[var(--color-error-soft)]/28"
          : "bg-white/50",
      )}
    >
      <p
        className="min-w-0 truncate text-sm font-semibold text-[var(--color-ink)]"
        title={classification.file_name}
      >
        {classification.file_name}
      </p>

      <p className="min-w-0 truncate text-xs font-semibold text-[var(--color-forest)] max-lg:col-start-1">
        <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
          Type
        </span>
        {technicalDocumentTypeLabel(classification.document_type)}
      </p>

      <p className="text-xs font-semibold text-[var(--color-ink)] max-lg:col-start-1">
        <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
          Score
        </span>
        {formatGcpConfidence(classification.confidence)}
      </p>

      <Badge className="justify-self-end whitespace-nowrap" tone={status.tone}>
        {status.label}
      </Badge>
    </div>
  );
}

function TechnicalExtractionResultsDisclosure({
  candidates,
  metadata,
  sources,
}: {
  candidates: TechnicalFactCandidate[];
  metadata: ProductStepMetadataField[];
  sources: TechnicalSource[];
}) {
  const [selectedCandidate, setSelectedCandidate] = useState<TechnicalFactCandidate | null>(
    null,
  );
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const candidateGroups = groupExtractionCandidatesBySource(candidates, sources);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(
    candidateGroups[0]?.sourceId ?? null,
  );
  const selectedGroup =
    candidateGroups.find((group) => group.sourceId === selectedSourceId) ??
    candidateGroups[0] ??
    null;
  const selectedCandidates = selectedGroup?.candidates ?? [];
  const occurrenceLabels = buildExtractionCandidateOccurrenceLabels(selectedCandidates);
  const reviewRequiredCount = candidates.filter((candidate) => candidate.review_required).length;

  return (
    <>
      <details className="group mt-3 w-full max-w-5xl">
        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 rounded-2xl bg-[var(--color-surface-raised)]/55 px-4 py-2.5 text-sm font-semibold text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]/55 [&::-webkit-details-marker]:hidden">
          <span
            aria-hidden="true"
            className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open:rotate-90"
          />
          Résultats d’extraction
          {reviewRequiredCount > 0 ? (
            <Badge tone="warning" className="ml-auto">
              {reviewRequiredCount} à vérifier
            </Badge>
          ) : null}
        </summary>

        <div className="mt-3 rounded-[1.35rem] bg-[var(--color-surface-raised)]/35 p-2.5 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
          <div className="grid gap-2 lg:grid-cols-[15rem_minmax(0,1fr)]">
            <div className="rounded-2xl bg-[var(--color-ivory)] p-1.5">
              <div className="grid gap-1.5" role="tablist" aria-label="PDFs extraits">
                {candidateGroups.map((group, index) => {
                  const isSelected = selectedGroup?.sourceId === group.sourceId;

                  return (
                    <button
                      key={group.sourceId}
                      type="button"
                      role="tab"
                      aria-selected={isSelected}
                      className={cn(
                        "flex min-w-0 items-center gap-3 rounded-[1.05rem] px-3 py-2.5 text-left transition",
                        isSelected
                          ? "bg-white text-[var(--color-forest)] shadow-[0_10px_24px_rgba(27,28,26,0.07)]"
                          : "text-[var(--color-muted)] hover:bg-white/55 hover:text-[var(--color-ink)]",
                      )}
                      onClick={() => setSelectedSourceId(group.sourceId)}
                    >
                      <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
                        <FileCheck2 className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[0.68rem] font-bold uppercase tracking-[0.14em]">
                          PDF {index + 1}
                        </span>
                        <span className="mt-0.5 block break-all text-[0.58rem] font-semibold leading-3 text-[var(--color-muted)]">
                          {group.fileName}
                        </span>
                      </span>
                      <Badge tone="neutral" className="shrink-0">
                        {group.candidates.length}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl bg-white/60 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
              <div className="grid grid-cols-[minmax(14rem,0.85fr)_minmax(14rem,1fr)_5.5rem_6.5rem] gap-3 border-b border-black/5 px-3 py-2 text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:hidden">
                <span>Label</span>
                <span>Valeur source</span>
                <span>Score</span>
                <span className="text-right">Preuve</span>
              </div>

              {selectedCandidates.map((candidate) => {
                const source = sourceById.get(candidate.source_id) ?? null;
                const proofText = extractionCandidateProofText(candidate);
                const proofDisabled = source === null || proofText === null;
                const occurrenceLabel = occurrenceLabels.get(candidate.id);
                const labelMetadata = technicalFactLabelMetadata(candidate.field_name);
                const labelDescription = technicalFactLabelDescription(
                  candidate.field_name,
                  source?.document_type,
                );

                return (
                  <div
                    key={candidate.id}
                    className="grid grid-cols-[minmax(14rem,0.85fr)_minmax(14rem,1fr)_5.5rem_6.5rem] items-center gap-3 border-b border-black/5 bg-white/50 px-3 py-2.5 last:border-b-0 max-lg:grid-cols-[minmax(0,1fr)_auto] max-lg:gap-y-2"
                  >
                    <div className="min-w-0">
                      <p
                        className="min-w-0 cursor-help truncate text-sm font-semibold text-[var(--color-ink)]"
                        title={labelDescription}
                      >
                        {candidate.field_name}
                        {occurrenceLabel ? (
                          <span className="ml-1 text-[0.68rem] font-bold text-[var(--color-muted)]">
                            {occurrenceLabel}
                          </span>
                        ) : null}
                      </p>
                      <p className="mt-0.5 whitespace-nowrap text-[0.52rem] font-bold uppercase leading-3 tracking-[0.06em] text-[var(--color-muted)]">
                        {labelMetadata.dataType} · {labelMetadata.method} ·{" "}
                        {labelMetadata.occurrence}
                      </p>
                    </div>

                    <p
                      className="min-w-0 whitespace-normal break-words text-xs font-semibold leading-5 text-[var(--color-forest)] max-lg:col-start-1"
                      title={extractionCandidateDisplayValue(candidate)}
                    >
                      <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
                        Valeur
                      </span>
                      {extractionCandidateDisplayValue(candidate)}
                    </p>

                    <p className="text-xs font-semibold text-[var(--color-ink)] max-lg:col-start-1">
                      <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
                        Score
                      </span>
                      {formatGcpConfidence(candidate.extractor_confidence)}
                    </p>

                    <Button
                      className="justify-self-end"
                      size="sm"
                      variant="secondary"
                      disabled={proofDisabled}
                      onClick={() => setSelectedCandidate(candidate)}
                    >
                      <FileText className="size-4" />
                      Voir
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>

          <CompactProviderMetadata fields={metadata} />
        </div>
      </details>

      {selectedCandidate ? (
        <TechnicalSourcePdfDialog
          candidate={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
          source={sourceById.get(selectedCandidate.source_id) ?? null}
        />
      ) : null}
    </>
  );
}

function TechnicalSourcePdfDialog({
  candidate,
  onClose,
  source,
}: {
  candidate: TechnicalFactCandidate;
  onClose: () => void;
  source: TechnicalSource | null;
}) {
  const proofText = extractionCandidateProofText(candidate) ?? "";
  const fileName = source?.original_file_name ?? "PDF technique";
  const sourceId = source?.id ?? null;
  const loadPdf = useCallback(async () => {
    if (sourceId === null) {
      return null;
    }

    return (await loadTechnicalSourcePdf(sourceId)) ?? loadTechnicalSourcePdfByFileName(fileName);
  }, [fileName, sourceId]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.26)] p-5 backdrop-blur-sm">
      <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-[1.6rem] bg-[var(--color-ivory)] shadow-[0_28px_90px_rgba(27,28,26,0.22)]">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-black/5 px-6 py-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Preuve PDF
            </p>
            <h2 className="mt-1 truncate font-serif text-2xl font-semibold tracking-[-0.035em] text-[var(--color-ink)]">
              {technicalFactFieldLabel(candidate.field_name)}
            </h2>
            <p className="mt-1 max-w-3xl truncate text-sm font-semibold text-[var(--color-muted)]">
              {fileName} · {extractionCandidateDisplayValue(candidate)}
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={onClose}>
            <X className="size-4" />
            Fermer
          </Button>
        </div>

        <div className="min-h-0 flex-1 p-4">
          {source === null ? (
            <div className="grid h-full place-items-center rounded-[1.25rem] bg-white/70 px-6 text-center">
              <div>
                <p className="font-serif text-2xl font-semibold tracking-[-0.04em] text-[var(--color-ink)]">
                  Source introuvable
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
                  Le document source n’est plus associé à ce fait extrait.
                </p>
              </div>
            </div>
          ) : (
            <SourcePdfPreview
              className="h-full"
              excerpt={proofText}
              fileName={fileName}
              loadPdf={loadPdf}
              pageEnd={candidate.source_page}
              pageStart={candidate.source_page}
            />
          )}
        </div>
      </div>
    </div>
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

type ProductAnalysisStepStatus =
  | "blocked"
  | "completed"
  | "running"
  | "pending"
  | "failed"
  | "review";
type ProductAnalysisStepId =
  | "document-classification"
  | "fact-extraction"
  | "deterministic-validation"
  | "technical-review"
  | "context";
type ProductStepMetadataField = { label: string; value: string };

type ProductAnalysisStep = {
  description: string;
  eta?: string;
  id: ProductAnalysisStepId;
  label: string;
  metadata: ProductStepMetadataField[];
  status: ProductAnalysisStepStatus;
  statusLabel?: string;
};

function ProductAnalysisStepItem({
  classificationResults,
  defaultOpenClassificationResults = false,
  elapsedTime,
  extractionResults,
  extractionSources = [],
  generationReadiness,
  hideStepMetadata = false,
  onReplaceSources,
  productId,
  step,
  validationReviewCases = [],
}: {
  classificationResults?: TechnicalClassification[];
  defaultOpenClassificationResults?: boolean;
  elapsedTime: string;
  extractionResults?: TechnicalFactCandidate[];
  extractionSources?: TechnicalSource[];
  generationReadiness?: ProductOverview["generation_readiness"];
  hideStepMetadata?: boolean;
  onReplaceSources?: () => void;
  productId: string;
  step: ProductAnalysisStep;
  validationReviewCases?: TechnicalReviewCase[];
}) {
  const isRunning = step.status === "running";

  return (
    <li className="grid grid-cols-[42px_1fr] gap-4">
      <span
        className={cn(
          "mt-1 grid size-10 place-items-center rounded-2xl",
          step.status === "completed" && "bg-[var(--color-sage-soft)] text-[var(--color-forest)]",
          step.status === "running" && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
          step.status === "review" && "bg-[var(--color-gold-soft)] text-[var(--color-teak)]",
          step.status === "pending" && "bg-[var(--color-stone)] text-[var(--color-muted)]",
          step.status === "failed" && "bg-[var(--color-error-soft)] text-[var(--color-error)]",
          step.status === "blocked" && "bg-[var(--color-error-soft)] text-[var(--color-error)]",
        )}
        aria-current={isRunning ? "step" : undefined}
      >
        {isRunning ? (
          <Loader2 className="size-5 animate-spin" />
        ) : step.status === "review" || step.status === "blocked" ? (
          <AlertTriangle className="size-5" />
        ) : step.status === "failed" ? (
          <FileText className="size-5" />
        ) : (
          <CheckCircle2 className="size-5" />
        )}
      </span>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold text-[var(--color-ink)]">{step.label}</p>
          <Badge tone={productAnalysisStepTone(step.status)}>
            {step.statusLabel ?? productAnalysisStepLabel(step.status)}
          </Badge>
        </div>
        <p className="mt-1 text-sm leading-6 text-[var(--color-muted)]">{step.description}</p>
        {generationReadiness ? (
          <TechnicalValidationResultsDisclosure
            generationReadiness={generationReadiness}
            productId={productId}
            reviewCases={validationReviewCases}
          />
        ) : null}
        {classificationResults ? (
          <TechnicalClassificationResultsDisclosure
            classifications={classificationResults}
            defaultOpen={defaultOpenClassificationResults}
            metadata={step.metadata}
            onReplaceSources={onReplaceSources}
            status={step.status}
          />
        ) : null}
        {extractionResults ? (
          <TechnicalExtractionResultsDisclosure
            candidates={extractionResults}
            metadata={step.metadata}
            sources={extractionSources}
          />
        ) : null}
        {hideStepMetadata ? null : <StepMetadata fields={step.metadata} />}
        {step.eta ? (
          <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs leading-5 text-[var(--color-muted)]">
            <span>{step.eta}</span>
            {isRunning ? (
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden="true">·</span>
                <Clock3 className="size-3.5" />
                <span>{elapsedTime}</span>
              </span>
            ) : null}
          </p>
        ) : null}
      </div>
    </li>
  );
}

function TechnicalValidationResultsDisclosure({
  generationReadiness,
  productId,
  reviewCases,
}: {
  generationReadiness: NonNullable<ProductOverview["generation_readiness"]>;
  productId: string;
  reviewCases: TechnicalReviewCase[];
}) {
  const [selectedCase, setSelectedCase] = useState<TechnicalReviewCase | null>(null);
  const checks = validationFieldChecks(generationReadiness);
  const blockingCount = generationReadiness.blocking_count ?? 0;
  const hasBlocking = blockingCount > 0;
  const [isOpen, setIsOpen] = useState(hasBlocking);

  useEffect(() => {
    if (hasBlocking) {
      setIsOpen(true);
    }
  }, [hasBlocking]);

  if (checks.length === 0) {
    return <GenerationReadinessSummary generationReadiness={generationReadiness} />;
  }

  return (
    <>
      <details
        className="group mt-3 w-full max-w-5xl"
        open={isOpen}
        onToggle={(event) => setIsOpen(event.currentTarget.open)}
      >
        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 rounded-2xl bg-[var(--color-surface-raised)]/55 px-4 py-2.5 text-sm font-semibold text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]/55 [&::-webkit-details-marker]:hidden">
          <span
            aria-hidden="true"
            className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open:rotate-90"
          />
          Résultats du contrôle
          <Badge className="ml-auto" tone={hasBlocking ? "danger" : "success"}>
            {hasBlocking ? `${blockingCount} à corriger` : "Prêt"}
          </Badge>
        </summary>

        <div className="mt-3 overflow-hidden rounded-[1.35rem] bg-white/60 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
          <div className="grid grid-cols-[minmax(12rem,0.8fr)_minmax(14rem,1fr)_5.5rem_8rem_7rem] gap-3 border-b border-black/5 px-3 py-2 text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-xl:hidden">
            <span>Champ</span>
            <span>Valeur retenue / candidates</span>
            <span>Score</span>
            <span>Contrôle</span>
            <span className="text-right">Action</span>
          </div>

          {checks.map((check) => {
            const reviewCase = findReviewCaseForCheck(reviewCases, check);
            const rowTone = validationCheckTone(check);
            const valueLabel = validationCheckValueLabel(check);

            return (
              <div
                key={`${check.fieldName}-${check.status}`}
                className={cn(
                  "grid grid-cols-[minmax(12rem,0.8fr)_minmax(14rem,1fr)_5.5rem_8rem_7rem] items-center gap-3 border-b border-black/5 px-3 py-2.5 last:border-b-0 max-xl:grid-cols-[minmax(0,1fr)_auto] max-xl:gap-y-2",
                  rowTone === "danger" && "bg-[var(--color-error-soft)]/45",
                  rowTone === "warning" && "bg-[var(--color-gold-soft)]/45",
                  rowTone === "success" && "bg-[var(--color-sage-soft)]/35",
                  rowTone === "neutral" && "bg-white/45",
                )}
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--color-ink)]">
                    {technicalFactFieldLabel(check.fieldName)}
                  </p>
                  <p className="mt-0.5 text-[0.58rem] font-bold uppercase tracking-[0.08em] text-[var(--color-muted)]">
                    {check.fieldName} · {check.cardinality}
                  </p>
                </div>
                <p className="text-xs font-semibold leading-5 text-[var(--color-forest)]">
                  {valueLabel}
                </p>
                <p className="text-xs font-semibold text-[var(--color-ink)]">
                  {formatGcpConfidence(check.confidence)}
                </p>
                <Badge tone={rowTone}>{validationCheckStatusLabel(check)}</Badge>
                <div className="justify-self-end">
                  {reviewCase && ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status) ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setSelectedCase(reviewCase)}
                    >
                      Décider
                    </Button>
                  ) : (
                    <span className="text-xs font-semibold text-[var(--color-muted)]">
                      {rowTone === "success" ? "Validé" : "Sans action"}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </details>

      <ResolveTechnicalReviewCaseDialog
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

function GenerationReadinessSummary({
  generationReadiness,
}: {
  generationReadiness: NonNullable<ProductOverview["generation_readiness"]>;
}) {
  const requiredMissing = generationReadiness.required_missing ?? [];
  const lowConfidenceCount = generationReadiness.low_confidence?.length ?? 0;
  const outOfBoundsCount = generationReadiness.out_of_bounds?.length ?? 0;
  const contradictionCount = generationReadiness.contradictions?.length ?? 0;
  const doNotMention = generationReadiness.do_not_mention ?? [];
  const blockingCount =
    generationReadiness.blocking_count ??
    requiredMissing.length + lowConfidenceCount + outOfBoundsCount + contradictionCount;

  return (
    <div className="mt-3 w-full max-w-3xl rounded-2xl bg-[var(--color-surface-raised)]/55 p-3 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
          Readiness génération
        </p>
        <Badge tone={blockingCount > 0 ? "warning" : "success"}>
          {blockingCount > 0 ? `${blockingCount} blocage${blockingCount > 1 ? "s" : ""}` : "OK"}
        </Badge>
      </div>

      <p className="mt-2 text-sm font-semibold leading-5 text-[var(--color-forest)]">
        {generationReadiness.profile_code ?? "Profil product_sheet"}
      </p>

      {requiredMissing.length > 0 ? (
        <p className="mt-2 text-xs leading-5 text-[var(--color-muted)]">
          Champs manquants : {requiredMissing.map(formatCode).join(", ")}
        </p>
      ) : null}

      {outOfBoundsCount > 0 || lowConfidenceCount > 0 || contradictionCount > 0 ? (
        <p className="mt-1 text-xs leading-5 text-[var(--color-muted)]">
          Contrôles à revoir : {lowConfidenceCount} confiance faible, {outOfBoundsCount} hors borne, {contradictionCount} contradiction.
        </p>
      ) : null}

      {doNotMention.length > 0 ? (
        <p className="mt-1 text-xs leading-5 text-[var(--color-muted)]">
          À ne pas mentionner sans preuve : {doNotMention.map(formatCode).join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function StepMetadata({ fields }: { fields: ProductStepMetadataField[] }) {
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

function ProductCriteriaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl bg-white/70 px-4 py-3">
      <dt className="font-semibold text-[var(--color-muted)]">{label}</dt>
      <dd className="font-semibold text-[var(--color-ink)]">{value}</dd>
    </div>
  );
}

function FactsCard({ overview }: { overview: ProductOverview }) {
  const factsOrCandidates = overview.facts.length > 0 ? overview.facts : overview.fact_candidates;

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-start justify-between gap-4 p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
            Faits techniques
          </p>
          <CardTitle className="mt-2">
            {overview.facts.length > 0 ? "Faits validés" : "Faits proposés"}
          </CardTitle>
        </div>
        <Badge tone={overview.facts.length > 0 ? "success" : "neutral"}>
          {factsOrCandidates.length}
        </Badge>
      </div>

      {overview.generation_readiness ? (
        <div className="px-6 pb-6">
          <GenerationReadinessSummary generationReadiness={overview.generation_readiness} />
        </div>
      ) : null}

      {factsOrCandidates.length === 0 ? (
        <div className="border-t border-[var(--color-stone)] p-6 text-sm leading-6 text-[var(--color-muted)]">
          Les faits techniques apparaîtront ici après l’analyse.
        </div>
      ) : (
        <div className="overflow-x-auto border-t border-[var(--color-stone)]">
          <table className="w-full min-w-[42rem] border-collapse text-left">
            <thead>
              <tr className="bg-[var(--color-surface-raised)]/55 text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
                <th className="px-6 py-4">Champ</th>
                <th className="px-4 py-4">Valeur</th>
                <th className="px-4 py-4">Statut</th>
              </tr>
            </thead>
            <tbody>
              {factsOrCandidates.map((item) => {
                const isFact = "value" in item;
                const value = isFact ? item.value : item.normalized_value ?? item.raw_value ?? "Non extrait";
                const unit = isFact ? item.unit : item.unit;

                return (
                  <tr key={item.id} className="border-t border-[var(--color-stone)]/80">
                    <td className="px-6 py-4 text-sm font-semibold text-[var(--color-ink)]">
                      {formatCode(item.field_name)}
                    </td>
                    <td className="px-4 py-4 text-sm text-[var(--color-muted)]">
                      {value}
                      {unit ? ` ${unit}` : ""}
                    </td>
                    <td className="px-4 py-4">
                      <Badge tone={isFact ? "success" : item.review_required ? "warning" : "neutral"}>
                        {isFact ? "Validé" : item.validation_status}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function GenerationCard({ overview }: { overview: ProductOverview }) {
  const isReady = overview.product_context_snapshot !== null;

  return (
    <section className="mt-6">
      <Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-start justify-between gap-4 p-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Génération
            </p>
            <CardTitle className="mt-2">
              {isReady ? "Contexte prêt" : "Génération à venir"}
            </CardTitle>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
              {isReady
                ? "Le contexte produit est assemblé. La génération de fiche sera branchée à l’étape suivante."
                : "La fiche sera générable quand le guide, les faits techniques et les signaux commerciaux seront disponibles."}
            </p>
          </div>
          <Badge tone={isReady ? "success" : "neutral"}>
            {isReady ? "Prêt" : "Verrouillé"}
          </Badge>
        </div>
        <div className="border-t border-[var(--color-stone)] bg-[var(--color-surface-raised)]/45 p-6">
          <Button disabled>
            <Sparkles className="size-4" />
            Générer la fiche produit
          </Button>
        </div>
      </Card>
    </section>
  );
}

function LoadingState({ onBack }: { onBack: () => void }) {
  return (
    <div className="grid min-h-[70vh] place-items-center">
      <div className="text-center">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" />
          Fiches produit
        </Button>
        <p className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-[var(--color-muted)]">
          <Loader2 className="size-4 animate-spin" />
          Chargement du produit...
        </p>
      </div>
    </div>
  );
}

function ErrorState({ error, onBack }: { error: Error | null; onBack: () => void }) {
  return (
    <div className="grid min-h-[70vh] place-items-center">
      <Card className="max-w-xl text-center">
        <div className="mx-auto grid size-14 place-items-center rounded-3xl bg-[var(--color-error-soft)] text-[var(--color-error)]">
          <FileText className="size-7" />
        </div>
        <h1 className="mt-5 font-serif text-3xl font-semibold tracking-[-0.04em]">
          Produit introuvable
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
          {error?.message ?? "Impossible de charger le détail du produit."}
        </p>
        <Button className="mt-5" onClick={onBack}>
          <ArrowLeft className="size-4" />
          Retour aux fiches
        </Button>
      </Card>
    </div>
  );
}

function buildTechnicalAnalysisSteps(overview: ProductOverview): ProductAnalysisStep[] {
  const currentStep = overview.run?.current_step ?? "";
  const hasFacts = overview.facts.length > 0;
  const hasCandidates = overview.fact_candidates.length > 0;
  const hasOpenReviewCases = overview.review_cases.some((reviewCase) =>
    ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
  );
  const hasOpenClassificationReviewCases = overview.review_cases.some(
    (reviewCase) =>
      reviewCase.case_type === "CLASSIFICATION_UNCERTAIN" &&
      ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
  );
  const hasOutOfScopeClassification = overview.technical_classifications.some(
    isOutOfScopeClassification,
  );
  const hasNonClassificationReviewCases = overview.review_cases.some(
    (reviewCase) => reviewCase.case_type !== "CLASSIFICATION_UNCERTAIN",
  );
  const hasOpenNonClassificationReviewCases = overview.review_cases.some(
    (reviewCase) =>
      reviewCase.case_type !== "CLASSIFICATION_UNCERTAIN" &&
      ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
  );
  const contextReady = overview.product_context_snapshot !== null;
  const steps = normalizeTechnicalExtractionSteps(overview.run);
  const hasExtractionResults = steps.some((step) => step.step === "extraction");
  const isStoppedAfterExtractionForPoc =
    currentStep === "DETERMINISTIC_VALIDATION" &&
    hasCandidates &&
    !hasFacts &&
    !hasNonClassificationReviewCases &&
    !overview.generation_readiness;
  const classificationDone =
    hasFacts ||
    hasCandidates ||
    ["FACT_EXTRACTION", "DETERMINISTIC_VALIDATION", "HUMAN_REVIEW", "PROMOTION", "DONE"].includes(
      currentStep,
    );
  const extractionDone =
    !hasOpenClassificationReviewCases &&
    (hasFacts ||
      hasCandidates ||
      hasExtractionResults ||
      ["DETERMINISTIC_VALIDATION", "HUMAN_REVIEW", "PROMOTION", "DONE"].includes(
        currentStep,
      ));
  const validationDone =
    !hasOpenClassificationReviewCases &&
    !hasOpenNonClassificationReviewCases &&
    (hasFacts ||
      (hasNonClassificationReviewCases && !hasOpenNonClassificationReviewCases) ||
      ["HUMAN_REVIEW", "PROMOTION", "DONE"].includes(currentStep));

  return [
    {
      id: "document-classification",
      label: "Classification des PDFs",
      description: hasOutOfScopeClassification
        ? "Un ou plusieurs PDFs ne sont pas des dossiers techniques exploitables. Le lot doit être remplacé avant extraction."
        : hasOpenClassificationReviewCases
        ? "Un type de document doit être confirmé avant extraction."
        : `${overview.sources.length} PDF importé${overview.sources.length > 1 ? "s" : ""}. Chaque document est identifié avant extraction.`,
      status: hasOutOfScopeClassification
        ? "blocked"
        : hasOpenClassificationReviewCases
        ? "review"
        : classificationDone
        ? "completed"
        : currentStep === "DOCUMENT_CLASSIFICATION"
          ? "running"
          : "pending",
      statusLabel: hasOutOfScopeClassification ? "Lot à remplacer" : undefined,
      eta: "souvent quelques secondes par PDF",
      metadata: metadataFieldsForTechnicalStep("document-classification", steps),
    },
    {
      id: "fact-extraction",
      label: "Extraction des faits",
      description:
        hasFacts || hasCandidates
          ? "Les informations techniques ont été extraites des PDFs."
          : "Les champs utiles à la fiche produit sont extraits par type de document.",
      status: extractionDone
        ? "completed"
        : currentStep === "FACT_EXTRACTION"
          ? "running"
          : "pending",
      eta: "souvent 1 à 3 min",
      metadata: metadataFieldsForTechnicalStep("fact-extraction", steps),
    },
    {
      id: "deterministic-validation",
      label: "Contrôle déterministe",
      description: hasNonClassificationReviewCases
        ? "Des points peuvent demander une validation humaine après extraction."
        : "Les champs requis, valeurs et confiances sont contrôlés avant promotion.",
      status: hasOpenNonClassificationReviewCases
        ? "blocked"
        : validationDone
        ? "completed"
        : currentStep === "DETERMINISTIC_VALIDATION" && !isStoppedAfterExtractionForPoc
          ? "running"
          : "pending",
      statusLabel: hasOpenNonClassificationReviewCases ? "À corriger" : undefined,
      eta: "souvent moins d’une minute",
      metadata: metadataFieldsForTechnicalStep("deterministic-validation", steps),
    },
    {
      id: "technical-review",
      label: "Revue technique",
      description: hasOpenNonClassificationReviewCases
        ? "Les points bloquants sont prêts à être résolus."
        : "Une relecture humaine est demandée seulement si un blocage est détecté.",
      status: hasOpenNonClassificationReviewCases
        ? "running"
        : hasFacts && !hasOpenReviewCases
          ? "completed"
          : "pending",
      metadata: [],
    },
    {
      id: "context",
      label: "Contexte produit",
      description: contextReady
        ? "Le contexte produit est prêt."
        : "Le contexte sera assemblé après validation des faits et signaux compatibles.",
      status: contextReady ? "completed" : currentStep === "PROMOTION" ? "running" : "pending",
      metadata: [],
    },
  ];
}

function productAnalysisStepLabel(status: ProductAnalysisStepStatus) {
  if (status === "blocked") {
    return "Lot à remplacer";
  }
  if (status === "completed") {
    return "Terminé";
  }
  if (status === "running") {
    return "En cours";
  }
  if (status === "review") {
    return "À confirmer";
  }
  if (status === "failed") {
    return "Erreur";
  }
  return "À venir";
}

function productAnalysisStepTone(status: ProductAnalysisStepStatus) {
  if (status === "blocked") {
    return "danger";
  }
  if (status === "completed") {
    return "success";
  }
  if (status === "running") {
    return "warning";
  }
  if (status === "review") {
    return "warning";
  }
  if (status === "failed") {
    return "danger";
  }
  return "neutral";
}

function normalizeTechnicalExtractionSteps(run: TechnicalRun | null) {
  const extractionSteps = run?.extraction_steps_json;
  if (!isRecord(extractionSteps)) {
    return [];
  }

  const steps = extractionSteps.steps;
  return Array.isArray(steps) ? steps.filter(isRecord) : [];
}

function metadataFieldsForTechnicalStep(
  stepId: ProductAnalysisStepId,
  steps: Array<Record<string, unknown>>,
): ProductStepMetadataField[] {
  if (stepId === "document-classification") {
    return buildDocumentAiMetadata(findTechnicalStep(steps, "classification"), "custom_classifier");
  }

  if (stepId === "fact-extraction") {
    return buildDocumentAiMetadataForSteps(findTechnicalSteps(steps, "extraction"), "custom_extractor");
  }

  if (stepId === "deterministic-validation") {
    const step = findTechnicalStep(steps, "validation");
    if (step === null) {
      return [];
    }

    return compactMetadataFields([
      ["Fournisseur", "Factory Writer"],
      ["Processor", "Validateur déterministe"],
      ["Version", "Règles POC"],
    ]);
  }

  return [];
}

function buildDocumentAiMetadata(
  step: Record<string, unknown> | null,
  fallbackProcessorKind: string,
): ProductStepMetadataField[] {
  if (step === null) {
    return [];
  }

  const requestConfig = isRecord(step.request_config_snapshot) ? step.request_config_snapshot : null;
  const processorResourceName = optionalString(step.processor_resource_name);
  const processorVersion = optionalString(step.processor_version);

  return compactMetadataFields([
    ["Fournisseur", "Google Document AI"],
    [
      "Processor",
      processorIdFromResourceName(processorResourceName) ??
        optionalString(requestConfig?.processor_kind) ??
        fallbackProcessorKind,
    ],
    ["Version", processorVersionLabel(processorVersion)],
  ]);
}

function buildDocumentAiMetadataForSteps(
  steps: Array<Record<string, unknown>>,
  fallbackProcessorKind: string,
): ProductStepMetadataField[] {
  if (steps.length === 0) {
    return [];
  }

  if (steps.length === 1) {
    return buildDocumentAiMetadata(steps[0] ?? null, fallbackProcessorKind);
  }

  return compactMetadataFields([
    ["Fournisseur", "Google Document AI"],
    ...steps.map((step, index): [string, string] => {
      const processorResourceName = optionalString(step.processor_resource_name);
      const processorId =
        processorIdFromResourceName(processorResourceName) ??
        optionalString(
          isRecord(step.request_config_snapshot)
            ? step.request_config_snapshot.processor_kind
            : null,
        ) ??
        fallbackProcessorKind;
      const processorVersion = optionalString(step.processor_version);
      const documentTypeLabel =
        technicalDocumentTypeFromStep(step) ?? "Type non renseigné";

      return [
        `PDF ${index + 1} · ${documentTypeLabel}`,
        `Processor ${processorId} · Version ${processorVersionLabel(processorVersion)}`,
      ];
    }),
  ]);
}

function findTechnicalStep(
  steps: Array<Record<string, unknown>>,
  stepName: string,
): Record<string, unknown> | null {
  return steps.find((step) => step.step === stepName) ?? null;
}

function findTechnicalSteps(
  steps: Array<Record<string, unknown>>,
  stepName: string,
): Array<Record<string, unknown>> {
  return steps.filter((step) => step.step === stepName);
}

function compactMetadataFields(
  pairs: Array<[string, string | null | undefined]>,
): ProductStepMetadataField[] {
  return pairs.flatMap(([label, value]) => {
    const normalizedValue = optionalString(value);
    return normalizedValue === null ? [] : [{ label, value: normalizedValue }];
  });
}

function optionalString(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  const text = String(value).trim();
  return text.length > 0 ? text : null;
}

function processorIdFromResourceName(resourceName: string | null) {
  if (resourceName === null) {
    return null;
  }

  const parts = resourceName.split("/");
  const processorIndex = parts.indexOf("processors");
  return processorIndex >= 0 ? parts[processorIndex + 1] ?? null : null;
}

function technicalDocumentTypeFromStep(step: Record<string, unknown>): string | null {
  const requestConfig = isRecord(step.request_config_snapshot) ? step.request_config_snapshot : null;
  const documentType =
    optionalString(requestConfig?.extractor_document_type) ??
    optionalString(requestConfig?.document_type) ??
    optionalString(step.document_type);

  return documentType === null ? null : technicalDocumentTypeLabel(documentType);
}

function splitMetadataValue(value: string): { primary: string; secondary: string | null } {
  const match = value.match(/^(.*)\s(\(Gemini [^)]+\))$/);
  if (!match) {
    return { primary: value, secondary: null };
  }

  return { primary: match[1], secondary: match[2] };
}

function annotateDocumentAiProcessorVersion(version: string | null): string | null {
  if (version === null) {
    return null;
  }

  if (version === "pretrained-classifier-v1.5-2025-08-05") {
    return `${version} (Gemini 2.5 Flash)`;
  }

  if (version === "pretrained-foundation-model-v1.5-pro-2025-06-20") {
    return `${version} (Gemini 2.5 Pro)`;
  }

  return version;
}

function processorVersionLabel(version: string | null): string {
  return annotateDocumentAiProcessorVersion(version) ?? "Version par défaut";
}

function useProductAnalysisNow(isActive: boolean) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!isActive) {
      return;
    }

    setNow(Date.now());
    const intervalId = window.setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [isActive]);

  return now;
}

function formatTechnicalRunElapsedTime(run: TechnicalRun | null, now: number) {
  const rawDate = run?.updated_at ?? run?.started_at ?? run?.created_at;
  if (!rawDate) {
    return "moins d’une minute";
  }

  const date = new Date(hasTimezoneOffset(rawDate) ? rawDate : `${rawDate}Z`);
  if (Number.isNaN(date.getTime())) {
    return "moins d’une minute";
  }

  const elapsedSeconds = Math.max(1, Math.floor((now - date.getTime()) / 1000));
  return formatWorkflowElapsedTime(`${elapsedSeconds} s`);
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

function hasTimezoneOffset(value: string) {
  return /(?:Z|[+-]\d{2}:\d{2})$/.test(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

type ValidationFieldCheck = {
  fieldName: string;
  cardinality: string;
  status: string;
  selectedValues: string[];
  confidence: number | null;
  blockingReason: string | null;
  alternatives: Array<Record<string, unknown>>;
};

function validationFieldChecks(
  generationReadiness: NonNullable<ProductOverview["generation_readiness"]>,
): ValidationFieldCheck[] {
  const rawChecks = generationReadiness.field_checks;
  if (!Array.isArray(rawChecks)) {
    return [];
  }

  return rawChecks.flatMap((rawCheck) => {
    if (!isRecord(rawCheck)) {
      return [];
    }
    const fieldName = stringRecordValue(rawCheck, "field_name");
    if (fieldName === null) {
      return [];
    }
    return [
      {
        fieldName,
        cardinality: stringRecordValue(rawCheck, "cardinality") ?? "SINGLE",
        status: stringRecordValue(rawCheck, "status") ?? "UNKNOWN",
        selectedValues: stringArrayRecordValue(rawCheck, "selected_values"),
        confidence: numberRecordValue(rawCheck, "confidence"),
        blockingReason: stringRecordValue(rawCheck, "blocking_reason"),
        alternatives: recordArrayValue(rawCheck, "alternatives"),
      },
    ];
  });
}

function findReviewCaseForCheck(
  reviewCases: TechnicalReviewCase[],
  check: ValidationFieldCheck,
): TechnicalReviewCase | null {
  return (
    reviewCases.find(
      (reviewCase) =>
        reviewCase.field_name === check.fieldName &&
        ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
    ) ?? null
  );
}

function validationCheckTone(
  check: ValidationFieldCheck,
): "danger" | "neutral" | "success" | "warning" {
  if (check.status === "BLOCKED") {
    return "danger";
  }
  if (check.status === "WARNING") {
    return "warning";
  }
  if (check.status === "PASSED") {
    return "success";
  }
  return "neutral";
}

function validationCheckStatusLabel(check: ValidationFieldCheck) {
  if (check.status === "BLOCKED") {
    return check.blockingReason ? formatCode(check.blockingReason) : "Bloqué";
  }
  if (check.status === "WARNING") {
    return "À surveiller";
  }
  if (check.status === "PASSED") {
    return "Validé";
  }
  if (check.status === "SKIPPED") {
    return "Non mentionné";
  }
  return formatCode(check.status);
}

function validationCheckValueLabel(check: ValidationFieldCheck) {
  if (check.selectedValues.length > 0) {
    return check.selectedValues.join(" · ");
  }

  const alternativeValues = check.alternatives
    .map((alternative) => {
      const value =
        stringRecordValue(alternative, "normalized_value") ??
        stringRecordValue(alternative, "raw_value");
      const unit = stringRecordValue(alternative, "unit");
      return value ? `${value}${unit && !value.includes(unit) ? ` ${unit}` : ""}` : null;
    })
    .filter((value): value is string => value !== null);

  return alternativeValues.length > 0 ? alternativeValues.join(" / ") : "Non renseigné";
}

function stringRecordValue(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberRecordValue(record: Record<string, unknown>, key: string): number | null {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArrayRecordValue(record: Record<string, unknown>, key: string): string[] {
  const value = record[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function recordArrayValue(record: Record<string, unknown>, key: string): Array<Record<string, unknown>> {
  const value = record[key];
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function formatNullable(value: string | null | undefined) {
  return value && value.length > 0 ? value : "Non renseigné";
}

function extractionCandidateProofText(candidate: TechnicalFactCandidate) {
  const value =
    candidate.source_evidence_text ?? candidate.raw_value ?? candidate.normalized_value;
  return value !== null && value.trim().length > 0 ? value : null;
}

function extractionCandidateDisplayValue(candidate: TechnicalFactCandidate) {
  const evidenceText = candidate.source_evidence_text?.trim();
  if (evidenceText) {
    return evidenceText;
  }

  const rawValue = candidate.raw_value?.trim();
  if (rawValue) {
    return rawValue;
  }

  const normalizedValue = candidate.normalized_value?.trim();
  if (!normalizedValue) {
    return "Non extrait";
  }

  return candidate.unit ? `${normalizedValue} ${candidate.unit}` : normalizedValue;
}

type ExtractionCandidateGroup = {
  sourceId: string;
  fileName: string;
  candidates: TechnicalFactCandidate[];
};

function groupExtractionCandidatesBySource(
  candidates: TechnicalFactCandidate[],
  sources: TechnicalSource[],
): ExtractionCandidateGroup[] {
  const candidatesBySourceId = new Map<string, TechnicalFactCandidate[]>();

  for (const candidate of candidates) {
    const group = candidatesBySourceId.get(candidate.source_id) ?? [];
    group.push(candidate);
    candidatesBySourceId.set(candidate.source_id, group);
  }

  const groups = sources.flatMap((source) => {
    const sourceCandidates = candidatesBySourceId.get(source.id) ?? [];
    return sourceCandidates.length === 0
      ? []
      : [
          {
            sourceId: source.id,
            fileName: source.original_file_name,
            candidates: sourceCandidates,
          },
        ];
  });

  for (const [sourceId, sourceCandidates] of candidatesBySourceId.entries()) {
    if (sources.some((source) => source.id === sourceId)) {
      continue;
    }

    groups.push({
      sourceId,
      fileName: "PDF technique",
      candidates: sourceCandidates,
    });
  }

  return groups;
}

function buildExtractionCandidateOccurrenceLabels(
  candidates: TechnicalFactCandidate[],
): Map<string, string> {
  const totalsByFieldName = new Map<string, number>();
  const seenByFieldName = new Map<string, number>();
  const labelsByCandidateId = new Map<string, string>();

  for (const candidate of candidates) {
    totalsByFieldName.set(
      candidate.field_name,
      (totalsByFieldName.get(candidate.field_name) ?? 0) + 1,
    );
  }

  for (const candidate of candidates) {
    const total = totalsByFieldName.get(candidate.field_name) ?? 0;
    if (total <= 1) {
      continue;
    }

    const index = (seenByFieldName.get(candidate.field_name) ?? 0) + 1;
    seenByFieldName.set(candidate.field_name, index);
    labelsByCandidateId.set(candidate.id, `${index}/${total}`);
  }

  return labelsByCandidateId;
}

function technicalFactLabelMetadata(_fieldName: string): {
  dataType: string;
  method: string;
  occurrence: string;
} {
  return {
    dataType: "Plain text",
    method: "Extract",
    occurrence: "Optional multiple",
  };
}

function technicalFactLabelDescription(
  fieldName: string,
  documentType: string | null | undefined,
) {
  const scopedDescription =
    TECHNICAL_FACT_LABEL_DESCRIPTIONS[`${documentType ?? ""}:${fieldName}`];
  return scopedDescription ?? TECHNICAL_FACT_LABEL_DESCRIPTIONS[fieldName] ?? fieldName;
}

const TECHNICAL_FACT_LABEL_DESCRIPTIONS: Record<string, string> = {
  "TECHNICAL_SHEET:component_dimensions":
    "Extraire les dimensions d’un composant important : plateau, piètement, cadre, assise, manche, lame, toile, roue ou bac. Conserver unités et tolérances. Ne pas extraire les dimensions globales du produit fini ni du colis.",
  "TECHNICAL_SHEET:dimension_depth":
    "Extraire la profondeur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la deuxième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant.",
  "TECHNICAL_SHEET:dimension_height":
    "Extraire la hauteur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la troisième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire la hauteur de colis.",
  "TECHNICAL_SHEET:dimension_set_raw":
    "Extraire la ligne ou cellule complète qui donne les dimensions du produit fini avec ordre et unité : L/P/H, L x P x H, largeur/profondeur/hauteur, mm, cm ou m. Ne pas convertir. Ne pas extraire dimensions colis ou composant.",
  "TECHNICAL_SHEET:dimension_width":
    "Extraire la largeur ou longueur principale du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la première valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant.",
  "TECHNICAL_SHEET:feature_or_accessory":
    "Extraire les fonctionnalités ou accessoires techniques écrits : passage parasol, patins, poignée, lame, housse, verrouillage, batterie, réglage.",
  "TECHNICAL_SHEET:finish_primary":
    "Extraire la finition principale : huile, peinture, poudre, couleur, RAL, traitement de surface ou aspect. Ne pas transformer en promesse de durabilité.",
  "TECHNICAL_SHEET:material_primary":
    "Extraire la matière principale du produit ou de la partie dominante. Inclure essence, grade, alliage ou nom scientifique si présents. Ne rien inventer.",
  "TECHNICAL_SHEET:material_secondary":
    "Extraire les matières secondaires structurantes : piètement, cadre, visserie, manche, lame, textile, batterie. Inclure grade ou finition si écrit.",
  "TECHNICAL_SHEET:product_name":
    "Extraire le nom ou la désignation produit exacte couverte par la fiche technique. Prendre le nom le plus spécifique. Ne pas extraire une famille générique ni un autre produit cité.",
  "TECHNICAL_SHEET:quality_control_points":
    "Extraire les critères de contrôle qualité explicitement listés : stabilité, jeu, tolérance, nettoyage, conformité atelier. Garder les formulations techniques.",
  "TECHNICAL_SHEET:sku":
    "Extraire la référence produit, SKU ou code article exact. Conserver lettres, chiffres et tirets. Ne pas confondre avec lot, révision ou tampon documentaire.",
  "TECHNICAL_SHEET:technical_claim_limits":
    "Extraire les notes qui limitent l’usage marketing des données techniques : absence de garantie permanente, entretien limité, usage non absolu. Ne pas créer de restriction absente.",
  "TECHNICAL_SHEET:usage_capacity":
    "Extraire la capacité d’usage explicitement indiquée : nombre de places, charge, volume, surface couverte ou cadence recommandée. Ne pas déduire depuis les dimensions.",
  "TECHNICAL_SHEET:weight":
    "Extraire le poids du produit hors emballage exactement comme écrit. Conserver l’unité source, la tolérance ou la plage si présentes. Ne pas convertir. Ne pas extraire le poids du colis, de la palette ou de l’emballage.",
  "MATERIAL_SPECIFICATION:assembly_site":
    "Extraire le site d’assemblage, fabrication ou pays d’origine s’il est explicitement écrit. Ne pas déduire depuis une langue ou un code.",
  "MATERIAL_SPECIFICATION:certificate_valid_until":
    "Extraire la date de validité, expiration ou prochaine vérification. Ne pas extraire la date d’émission si aucune validité n’est indiquée.",
  "MATERIAL_SPECIFICATION:certification_claim_type":
    "Extraire le type exact de revendication certifiée, par exemple FSC Mix Credit. Ne jamais transformer en claim plus fort comme 100 % FSC.",
  "MATERIAL_SPECIFICATION:chain_of_custody_code":
    "Extraire le code de chaîne de contrôle, CoC ou audit associé. Conserver le format exact et ne pas le confondre avec une licence de marque.",
  "MATERIAL_SPECIFICATION:covered_component":
    "Extraire les composants explicitement couverts par la preuve ou certification. Ne pas inclure les composants seulement listés ou exclus.",
  "MATERIAL_SPECIFICATION:eco_certifications":
    "Extraire les certifications ou preuves environnementales explicitement valides : FSC, PEFC, SVLK, FLEGT, REACH, RoHS, recyclé, origine contrôlée.",
  "MATERIAL_SPECIFICATION:excluded_component":
    "Extraire les composants explicitement exclus du périmètre de certification ou d’attestation. Garder la formulation précise.",
  "MATERIAL_SPECIFICATION:legality_export_reference":
    "Extraire les références de légalité export ou traçabilité, par exemple SVLK, FLEGT ou batch export. Conserver le code complet.",
  "MATERIAL_SPECIFICATION:license_or_certificate_code":
    "Extraire les codes de licence, certificat, audit ou conformité. Conserver lettres, tirets et chiffres. Ne pas fusionner plusieurs codes.",
  "MATERIAL_SPECIFICATION:material_origin":
    "Extraire l’origine déclarée de la matière : pays, plantation, provenance, lot ou légalité export. Ne pas inventer depuis le fournisseur.",
  "MATERIAL_SPECIFICATION:material_primary":
    "Extraire la matière, essence, alliage ou composition principale déclarée. Inclure nom scientifique, grade ou origine si présents.",
  "MATERIAL_SPECIFICATION:product_name":
    "Extraire le produit couvert par l’attestation matière ou conformité. Ne pas extraire un produit mentionné comme exemple, exclusion ou référence secondaire.",
  "MATERIAL_SPECIFICATION:sku":
    "Extraire le SKU, référence article ou code produit concerné par l’attestation. Conserver le format exact. Ne pas confondre avec lot ou certificat.",
  "MATERIAL_SPECIFICATION:supplier_name":
    "Extraire le fournisseur, fabricant, site ou organisme émetteur de la déclaration. Ne pas extraire la marque commerciale si elle n’est pas l’émetteur.",
  "MATERIAL_SPECIFICATION:unsupported_claims":
    "Extraire les mentions que le document interdit ou ne permet pas d’affirmer : 100 % FSC, zéro entretien, garantie permanente, matériau certifié à tort.",
  "ASSEMBLY_NOTICE:assembly_constraints":
    "Extraire les contraintes de montage qui conditionnent la qualité ou la sécurité : support, ordre, jeu, serrage progressif, interdictions, tolérances.",
  "ASSEMBLY_NOTICE:assembly_people_required":
    "Extraire le nombre de personnes ou opérateurs nécessaires au montage. Conserver la formulation source, par exemple 2 adultes.",
  "ASSEMBLY_NOTICE:assembly_product_ref":
    "Extraire la référence de colis, article, notice ou version de montage. Conserver le format exact. Ne pas confondre avec le SKU commercial.",
  "ASSEMBLY_NOTICE:assembly_steps":
    "Extraire la séquence opératoire dans l’ordre : préparer, présenter, équerrer, serrer, régler, contrôler. Garder verbes et contraintes clés.",
  "ASSEMBLY_NOTICE:assembly_time":
    "Extraire le temps de montage indiqué ou constaté exactement comme écrit. Conserver l’unité source et la plage si présentes. Ne pas convertir. Ne pas additionner des étapes si aucun total n’est écrit.",
  "ASSEMBLY_NOTICE:clearance_or_tolerance":
    "Extraire les jeux, tolérances ou écarts acceptés : diagonales, jeu bois/métal, écart de montage, distance minimale. Conserver unités et tolérances. Ne pas convertir.",
  "ASSEMBLY_NOTICE:final_quality_check":
    "Extraire les contrôles finaux demandés après montage : stabilité, hauteur finie, patins, serrage, alignement, surface plane.",
  "ASSEMBLY_NOTICE:hardware_list":
    "Extraire la quincaillerie : vis, rondelles, inserts, patins, sachets. Inclure dimensions et quantités si disponibles. Ne pas extraire les outils.",
  "ASSEMBLY_NOTICE:max_torque":
    "Extraire le couple de serrage maximum ou recommandé exactement comme écrit. Conserver l’unité source, par exemple N·m. Ne pas convertir. Ne pas extraire un diamètre, une taille ou une référence de vis.",
  "ASSEMBLY_NOTICE:parts_list":
    "Extraire la liste des pièces principales à assembler : structure, cadre, pieds, assise, manche, lame, toile, roues, bac ou modules. Inclure quantités si écrites. Ne pas inclure les étapes.",
  "ASSEMBLY_NOTICE:product_name":
    "Extraire le nom, article ou référence du produit concerné par la notice. Ne pas extraire le nom d’une pièce ou d’un composant isolé.",
  "ASSEMBLY_NOTICE:prohibited_actions":
    "Extraire les actions explicitement interdites : visseuse à choc, reperçage, collage, levage incorrect, usage abrasif. Ne pas reformuler en bénéfice.",
  "ASSEMBLY_NOTICE:required_tool":
    "Extraire les outils nécessaires ou fournis : clé Allen, tournevis, maillet, gabarit, niveau. Ne pas extraire la visserie comme outil.",
  "ASSEMBLY_NOTICE:use_or_safety_warning":
    "Extraire les avertissements d’usage ou sécurité après montage. Ne pas transformer en argument marketing ni inventer de risque absent.",
};

function formatGcpConfidence(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "Non renseigné";
  }

  return `${truncateDecimal(value * 100, 2).toFixed(2)} %`;
}

function technicalClassificationStatus(classification: TechnicalClassification): {
  label: string;
  tone: "danger" | "neutral" | "success" | "warning";
} {
  if (!classification.is_blocking) {
    return { label: "Accepté", tone: "success" };
  }

  if (isMixedTechnicalDossierClassification(classification)) {
    return { label: "Refusé", tone: "danger" };
  }

  if (classification.blocking_reason === "OUT_OF_SCOPE") {
    return { label: "Refusé", tone: "danger" };
  }

  return {
    label: "À vérifier",
    tone: "warning",
  };
}

function isOutOfScopeClassification(classification: TechnicalClassification) {
  return classification.document_type === "OUT_OF_SCOPE_DOCUMENT";
}

function isMixedTechnicalDossierClassification(classification: TechnicalClassification) {
  return classification.document_type === "MIXED_TECHNICAL_DOSSIER";
}

function truncateDecimal(value: number, decimals: number) {
  const factor = 10 ** decimals;
  return Math.trunc(value * factor) / factor;
}

function dedupeTechnicalSources(sources: TechnicalSource[]) {
  const sourcesByFileName = new Map<string, TechnicalSource>();

  for (const source of sources) {
    sourcesByFileName.set(source.original_file_name, source);
  }

  return Array.from(sourcesByFileName.values());
}
