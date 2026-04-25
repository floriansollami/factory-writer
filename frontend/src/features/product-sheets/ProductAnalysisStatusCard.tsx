import { Clock3, FileText, Loader2, PlayCircle, UploadCloud } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { ProductOverview } from "@/features/product-sheets/schema";
import { formatCode, isProductAnalysisActive } from "@/features/product-sheets/productSheetUtils";

type ProductAnalysisStatusCardProps = {
  isStartingIngestion: boolean;
  onImportSources: () => void;
  onStartIngestion: () => void;
  overview: ProductOverview;
};

export function ProductAnalysisStatusCard({
  isStartingIngestion,
  onImportSources,
  onStartIngestion,
  overview,
}: ProductAnalysisStatusCardProps) {
  const elapsedSeconds = useElapsedSeconds(isProductAnalysisActive(overview.run));
  const hasSources = overview.sources.length > 0;
  const hasRun = overview.run !== null;

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-start justify-between gap-4 p-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
            Préparation
          </p>
          <CardTitle className="mt-2">Dossiers techniques</CardTitle>
        </div>
        {!hasSources ? (
          <Button onClick={onImportSources}>
            <UploadCloud className="size-4" />
            Importer les dossiers
          </Button>
        ) : !hasRun ? (
          <Button onClick={onStartIngestion} disabled={isStartingIngestion}>
            {isStartingIngestion ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <PlayCircle className="size-4" />
            )}
            Lancer l’analyse
          </Button>
        ) : null}
      </div>

      <div className="grid gap-4 border-t border-[var(--color-stone)] p-6">
        <div className="grid grid-cols-[1.1fr_0.9fr] gap-4 max-lg:grid-cols-1">
          <div className="rounded-[1.35rem] bg-[var(--color-surface-raised)]/55 p-5">
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
                Sources
              </p>
              <Badge tone={hasSources ? "success" : "neutral"}>
                {hasSources ? `${overview.sources.length} PDF` : "En attente"}
              </Badge>
            </div>

            {hasSources ? (
              <ul className="mt-4 grid gap-3">
                {overview.sources.map((source) => (
                  <li
                    key={source.id}
                    className="rounded-2xl bg-white px-4 py-3 text-sm font-semibold"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <span className="inline-flex items-center gap-2">
                        <FileText className="size-4 text-[var(--color-forest)]" />
                        {source.original_file_name}
                      </span>
                      <span className="text-xs uppercase tracking-[0.1em] text-[var(--color-muted)]">
                        {source.document_type === "UNKNOWN"
                          ? "À classer"
                          : formatCode(source.document_type)}
                      </span>
                    </div>
                    {source.classification_confidence !== null ? (
                      <p className="mt-2 text-xs text-[var(--color-muted)]">
                        Confiance : {Math.round(source.classification_confidence * 100)}%
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm leading-6 text-[var(--color-muted)]">
                Importez les PDFs techniques pour démarrer l’analyse du produit.
              </p>
            )}
          </div>

          <div className="rounded-[1.35rem] bg-[linear-gradient(135deg,#173124,#2d4739)] p-5 text-white">
            <div className="flex items-center justify-between gap-4">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-white/62">
                Analyse
              </p>
              {overview.run !== null ? (
                <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-white/76">
                  <Clock3 className="size-4" />
                  {formatElapsed(elapsedSeconds)}
                </span>
              ) : null}
            </div>
            <h3 className="mt-4 font-serif text-2xl font-semibold tracking-[-0.04em]">
              {analysisTitle(overview)}
            </h3>
            <p className="mt-3 text-sm leading-6 text-white/72">
              {analysisDescription(overview)}
            </p>
            {overview.run !== null ? (
              <div className="mt-5 grid gap-2 text-sm font-semibold text-white/80">
                {analysisSteps(overview.run.current_step).map((step) => (
                  <div key={step.label} className="flex items-center justify-between gap-4">
                    <span>{step.label}</span>
                    <span>{step.status}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </Card>
  );
}

function useElapsedSeconds(active: boolean) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsedSeconds(0);
      return;
    }

    const intervalId = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [active]);

  return elapsedSeconds;
}

function analysisTitle(overview: ProductOverview) {
  if (overview.run === null) {
    return overview.sources.length > 0 ? "Prêt à analyser" : "Dossiers attendus";
  }

  if (overview.review_cases.some((reviewCase) => reviewCase.status === "A_TRAITER")) {
    return "Points à corriger";
  }

  if (overview.run.statut === "TERMINE") {
    return "Analyse terminée";
  }

  return "Analyse en cours";
}

function analysisDescription(overview: ProductOverview) {
  if (overview.run === null) {
    return overview.sources.length > 0
      ? "Les documents sont importés. L’analyse peut maintenant être lancée."
      : "Ajoutez les fichiers usine pour extraire les faits techniques.";
  }

  if (overview.review_cases.some((reviewCase) => reviewCase.status === "A_TRAITER")) {
    return "Certains faits techniques demandent une décision humaine avant de continuer.";
  }

  if (overview.run.statut === "TERMINE") {
    return "Les faits techniques validés peuvent être utilisés pour préparer la génération.";
  }

  return "Les documents sont classés, lus et contrôlés pour préparer un contexte fiable.";
}

function analysisSteps(currentStep: string) {
  const steps = [
    { id: "DOCUMENT_CLASSIFICATION", label: "Identifier les documents" },
    { id: "FACT_EXTRACTION", label: "Extraire les faits techniques" },
    { id: "DETERMINISTIC_VALIDATION", label: "Contrôler les preuves" },
    { id: "PROMOTION", label: "Valider le contexte" },
    { id: "DONE", label: "Terminé" },
  ];
  const currentIndex = Math.max(
    0,
    steps.findIndex((step) => step.id === currentStep),
  );

  return steps.map((step, index) => ({
    label: step.label,
    status: index < currentIndex ? "Terminé" : index === currentIndex ? "En cours" : "À venir",
  }));
}

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
