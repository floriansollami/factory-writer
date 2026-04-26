import { ArrowRight, Settings } from "lucide-react";

import { AxolotlLogo } from "@/components/brand/AxolotlLogo";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil",
  "Fiches produit",
  "Guide de style",
  "Paramètres",
];

type SettingsPageProps = {
  onOpenAdminHome: () => void;
  onOpenProductSheets: () => void;
  onOpenStyleGuide: () => void;
};

export function SettingsPage({
  onOpenAdminHome,
  onOpenProductSheets,
  onOpenStyleGuide,
}: SettingsPageProps) {
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
                    item === "Paramètres" &&
                      "bg-white text-[var(--color-forest)] hover:bg-white hover:text-[var(--color-forest)]",
                  )}
                  onClick={
                    item === "Accueil"
                      ? onOpenAdminHome
                      : item === "Guide de style"
                        ? onOpenStyleGuide
                        : item === "Fiches produit"
                          ? onOpenProductSheets
                          : undefined
                  }
                >
                  {item}
                  {item !== "Paramètres" ? <ArrowRight className="size-4" /> : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          <header>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
              Administration
            </p>
            <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
              Paramètres
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
              Espace de configuration du POC. Les réglages avancés seront branchés ici quand
              les paramètres backend seront exposés.
            </p>
          </header>

          <section className="mt-8 grid max-w-3xl gap-5">
            <Card className="bg-[linear-gradient(135deg,#fffdf8,#f4efe4)] p-6">
              <div className="flex items-start gap-4">
                <div className="grid size-12 place-items-center rounded-2xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
                  <Settings className="size-6" />
                </div>
                <div>
                  <Badge tone="neutral">POC</Badge>
                  <CardTitle className="mt-3">Configuration à venir</CardTitle>
                  <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
                    Aucun réglage manuel n’est nécessaire pour le moment. Le guide de style,
                    les fiches produit et les signaux seedés restent pilotés depuis leurs
                    parcours dédiés.
                  </p>
                </div>
              </div>
            </Card>
          </section>
        </section>
      </div>
    </main>
  );
}
