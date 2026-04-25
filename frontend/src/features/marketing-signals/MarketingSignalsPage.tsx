import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Flower2,
  Loader2,
  Megaphone,
  SearchX,
} from "lucide-react";
import { useSearchParams } from "react-router";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type { ProductSheet } from "@/features/product-sheets/schema";
import { formatCode, formatNullableCode } from "@/features/product-sheets/productSheetUtils";
import { listProducts } from "@/lib/api";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil admin",
  "Guide de style",
  "Fiches produit",
  "Signaux marketing",
];

type MarketingSignalsPageProps = {
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
  onOpenStyleGuide: () => void;
  onReturnTo: (returnTo: string) => void;
};

export function MarketingSignalsPage({
  onOpenAdminHome,
  onOpenProductSheets,
  onOpenStyleGuide,
  onReturnTo,
}: MarketingSignalsPageProps) {
  const [searchParams] = useSearchParams();
  const productId = searchParams.get("productId");
  const returnTo = sanitizeReturnTo(searchParams.get("returnTo"));
  const { data, error, isPending } = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    retry: false,
  });
  const product = data?.products.find((item) => item.id === productId) ?? null;

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
                    item === "Signaux marketing" &&
                      "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={
                    item === "Accueil admin"
                      ? onOpenAdminHome
                      : item === "Guide de style"
                        ? onOpenStyleGuide
                        : item === "Fiches produit"
                          ? onOpenProductSheets
                          : undefined
                  }
                >
                  {item}
                  {item !== "Signaux marketing" ? <ArrowRight className="size-4" /> : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
                Signaux marketing
              </p>
              <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Ventes et retours clients
              </h1>
            </div>
            <Button variant="secondary" onClick={() => onReturnTo(returnTo)}>
              <ArrowLeft className="size-4" />
              Revenir à la fiche produit
            </Button>
          </header>

          <section className="mt-8">
            {isPending ? (
              <Card className="grid min-h-72 place-items-center p-8 text-sm font-semibold text-[var(--color-muted)]">
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="size-4 animate-spin" />
                  Vérification des signaux...
                </span>
              </Card>
            ) : error ? (
              <Card className="border border-[var(--color-error-soft)] bg-[var(--color-error-soft)]/35 p-6">
                <CardTitle>Impossible de vérifier les signaux</CardTitle>
                <p className="mt-3 text-sm leading-6 text-[var(--color-error)]">
                  Le service de lecture produit est indisponible.
                </p>
              </Card>
            ) : product === null ? (
              <MissingProductCard onBack={() => onReturnTo(returnTo)} />
            ) : (
              <MarketingSignalsStatusCard
                onBack={() => onReturnTo(returnTo)}
                product={product}
              />
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

function MarketingSignalsStatusCard({
  onBack,
  product,
}: {
  onBack: () => void;
  product: ProductSheet;
}) {
  const isReady = product.commercialSignalsReady;

  return (
    <Card className="relative overflow-hidden bg-[linear-gradient(145deg,#fffdf7,#eef2ea)] p-8">
      <div className="absolute -right-20 -top-24 size-72 rounded-full bg-[var(--color-sage-soft)] blur-3xl" />
      <div className="relative grid grid-cols-[1fr_20rem] gap-8 max-xl:grid-cols-1">
        <div>
          <Badge tone={isReady ? "success" : "warning"}>
            {isReady ? "Signaux disponibles" : "Snapshot à vérifier"}
          </Badge>
          <h2 className="mt-4 max-w-3xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
            {isReady
              ? "Les signaux compatibles sont prêts."
              : "Aucun signal compatible n’est disponible pour cette fiche."}
          </h2>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-[var(--color-muted)]">
            {isReady
              ? "La génération pourra utiliser les tendances de vente et les retours clients correspondant à cette famille produit."
              : "Pour ce POC, les signaux sont chargés depuis les snapshots seedés. Aucun import manuel n’est disponible sur cet écran."}
          </p>
          <Button className="mt-7" onClick={onBack}>
            <ArrowLeft className="size-4" />
            Revenir à la fiche produit
          </Button>
        </div>

        <div className="rounded-[1.5rem] bg-white/80 p-5 shadow-[0_16px_40px_rgba(27,28,26,0.07)]">
          <div className="grid size-12 place-items-center rounded-2xl bg-[var(--color-gold-soft)] text-[var(--color-teak)]">
            {isReady ? <CheckCircle2 className="size-6" /> : <Megaphone className="size-6" />}
          </div>
          <p className="mt-4 text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
            Critères recherchés
          </p>
          <dl className="mt-4 grid gap-3 text-sm">
            <div>
              <dt className="font-bold text-[var(--color-ink)]">Produit</dt>
              <dd className="mt-1 text-[var(--color-muted)]">{product.name}</dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--color-ink)]">Famille</dt>
              <dd className="mt-1 text-[var(--color-muted)]">
                {formatCode(product.familleCode)}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--color-ink)]">Segment</dt>
              <dd className="mt-1 text-[var(--color-muted)]">
                {formatNullableCode(product.segmentPrixCode)}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--color-ink)]">Saison</dt>
              <dd className="mt-1 text-[var(--color-muted)]">
                {formatNullableCode(product.seasonCode)}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </Card>
  );
}

function MissingProductCard({ onBack }: { onBack: () => void }) {
  return (
    <Card className="grid min-h-72 place-items-center p-8 text-center">
      <div>
        <div className="mx-auto grid size-14 place-items-center rounded-3xl bg-[var(--color-gold-soft)] text-[var(--color-teak)]">
          <SearchX className="size-7" />
        </div>
        <CardTitle className="mt-5">Produit introuvable</CardTitle>
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-[var(--color-muted)]">
          La vérification des signaux doit partir d’une fiche produit existante.
        </p>
        <Button className="mt-5" onClick={onBack}>
          <ArrowLeft className="size-4" />
          Revenir aux fiches produit
        </Button>
      </div>
    </Card>
  );
}

function sanitizeReturnTo(value: string | null) {
  if (value !== null && value.startsWith("/") && !value.startsWith("//")) {
    return value;
  }

  return "/product-sheets";
}
