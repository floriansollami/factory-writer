import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  FileText,
  Flower2,
  Loader2,
} from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ProductAnalysisStatusCard } from "@/features/product-sheets/ProductAnalysisStatusCard";
import { ProductContextReadyCard } from "@/features/product-sheets/ProductContextReadyCard";
import { ProductSheetFlowProgress } from "@/features/product-sheets/ProductSheetFlowProgress";
import { TechnicalReviewCasesPanel } from "@/features/product-sheets/TechnicalReviewCasesPanel";
import { TechnicalSourcesUploadDialog } from "@/features/product-sheets/TechnicalSourcesUploadDialog";
import type { ProductOverview, ProductSheet } from "@/features/product-sheets/schema";
import {
  formatCode,
  formatNullableCode,
  isProductAnalysisActive,
  resolveProductFlowStep,
} from "@/features/product-sheets/productSheetUtils";
import { getProductOverview, listProducts, startTechnicalIngestion } from "@/lib/api";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil admin",
  "Guide de style",
  "Fiches produit",
  "Signaux marketing",
];
const navigableNavItems = new Set(["Accueil admin", "Fiches produit", "Guide de style"]);

type ProductSheetDetailPageProps = {
  onBack: () => void;
  onOpenAdminHome: () => void;
  onOpenMarketingSignals: (productId: string, returnTo: string) => void;
  onOpenProductSheets: () => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  productId: string;
};

export function ProductSheetDetailPage({
  onBack,
  onOpenAdminHome,
  onOpenMarketingSignals,
  onOpenProductSheets,
  onOpenStyleGuide,
  productId,
}: ProductSheetDetailPageProps) {
  const [isUploadDialogOpen, setUploadDialogOpen] = useState(false);
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
                <Flower2 className="size-6" />
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
                    item === "Accueil admin"
                      ? onOpenAdminHome
                      : item === "Guide de style"
                        ? () => onOpenStyleGuide()
                        : item === "Fiches produit"
                          ? onOpenProductSheets
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
              onImportSources={() => setUploadDialogOpen(true)}
              onOpenMarketingSignals={onOpenMarketingSignals}
              onOpenStyleGuide={onOpenStyleGuide}
              onStartIngestion={() => startMutation.mutate()}
              overview={data}
              product={listedProduct}
              startError={startMutation.error}
            />
          )}
        </section>
      </div>

      <TechnicalSourcesUploadDialog
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
  onOpenMarketingSignals,
  onOpenStyleGuide,
  onStartIngestion,
  overview,
  product,
  startError,
}: {
  isStartingIngestion: boolean;
  onBack: () => void;
  onImportSources: () => void;
  onOpenMarketingSignals: (productId: string, returnTo: string) => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  onStartIngestion: () => void;
  overview: ProductOverview;
  product: ProductSheet | null;
  startError: Error | null;
}) {
  const currentStep = resolveProductFlowStep(overview);
  const returnTo = `/product-sheets/${overview.product.id}`;

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-5">
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
          <p className="mt-3 text-sm font-semibold text-[var(--color-muted)]">
            {overview.product.sku} · {formatCode(overview.product.famille_code)} ·{" "}
            {formatNullableCode(overview.product.segment_prix_code)}
          </p>
        </div>
        <Badge tone={overviewStatusTone(overview)}>{overviewStatusLabel(overview)}</Badge>
      </header>

      <section className="mt-7">
        <Card className="bg-[linear-gradient(135deg,#fffdf8,#f1eee4)] p-6">
          <ProductSheetFlowProgress currentStep={currentStep} />
        </Card>
      </section>

      {product !== null && (!product.styleGuideReady || !product.commercialSignalsReady) ? (
        <ProductPrerequisiteNotice
          onOpenMarketingSignals={() => onOpenMarketingSignals(product.id, returnTo)}
          onOpenStyleGuide={() => onOpenStyleGuide(returnTo)}
          product={product}
        />
      ) : null}

      <section className="mt-6 grid grid-cols-[1.05fr_0.95fr] gap-5 max-2xl:grid-cols-1">
        <div className="grid gap-5">
          <ProductAnalysisStatusCard
            isStartingIngestion={isStartingIngestion}
            onImportSources={onImportSources}
            onStartIngestion={onStartIngestion}
            overview={overview}
          />
          {startError ? (
            <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/50 p-4 text-sm font-semibold text-[var(--color-error)]">
              {startError.message}
            </div>
          ) : null}
          <FactsCard overview={overview} />
        </div>

        <div className="grid content-start gap-5">
          <TechnicalReviewCasesPanel
            productId={overview.product.id}
            reviewCases={overview.review_cases}
          />
          <ProductContextReadyCard overview={overview} />
        </div>
      </section>
    </>
  );
}

function ProductPrerequisiteNotice({
  onOpenMarketingSignals,
  onOpenStyleGuide,
  product,
}: {
  onOpenMarketingSignals: () => void;
  onOpenStyleGuide: () => void;
  product: ProductSheet;
}) {
  const isStyleGuideMissing = !product.styleGuideReady;

  return (
    <Card className="mt-5 flex flex-wrap items-center justify-between gap-4 border border-[var(--color-gold-soft)] bg-[rgba(255,249,232,0.72)] p-4">
      <div>
        <p className="text-sm font-bold text-[var(--color-ink)]">
          {isStyleGuideMissing
            ? "Guide de style requis avant génération"
            : "Signaux marketing à vérifier avant génération"}
        </p>
        <p className="mt-1 text-sm text-[var(--color-muted)]">
          {isStyleGuideMissing
            ? "Activez le guide, puis revenez à cette fiche produit."
            : "Vérifiez les données ventes et retours compatibles, puis revenez à cette fiche produit."}
        </p>
      </div>
      <Button
        variant="secondary"
        onClick={isStyleGuideMissing ? onOpenStyleGuide : onOpenMarketingSignals}
      >
        {isStyleGuideMissing ? "Activer le guide de style" : "Préparer les signaux"}
        <ArrowRight className="size-4" />
      </Button>
    </Card>
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

function overviewStatusLabel(overview: ProductOverview) {
  if (overview.product_context_snapshot !== null) {
    return "Contexte prêt";
  }

  if (overview.review_cases.some((reviewCase) => reviewCase.status === "A_TRAITER")) {
    return "À corriger";
  }

  if (overview.run?.statut === "EN_COURS") {
    return "Analyse";
  }

  if (overview.run?.statut === "TERMINE") {
    return "Contexte en préparation";
  }

  if (overview.sources.length > 0) {
    return "PDFs reçus";
  }

  return "Dossiers attendus";
}

function overviewStatusTone(overview: ProductOverview) {
  if (overview.product_context_snapshot !== null) {
    return "success";
  }

  if (overview.review_cases.some((reviewCase) => reviewCase.status === "A_TRAITER")) {
    return "danger";
  }

  if (overview.run?.statut === "EN_COURS" || overview.sources.length > 0) {
    return "warning";
  }

  return "neutral";
}
