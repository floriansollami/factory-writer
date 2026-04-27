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
} from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";

import { AxolotlLogo } from "@/components/brand/AxolotlLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ProductSheetFlowProgress } from "@/features/product-sheets/ProductSheetFlowProgress";
import {
  CompactProviderMetadata,
  type ProductStepMetadataField,
} from "@/features/product-sheets/ProductStepMetadata";
import {
  TechnicalExtractionResultsDisclosure,
  technicalFactLabelDescription,
} from "@/features/product-sheets/TechnicalExtractionResultsDisclosure";
import {
  ResolveTechnicalReviewCaseDialog,
  TechnicalReviewCasesPanel,
} from "@/features/product-sheets/TechnicalReviewCasesPanel";
import { TechnicalSourcesUploadDialog } from "@/features/product-sheets/TechnicalSourcesUploadDialog";
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
  technicalDocumentTypeLabel,
} from "@/features/product-sheets/productSheetUtils";
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
    onSuccess: async (result) => {
      queryClient.setQueryData<ProductOverview>(
        ["product-overview", productId],
        (previous) =>
          previous
            ? {
                ...previous,
                product: result.product,
                run: result.run,
                sources: result.sources,
                technical_collection: {
                  id: result.collection_id,
                  kind: "TECHNICAL_DOSSIER",
                  statut: "EN_COURS",
                },
              }
            : previous,
      );
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
                factCandidates={overview.fact_candidates}
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
                  step.id === "deterministic-validation" ||
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
  factCandidates = [],
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
  factCandidates?: TechnicalFactCandidate[];
  generationReadiness?: ProductOverview["generation_readiness"];
  hideStepMetadata?: boolean;
  onReplaceSources?: () => void;
  productId: string;
  step: ProductAnalysisStep;
  validationReviewCases?: TechnicalReviewCase[];
}) {
  const isRunning = step.status === "running";
  const hasStepResults =
    classificationResults !== undefined ||
    extractionResults !== undefined ||
    generationReadiness !== undefined;
  const showStepEta =
    step.eta !== undefined &&
    !hasStepResults &&
    (step.status === "running" || step.status === "pending");

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
            factCandidates={factCandidates}
            generationReadiness={generationReadiness}
            productId={productId}
            reviewCases={validationReviewCases}
            sources={extractionSources}
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
        {showStepEta ? (
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
  factCandidates,
  generationReadiness,
  productId,
  reviewCases,
  sources,
}: {
  factCandidates: TechnicalFactCandidate[];
  generationReadiness: NonNullable<ProductOverview["generation_readiness"]>;
  productId: string;
  reviewCases: TechnicalReviewCase[];
  sources: TechnicalSource[];
}) {
  const [selectedCase, setSelectedCase] = useState<TechnicalReviewCase | null>(null);
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const checks = sortValidationChecksBySource(
    validationFieldChecks(generationReadiness),
    sourceById,
    factCandidates,
  );
  const checkGroups = groupValidationChecksBySource(
    checks,
    sourceById,
    factCandidates,
    reviewCases,
  );
  const visibleBlockingCount = checks.filter(
    (check) => check.status === "BLOCKED",
  ).length;
  const hasBlocking = visibleBlockingCount > 0;
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
        </summary>

        <div className="mt-3 space-y-3">
          {checkGroups.map((group) => (
            <details
              key={group.key}
              className="group/validation-section overflow-hidden rounded-[1.35rem] bg-white/60 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]"
            >
              <summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 border-b border-black/5 bg-[var(--color-surface-raised)]/45 px-3 py-2 transition hover:bg-[var(--color-sage-soft)]/40 [&::-webkit-details-marker]:hidden">
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="size-0 shrink-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current text-[var(--color-forest)] transition-transform group-open/validation-section:rotate-90"
                  />
                  <span
                    className="truncate text-[0.68rem] font-bold uppercase tracking-[0.14em] text-[var(--color-forest)]"
                    title={group.sourceTitle}
                  >
                    {group.label}
                  </span>
                </span>
                <Badge tone={group.blockingCount > 0 ? "danger" : group.ignoredCount > 0 ? "warning" : "success"}>
                  {group.blockingCount > 0
                    ? `${group.blockingCount} à corriger`
                    : group.ignoredCount > 0
                      ? `${group.ignoredCount} ignoré${group.ignoredCount > 1 ? "s" : ""}`
                      : `${group.checks.length} validé${group.checks.length > 1 ? "s" : ""}`}
                </Badge>
              </summary>

              <div className="grid grid-cols-[minmax(11rem,0.75fr)_minmax(18rem,1.45fr)_5.5rem_9.5rem_6.5rem] gap-4 border-b border-black/5 px-3 py-2 text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-xl:hidden">
                <span>Label</span>
                <span>Valeur retenue</span>
                <span>Score</span>
                <span className="text-center">Statut</span>
                <span className="text-right">Action</span>
              </div>

              {group.checks.map((check) => {
                const reviewCase = findReviewCaseForCheck(reviewCases, check);
                const rowTone = validationCheckTone(check);
                const valueLabel = validationCheckValueLabel(check);
                const score = validationCheckScore(check);
                const hasRetainedValue = check.selectedValues.length > 0;
                const rejectedCandidates = validationRejectedCandidates(
                  check,
                  reviewCases,
                );

                return (
                  <div key={`${check.fieldName}-${check.status}`} className="border-b border-black/5 last:border-b-0">
                    <div
                      className={cn(
                        "grid grid-cols-[minmax(11rem,0.75fr)_minmax(18rem,1.45fr)_5.5rem_9.5rem_6.5rem] items-center gap-4 px-3 py-2.5 max-xl:grid-cols-[minmax(0,1fr)_auto] max-xl:gap-y-2",
                        rowTone === "danger" && "bg-[var(--color-error-soft)]/45",
                        rowTone === "warning" && "bg-[var(--color-gold-soft)]/45",
                        rowTone === "success" && "bg-[var(--color-sage-soft)]/35",
                        rowTone === "neutral" && "bg-white/45",
                      )}
                    >
                      <ValidationLabelCell
                        check={check}
                        factCandidates={factCandidates}
                        reviewCases={reviewCases}
                        sourceById={sourceById}
                      />
                      <ValidationValueCell
                        showDash={!hasRetainedValue && rowTone === "danger"}
                        valueLabel={valueLabel}
                      />
                      <p className="text-xs font-semibold text-[var(--color-ink)]">
                        {hasRetainedValue || rowTone !== "danger"
                          ? formatGcpConfidence(score)
                          : "-"}
                      </p>
                      <div className="justify-self-center">
                        <ValidationStatusBadge check={check} tone={rowTone} />
                      </div>
                      <div className="min-w-0 justify-self-end">
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
                            -
                          </span>
                        )}
                      </div>
                    </div>
                    {rowTone === "danger" && rejectedCandidates.length > 0 ? (
                      <RejectedValidationCandidates candidates={rejectedCandidates} />
                    ) : null}
                  </div>
                );
              })}
            </details>
          ))}
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
        relatedReviewCases={relatedOpenReviewCases(selectedCase, reviewCases)}
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
        Profil de prérequis fiche produit
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
                      <Badge
                        tone={
                          isFact
                            ? "success"
                            : item.validation_status === "NEEDS_REVIEW"
                              ? "warning"
                              : "neutral"
                        }
                      >
                        {isFact ? "Validé" : technicalFactCandidateStatusLabel(item.validation_status)}
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

function technicalFactCandidateStatusLabel(status: string) {
  if (status === "EXTRACTED") {
    return "Extrait";
  }
  if (status === "NEEDS_REVIEW") {
    return "À vérifier";
  }
  if (status === "PROMOTED") {
    return "Promu";
  }
  if (status === "REJECTED") {
    return "Rejeté";
  }
  return formatCode(status);
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
  level: string;
  status: string;
  selectedValues: string[];
  selectedCandidateIndexes: number[];
  selectedSources: Array<Record<string, unknown>>;
  confidence: number | null;
  threshold: number | null;
  blockingReason: string | null;
  alternatives: Array<Record<string, unknown>>;
};

type RejectedValidationCandidate = {
  confidence: number | null;
  reason: string;
  value: string;
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
        level: stringRecordValue(rawCheck, "level") ?? "REQUIRED",
        status: stringRecordValue(rawCheck, "status") ?? "UNKNOWN",
        selectedValues: stringArrayRecordValue(rawCheck, "selected_values"),
        selectedCandidateIndexes: numberArrayRecordValue(rawCheck, "selected_candidate_indexes"),
        selectedSources: recordArrayValue(rawCheck, "selected_sources"),
        confidence: numberRecordValue(rawCheck, "confidence"),
        threshold: numberRecordValue(rawCheck, "threshold"),
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
  if (isIgnoredValidationCheck(check)) {
    return null;
  }

  if (check.status !== "BLOCKED" && check.status !== "WARNING") {
    return null;
  }

  return (
    reviewCases.find(
      (reviewCase) =>
        reviewCase.field_name === check.fieldName &&
        ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
    ) ?? null
  );
}

function relatedOpenReviewCases(
  reviewCase: TechnicalReviewCase | null,
  reviewCases: TechnicalReviewCase[],
) {
  if (reviewCase === null || reviewCase.field_name === null) {
    return reviewCase === null ? [] : [reviewCase];
  }

  const relatedCases = reviewCases.filter(
    (candidateReviewCase) =>
      candidateReviewCase.field_name === reviewCase.field_name &&
      ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(candidateReviewCase.status) &&
      candidateReviewCase.case_type !== "CLASSIFICATION_UNCERTAIN",
  );

  return relatedCases.length > 0 ? relatedCases : [reviewCase];
}

function ValidationStatusBadge({
  check,
  tone,
}: {
  check: ValidationFieldCheck;
  tone: "danger" | "neutral" | "success" | "warning";
}) {
  return (
    <Badge className="w-fit whitespace-nowrap" tone={tone}>
      {validationCheckStatusLabel(check)}
    </Badge>
  );
}

function RejectedValidationCandidates({
  candidates,
}: {
  candidates: RejectedValidationCandidate[];
}) {
  const visibleCandidates = candidates.slice(0, 3);
  const hiddenCount = Math.max(candidates.length - visibleCandidates.length, 0);
  const candidateCount = candidates.length;

  return (
    <details className="group/rejected-candidates bg-[var(--color-error-soft)]/30 px-3 pb-3 pt-1">
      <summary className="flex w-fit cursor-pointer list-none items-center gap-2 rounded-xl px-2 py-1 text-[0.68rem] font-bold uppercase tracking-[0.12em] text-[var(--color-error)] transition hover:bg-white/45 [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden="true"
          className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open/rejected-candidates:rotate-90"
        />
        {candidateCount} valeur{candidateCount > 1 ? "s" : ""} détectée{candidateCount > 1 ? "s" : ""}
      </summary>
      <div className="rounded-2xl bg-white/55 px-3 py-2.5 shadow-[inset_0_0_0_1px_rgba(128,60,45,0.08)]">
        <p className="text-[0.66rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
          Valeurs détectées non retenues
        </p>
        <div className="mt-2 grid gap-1.5">
          {visibleCandidates.map((candidate, index) => (
            <div
              key={`${candidate.value}-${candidate.confidence ?? "none"}-${index}`}
              className="flex items-start justify-between gap-4 rounded-xl bg-white/55 px-2.5 py-2 text-xs max-lg:flex-col max-lg:gap-1"
            >
              <p className="min-w-0 flex-1 font-semibold leading-5 text-[var(--color-forest)]">
                {candidate.value}
              </p>
              <div className="flex shrink-0 flex-wrap items-center justify-end gap-x-2 gap-y-1 text-right max-lg:justify-start max-lg:text-left">
                <span className="font-semibold text-[var(--color-ink)]">
                  {formatGcpConfidence(candidate.confidence)}
                </span>
                <span className="text-[var(--color-muted)]">·</span>
                <span className="font-semibold text-[var(--color-error)]">
                  {candidate.reason}
                </span>
              </div>
            </div>
          ))}
        </div>
        {hiddenCount > 0 ? (
          <p className="mt-2 text-xs font-semibold text-[var(--color-muted)]">
            + {hiddenCount} autre{hiddenCount > 1 ? "s" : ""} valeur{hiddenCount > 1 ? "s" : ""} détectée{hiddenCount > 1 ? "s" : ""}
          </p>
        ) : null}
      </div>
    </details>
  );
}

function ValidationLabelCell({
  check,
  factCandidates,
  reviewCases,
  sourceById,
}: {
  check: ValidationFieldCheck;
  factCandidates: TechnicalFactCandidate[];
  reviewCases: TechnicalReviewCase[];
  sourceById: Map<string, TechnicalSource>;
}) {
  const description = technicalFactLabelDescription(
    check.fieldName,
    validationCheckDocumentType(check, factCandidates, reviewCases, sourceById),
  );

  return (
    <div className="min-w-0">
      <p
        className="cursor-help break-words text-sm font-semibold leading-5 text-[var(--color-ink)]"
        title={description}
      >
        {check.fieldName}
      </p>
      <p className="mt-0.5 text-[0.58rem] font-bold uppercase tracking-[0.12em] text-[var(--color-muted)]">
        {validationRequirementLevelLabel(check.level)}
      </p>
    </div>
  );
}

function ValidationValueCell({
  showDash = false,
  valueLabel,
}: {
  showDash?: boolean;
  valueLabel: string;
}) {
  if (showDash) {
    return (
      <p className="text-xs font-semibold text-[var(--color-forest)]">
        -
      </p>
    );
  }

  return (
    <div className="min-w-0">
      <p className="break-words text-xs font-semibold leading-5 text-[var(--color-forest)]">
        {valueLabel}
      </p>
    </div>
  );
}

function validationCheckSourceRefs(
  check: ValidationFieldCheck,
  factCandidates: TechnicalFactCandidate[],
) {
  const sourceRecords =
    check.selectedSources.length > 0 ? check.selectedSources : check.alternatives;
  const sourcesById = new Map<
    string,
    { sourceId: string | null; sourceDocumentType: string | null }
  >();

  for (const candidateIndex of check.selectedCandidateIndexes) {
    const candidate = factCandidates[candidateIndex];
    if (candidate === undefined) {
      continue;
    }

    sourcesById.set(candidate.source_id, {
      sourceId: candidate.source_id,
      sourceDocumentType: null,
    });
  }

  for (const sourceRecord of sourceRecords) {
    const sourceId = stringRecordValue(sourceRecord, "source_id");
    const sourceDocumentType = stringRecordValue(sourceRecord, "source_document_type");
    const key = sourceId ?? `${sourceDocumentType ?? "unknown"}-${sourcesById.size}`;

    if (!sourcesById.has(key)) {
      sourcesById.set(key, { sourceId, sourceDocumentType });
    }
  }

  return Array.from(sourcesById.values());
}

function validationCheckDocumentType(
  check: ValidationFieldCheck,
  factCandidates: TechnicalFactCandidate[],
  reviewCases: TechnicalReviewCase[],
  sourceById: Map<string, TechnicalSource>,
) {
  const sourceRef = validationCheckSourceRefs(check, factCandidates)[0];
  const sourceDocumentType = sourceRef?.sourceId
    ? sourceById.get(sourceRef.sourceId)?.document_type
    : null;

  if (sourceDocumentType) {
    return sourceDocumentType;
  }

  if (sourceRef?.sourceDocumentType) {
    return sourceRef.sourceDocumentType;
  }

  const reviewCase = reviewCases.find(
    (candidateReviewCase) => candidateReviewCase.field_name === check.fieldName,
  );
  const reviewCaseSource = reviewCase?.source_id ? sourceById.get(reviewCase.source_id) : null;

  if (reviewCaseSource?.document_type) {
    return reviewCaseSource.document_type;
  }

  const metadata = isRecord(reviewCase?.metadata_json) ? reviewCase.metadata_json : null;
  return metadata ? stringRecordValue(metadata, "source_document_type") : null;
}

function validationRejectedCandidates(
  check: ValidationFieldCheck,
  reviewCases: TechnicalReviewCase[],
): RejectedValidationCandidate[] {
  const alternatives = check.alternatives
    .map((alternative) => rejectedCandidateFromRecord(alternative, check))
    .filter((candidate): candidate is RejectedValidationCandidate => candidate !== null);

  const fallbackReviewCases = reviewCases
    .filter(
      (reviewCase) =>
        reviewCase.field_name === check.fieldName &&
        ["A_TRAITER", "DOCUMENT_A_REMPLACER"].includes(reviewCase.status),
    )
    .map((reviewCase) => rejectedCandidateFromReviewCase(reviewCase, check))
    .filter((candidate): candidate is RejectedValidationCandidate => candidate !== null);

  const candidates = alternatives.length > 0 ? alternatives : fallbackReviewCases;
  const deduped = new Map<string, RejectedValidationCandidate>();

  for (const candidate of candidates) {
    const key = `${candidate.value}-${candidate.confidence ?? "none"}`;
    deduped.set(key, candidate);
  }

  return Array.from(deduped.values()).sort(
    (left, right) => (right.confidence ?? -1) - (left.confidence ?? -1),
  );
}

function rejectedCandidateFromRecord(
  record: Record<string, unknown>,
  check: ValidationFieldCheck,
): RejectedValidationCandidate | null {
  const value = validationRecordValue(record);
  if (value === null) {
    return null;
  }

  const confidence = numberRecordValue(record, "confidence");
  const threshold = check.threshold;

  return {
    confidence,
    reason: validationRejectedReason(confidence, threshold, check.blockingReason),
    value,
  };
}

function rejectedCandidateFromReviewCase(
  reviewCase: TechnicalReviewCase,
  check: ValidationFieldCheck,
): RejectedValidationCandidate | null {
  const metadata = isRecord(reviewCase.metadata_json) ? reviewCase.metadata_json : {};
  const value =
    reviewCase.detected_value ??
    validationRecordValue(metadata) ??
    stringRecordValue(metadata, "detected_value");

  if (value === null) {
    return null;
  }

  const confidence =
    numberRecordValue(metadata, "extractor_confidence") ??
    numberRecordValue(metadata, "confidence");
  const threshold = numberRecordValue(metadata, "threshold") ?? check.threshold;

  return {
    confidence,
    reason: validationRejectedReason(confidence, threshold, reviewCase.case_type),
    value: reviewCase.detected_unit ? `${value} ${reviewCase.detected_unit}` : value,
  };
}

function validationRecordValue(record: Record<string, unknown>) {
  const value =
    stringRecordValue(record, "normalized_value") ??
    stringRecordValue(record, "raw_value") ??
    stringRecordValue(record, "detected_value");
  const unit = stringRecordValue(record, "unit") ?? stringRecordValue(record, "detected_unit");

  return value ? `${value}${unit && !value.includes(unit) ? ` ${unit}` : ""}` : null;
}

function validationRejectedReason(
  confidence: number | null,
  threshold: number | null,
  fallbackReason: string | null,
) {
  if (confidence !== null && threshold !== null && confidence < threshold) {
    return `Sous le seuil ${formatGcpConfidence(threshold)}`;
  }

  if (fallbackReason === "VALUE_OUT_OF_RANGE") {
    return "Hors borne";
  }
  if (fallbackReason === "CONTRADICTION") {
    return "Conflit";
  }

  return fallbackReason ? formatCode(fallbackReason) : "Non retenue";
}

const VALIDATION_SOURCE_TYPE_ORDER = [
  "TECHNICAL_SHEET",
  "MATERIAL_SPECIFICATION",
  "ASSEMBLY_NOTICE",
];

type ValidationCheckGroup = {
  blockingCount: number;
  checks: ValidationFieldCheck[];
  ignoredCount: number;
  key: string;
  label: string;
  rank: number;
  sourceTitle?: string;
};

function groupValidationChecksBySource(
  checks: ValidationFieldCheck[],
  sourceById: Map<string, TechnicalSource>,
  factCandidates: TechnicalFactCandidate[],
  reviewCases: TechnicalReviewCase[],
): ValidationCheckGroup[] {
  const groups = new Map<
    string,
    Omit<ValidationCheckGroup, "blockingCount" | "ignoredCount" | "sourceTitle"> & {
      fileNames: Set<string>;
    }
  >();

  for (const check of checks) {
    const sourceRefs = validationCheckSourceRefs(check, factCandidates);
    const documentType =
      validationCheckGroupDocumentType(sourceRefs, sourceById) ??
      validationCheckDocumentType(check, factCandidates, reviewCases, sourceById);
    const key = documentType ?? "TRANSVERSAL";
    const rank = validationSourceTypeRank(documentType);
    const group =
      groups.get(key) ??
      {
        checks: [],
        fileNames: new Set<string>(),
        key,
        label: documentType ? technicalDocumentTypeLabel(documentType) : "Contrôles transverses",
        rank,
      };

    group.checks.push(check);
    for (const fileName of validationCheckSourceFileNames(
      check,
      sourceRefs,
      reviewCases,
      sourceById,
    )) {
      group.fileNames.add(fileName);
    }
    groups.set(key, group);
  }

  return Array.from(groups.values())
    .map((group) => ({
      blockingCount: group.checks.filter(
        (check) => check.status === "BLOCKED",
      ).length,
      checks: group.checks,
      ignoredCount: group.checks.filter(isIgnoredValidationCheck).length,
      key: group.key,
      label: group.label,
      rank: group.rank,
      sourceTitle:
        group.fileNames.size > 0 ? Array.from(group.fileNames).join("\n") : undefined,
    }))
    .sort((left, right) => {
      const leftBlockingRank = left.blockingCount > 0 ? 0 : left.ignoredCount > 0 ? 1 : 2;
      const rightBlockingRank = right.blockingCount > 0 ? 0 : right.ignoredCount > 0 ? 1 : 2;

      if (leftBlockingRank !== rightBlockingRank) {
        return leftBlockingRank - rightBlockingRank;
      }

      if (left.rank !== right.rank) {
        return left.rank - right.rank;
      }

      return left.label.localeCompare(right.label, "fr");
    });
}

function validationCheckSourceFileNames(
  check: ValidationFieldCheck,
  sourceRefs: Array<{ sourceId: string | null; sourceDocumentType: string | null }>,
  reviewCases: TechnicalReviewCase[],
  sourceById: Map<string, TechnicalSource>,
) {
  const fileNames = new Set<string>();

  for (const sourceRef of sourceRefs) {
    const fileName = sourceById.get(sourceRef.sourceId ?? "")?.original_file_name;
    if (fileName) {
      fileNames.add(fileName);
    }
  }

  for (const reviewCase of reviewCases) {
    if (reviewCase.field_name !== check.fieldName) {
      continue;
    }

    const sourceId =
      reviewCase.source_id ??
      (isRecord(reviewCase.metadata_json)
        ? stringRecordValue(reviewCase.metadata_json, "source_id")
        : null);
    const fileName = sourceId ? sourceById.get(sourceId)?.original_file_name : undefined;
    if (fileName) {
      fileNames.add(fileName);
    }
  }

  return Array.from(fileNames);
}

function validationCheckGroupDocumentType(
  sourceRefs: Array<{ sourceId: string | null; sourceDocumentType: string | null }>,
  sourceById: Map<string, TechnicalSource>,
) {
  const documentTypes = sourceRefs
    .map((sourceRef) => {
      const sourceDocumentType = sourceRef.sourceId
        ? sourceById.get(sourceRef.sourceId)?.document_type
        : null;
      return sourceDocumentType ?? sourceRef.sourceDocumentType;
    })
    .filter((documentType): documentType is string => documentType !== null);

  return documentTypes.sort(
    (left, right) => validationSourceTypeRank(left) - validationSourceTypeRank(right),
  )[0] ?? null;
}

function validationSourceTypeRank(documentType: string | null) {
  if (documentType === null) {
    return VALIDATION_SOURCE_TYPE_ORDER.length;
  }

  const index = VALIDATION_SOURCE_TYPE_ORDER.indexOf(documentType);
  return index === -1 ? VALIDATION_SOURCE_TYPE_ORDER.length : index;
}

function sortValidationChecksBySource(
  checks: ValidationFieldCheck[],
  sourceById: Map<string, TechnicalSource>,
  factCandidates: TechnicalFactCandidate[],
) {
  return [...checks].sort((left, right) => {
    const leftStatusRank = validationCheckStatusRank(left);
    const rightStatusRank = validationCheckStatusRank(right);

    if (leftStatusRank !== rightStatusRank) {
      return leftStatusRank - rightStatusRank;
    }

    const leftSourceRank = validationCheckSourceRank(left, sourceById, factCandidates);
    const rightSourceRank = validationCheckSourceRank(right, sourceById, factCandidates);

    if (leftSourceRank !== rightSourceRank) {
      return leftSourceRank - rightSourceRank;
    }

    return left.fieldName.localeCompare(right.fieldName, "fr");
  });
}

function validationCheckStatusRank(check: ValidationFieldCheck) {
  if (check.status === "BLOCKED") {
    return 0;
  }
  if (isIgnoredValidationCheck(check)) {
    return 1;
  }
  if (check.status === "WARNING") {
    return 2;
  }
  if (check.status === "PASSED") {
    return 3;
  }
  if (check.status === "SKIPPED") {
    return 4;
  }
  return 5;
}

function validationCheckSourceRank(
  check: ValidationFieldCheck,
  sourceById: Map<string, TechnicalSource>,
  factCandidates: TechnicalFactCandidate[],
) {
  const documentTypes = validationCheckSourceRefs(check, factCandidates)
    .map((sourceRef) => {
      const sourceDocumentType = sourceRef.sourceId
        ? sourceById.get(sourceRef.sourceId)?.document_type
        : null;
      return sourceDocumentType ?? sourceRef.sourceDocumentType;
    })
    .filter((documentType): documentType is string => documentType !== null);

  if (documentTypes.length === 0) {
    return VALIDATION_SOURCE_TYPE_ORDER.length;
  }

  return Math.min(
    ...documentTypes.map((documentType) => validationSourceTypeRank(documentType)),
  );
}

function validationCheckTone(
  check: ValidationFieldCheck,
): "danger" | "neutral" | "success" | "warning" {
  if (check.status === "BLOCKED") {
    return "danger";
  }
  if (isIgnoredValidationCheck(check)) {
    return "warning";
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
    if (check.blockingReason === "NO_VALID_CANDIDATE") {
      return "Invalide";
    }
    return check.blockingReason ? formatCode(check.blockingReason) : "Bloqué";
  }
  if (isIgnoredValidationCheck(check)) {
    return "Ignoré";
  }
  if (check.status === "WARNING") {
    return "À surveiller";
  }
  if (check.status === "PASSED") {
    return "Validé";
  }
  if (check.status === "SKIPPED") {
    if (isIgnoredValidationCheck(check)) {
      return "Ignoré";
    }
    return "Non mentionné";
  }
  return formatCode(check.status);
}

function isIgnoredValidationCheck(check: ValidationFieldCheck) {
  return (
    (check.status === "SKIPPED" && check.blockingReason?.startsWith("IGNORED_")) ||
    (check.status === "WARNING" &&
      check.level === "OPTIONAL" &&
      check.blockingReason === "LOW_CONFIDENCE")
  );
}

function validationRequirementLevelLabel(level: string) {
  if (level === "REQUIRED") {
    return "Obligatoire";
  }
  if (level === "CONDITIONAL") {
    return "Conditionnel";
  }
  if (level === "OPTIONAL") {
    return "Optionnel";
  }
  return formatCode(level);
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

function validationCheckScore(check: ValidationFieldCheck) {
  if (check.confidence !== null) {
    return check.confidence;
  }

  const alternativeScores = check.alternatives
    .map((alternative) => numberRecordValue(alternative, "confidence"))
    .filter((score): score is number => score !== null);

  return alternativeScores.length > 0 ? Math.max(...alternativeScores) : null;
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

function numberArrayRecordValue(record: Record<string, unknown>, key: string): number[] {
  const value = record[key];
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === "number" && Number.isFinite(item))
    : [];
}

function recordArrayValue(record: Record<string, unknown>, key: string): Array<Record<string, unknown>> {
  const value = record[key];
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function formatNullable(value: string | null | undefined) {
  return value && value.length > 0 ? value : "Non renseigné";
}

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
