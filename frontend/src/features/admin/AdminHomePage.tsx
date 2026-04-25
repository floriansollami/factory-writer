import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Flower2,
  Gauge,
  Loader2,
  Megaphone,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { lazy, Suspense } from "react";
import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { StyleGuideOverview } from "@/features/style-guide/schema";
import type { WorkflowGraphStep } from "@/features/style-guide/WorkflowPipelineGraph";
import { getStyleGuideOverview } from "@/lib/api";
import { cn } from "@/lib/utils";

const WorkflowPipelineGraph = lazy(() => import("@/features/style-guide/WorkflowPipelineGraph"));

const navItems = [
  "Accueil admin",
  "Guide de style",
  "Fiches produit",
  "Signaux marketing",
];

type AdminHomePageProps = {
  onOpenProductSheets: () => void;
  onOpenStyleGuide: () => void;
};

type PrerequisiteStatus = "ready" | "running" | "missing";

type PrerequisiteItem = {
  id: string;
  title: string;
  description: string;
  status: PrerequisiteStatus;
  detail: string;
  icon: typeof ShieldCheck;
};

export function AdminHomePage({ onOpenProductSheets, onOpenStyleGuide }: AdminHomePageProps) {
  const { data: styleGuideOverview } = useQuery({
    queryKey: ["style-guide-overview"],
    queryFn: getStyleGuideOverview,
    retry: false,
  });
  const prerequisites = buildPrerequisites(styleGuideOverview);
  const allPrerequisitesReady = prerequisites.every((item) => item.status === "ready");
  const globalWorkflowSteps = buildGlobalWorkflowSteps(prerequisites);

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
                    item === "Accueil admin" && "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={
                    item === "Guide de style"
                      ? onOpenStyleGuide
                      : item === "Fiches produit"
                        ? onOpenProductSheets
                        : undefined
                  }
                >
                  {item}
                  {item === "Guide de style" ? <ArrowRight className="size-4" /> : null}
                  {item === "Fiches produit" ? <ArrowRight className="size-4" /> : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
                Pilotage Factory Writer
              </p>
              <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Accueil admin
              </h1>
            </div>
            <Button variant="secondary" onClick={onOpenStyleGuide}>
              Guide de style
              <ArrowRight className="size-4" />
            </Button>
          </header>

          <section className="mt-8">
            <Card className="relative overflow-hidden bg-[linear-gradient(135deg,#173124,#2d4739)] p-8 text-white">
              <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[#cde5d3]/18 blur-3xl" />
              <div className="relative grid grid-cols-[1fr_auto] items-start gap-8 max-2xl:grid-cols-1">
                <div>
                  <Badge className="bg-white/15 text-white">Workflow global</Badge>
                  <h2 className="mt-4 max-w-3xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
                    Générer une fiche produit seulement quand tous les prérequis sont prêts.
                  </h2>
                  <p className="mt-5 max-w-2xl text-sm leading-7 text-white/76">
                    Le guide de style, les signaux marketing et les dossiers techniques doivent être disponibles avant
                    de lancer la génération d’une fiche produit.
                  </p>
                </div>

                <div className="min-w-80 rounded-[1.5rem] bg-white/12 p-5">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-white/60">
                    Action produit
                  </p>
                  <p className="mt-3 font-serif text-xl font-semibold">
                    {allPrerequisitesReady ? "Prêt à générer" : "Pré-requis incomplets"}
                  </p>
                  <Button
                    className="mt-5 border border-white/55 bg-white/12 !text-white hover:bg-white/18 hover:!text-white"
                    disabled={!allPrerequisitesReady}
                  >
                    <Sparkles className="size-4" />
                    Lancer la génération
                  </Button>
                </div>
              </div>
            </Card>
          </section>

          <section className="mt-6 grid grid-cols-3 gap-4 max-xl:grid-cols-1">
            {prerequisites.map((item) => (
              <PrerequisiteCard key={item.id} item={item} />
            ))}
          </section>

          <section className="mt-6">
            <Card className="overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                    Orchestration Temporal
                  </p>
                  <CardTitle className="mt-2">Vue complète du workflow produit</CardTitle>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--color-muted)]">
                    Cette vue globale sert à comprendre où se trouve le produit avant génération. Les pages métier
                    gardent des suivis plus simples, adaptés à leur tâche.
                  </p>
                </div>
                <Gauge className="size-6 text-[var(--color-muted)]" />
              </div>

              <div
                className="mt-7 h-[24rem] overflow-hidden rounded-[1.5rem] border border-[var(--color-stone)] bg-[linear-gradient(135deg,#fffdf8,#f4f1e9)]"
                aria-label="Workflow global Factory Writer"
              >
                <Suspense fallback={<WorkflowGraphFallback />}>
                  <WorkflowPipelineGraph steps={globalWorkflowSteps} />
                </Suspense>
              </div>
            </Card>
          </section>

          <section className="mt-6 grid grid-cols-[0.9fr_1.1fr] gap-6 max-2xl:grid-cols-1">
            <Card>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                Prochaine action
              </p>
              <CardTitle className="mt-2">Compléter les prérequis produit</CardTitle>
              <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
                Le POC doit d’abord recevoir un dossier technique produit et un snapshot de signaux marketing. La
                génération reste bloquée tant que ces deux sources ne sont pas prêtes.
              </p>
            </Card>

            <Card>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                Gouvernance
              </p>
              <CardTitle className="mt-2">Aucune activation automatique</CardTitle>
              <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
                Le workflow peut générer un brouillon rapidement, mais la publication reste séparée de la génération.
                Cela protège les dimensions, les matériaux et la voix de marque.
              </p>
            </Card>
          </section>
        </section>
      </div>
    </main>
  );
}

function PrerequisiteCard({ item }: { item: PrerequisiteItem }) {
  const Icon = item.icon;
  const isReady = item.status === "ready";

  return (
    <Card className="p-5">
      <div
        className={cn(
          "grid size-11 place-items-center rounded-2xl",
          isReady
            ? "bg-[var(--color-sage-soft)] text-[var(--color-forest)]"
            : "bg-[var(--color-stone)] text-[var(--color-muted)]",
        )}
      >
        {isReady ? <CheckCircle2 className="size-5" /> : <Icon className="size-5" />}
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <p className="font-semibold text-[var(--color-ink)]">{item.title}</p>
        <Badge tone={isReady ? "success" : "warning"}>{prerequisiteStatusLabel(item.status)}</Badge>
      </div>
      <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">{item.description}</p>
      <p className="mt-4 text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-teak)]">
        {item.detail}
      </p>
    </Card>
  );
}

function buildPrerequisites(overview: StyleGuideOverview | undefined): PrerequisiteItem[] {
  const styleGuideStatus = resolveStyleGuideStatus(overview);

  return [
    {
      id: "style-guide",
      title: "Guide de style",
      description: "Pack de règles validé par l’équipe éditoriale.",
      status: styleGuideStatus.status,
      detail: styleGuideStatus.detail,
      icon: ShieldCheck,
    },
    {
      id: "technical-files",
      title: "Dossiers techniques",
      description: "PDF usine, dimensions, matériaux et certifications.",
      status: "missing",
      detail: "Archive produit attendue",
      icon: FileText,
    },
    {
      id: "marketing-signals",
      title: "Signaux marketing",
      description: "Historique de ventes et retours clients consolidés.",
      status: "missing",
      detail: "Snapshot non chargé",
      icon: Megaphone,
    },
  ];
}

function resolveStyleGuideStatus(
  overview: StyleGuideOverview | undefined,
): { status: PrerequisiteStatus; detail: string } {
  if (overview?.activePack?.status === "ACTIF") {
    return { status: "ready", detail: "Pack actif disponible" };
  }
  if (overview?.activePack !== null && overview?.activePack !== undefined) {
    return { status: "running", detail: "Pack candidat en revue" };
  }
  if (overview?.currentWorkflow !== null && overview?.currentWorkflow !== undefined) {
    return { status: "running", detail: "Analyse en cours" };
  }
  if (overview?.pendingDocumentSource !== null && overview?.pendingDocumentSource !== undefined) {
    return { status: "running", detail: "PDF importé, analyse à lancer" };
  }
  return { status: "missing", detail: "Pack actif attendu" };
}

function buildGlobalWorkflowSteps(prerequisites: PrerequisiteItem[]): WorkflowGraphStep[] {
  const styleGuide = prerequisites.find((item) => item.id === "style-guide");
  const technicalFiles = prerequisites.find((item) => item.id === "technical-files");
  const marketingSignals = prerequisites.find((item) => item.id === "marketing-signals");
  const allReady = prerequisites.every((item) => item.status === "ready");

  return [
    {
      id: "style-guide-ready",
      label: "Guide de style",
      description: "La voix de marque doit être validée avant toute génération.",
      status: workflowStatusFromPrerequisite(styleGuide),
      eta: styleGuide?.status === "running" ? styleGuide.detail : undefined,
    },
    {
      id: "technical-dossier",
      label: "Dossier technique",
      description: "Les facts produit doivent être extraits et contrôlés.",
      status: workflowStatusFromPrerequisite(technicalFiles),
      eta: technicalFiles?.status !== "ready" ? technicalFiles?.detail : undefined,
    },
    {
      id: "marketing-signals",
      label: "Signaux marketing",
      description: "Les arguments performants et retours clients enrichissent le brief.",
      status: workflowStatusFromPrerequisite(marketingSignals),
      eta: marketingSignals?.status !== "ready" ? marketingSignals?.detail : undefined,
    },
    {
      id: "product-generation",
      label: "Génération fiche",
      description: "Le LLM produit la fiche uniquement quand les prérequis sont complets.",
      status: "pending",
      eta: allReady ? "prêt à lancer" : undefined,
    },
    {
      id: "content-review",
      label: "Revue contenu",
      description: "Un humain vérifie la fiche avant publication.",
      status: "pending",
    },
    {
      id: "publication-ready",
      label: "Prêt à publier",
      description: "La fiche validée devient disponible pour le canal e-commerce.",
      status: "pending",
    },
  ];
}

function workflowStatusFromPrerequisite(item: PrerequisiteItem | undefined): WorkflowGraphStep["status"] {
  if (item?.status === "ready") {
    return "completed";
  }
  if (item?.status === "running") {
    return "running";
  }
  return "pending";
}

function prerequisiteStatusLabel(status: PrerequisiteStatus) {
  if (status === "ready") {
    return "Prêt";
  }
  if (status === "running") {
    return "En cours";
  }
  return "À compléter";
}

function WorkflowGraphFallback() {
  return (
    <div className="grid h-full place-items-center text-sm font-semibold text-[var(--color-muted)]">
      <Loader2 className="mr-2 inline size-4 animate-spin" />
      Chargement du workflow global...
    </div>
  );
}
