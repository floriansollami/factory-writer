import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileText,
  Flower2,
  Loader2,
  PackagePlus,
  Plus,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useId,
  useMemo,
  useState,
} from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import type {
  CreateProductRequest,
  ProductSheet,
  ProductTaxonomy,
} from "@/features/product-sheets/schema";
import {
  formatCode,
  productListActionHint,
  productListActionLabel,
  productReadinessLabel,
  productStatusTone,
} from "@/features/product-sheets/productSheetUtils";
import {
  createProduct,
  listProducts,
  listProductTaxonomies,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const navItems = [
  "Accueil admin",
  "Guide de style",
  "Fiches produit",
  "Signaux marketing",
];

type ProductFormValues = {
  sku: string;
  name: string;
  familleCode: string;
  sousFamilleCode: string;
  seasonCode: string;
  segmentPrixCode: string;
};

type ProductFormErrors = Partial<Record<keyof ProductFormValues, string>>;

const initialProductFormValues: ProductFormValues = {
  sku: "AX-TB-RIV-220-TKGR",
  name: "Table Rivage 220",
  familleCode: "mobilier_jardin",
  sousFamilleCode: "table_repas_exterieur",
  seasonCode: "printemps_ete",
  segmentPrixCode: "premium",
};

const EMPTY_PRODUCTS: ProductSheet[] = [];
const EMPTY_TAXONOMIES: ProductTaxonomy[] = [];
const productJourneySteps = [
  {
    label: "Produit",
    text: "Entrée catalogue créée",
  },
  {
    label: "Dossiers",
    text: "PDFs techniques ajoutés",
  },
  {
    label: "Analyse",
    text: "Faits contrôlés",
  },
  {
    label: "Génération",
    text: "Fiche prête à relire",
  },
];

type ProductSheetsHomePageProps = {
  onOpenAdminHome: () => void;
  onOpenProductDetail: (productId: string) => void;
  onOpenMarketingSignals: (productId: string, returnTo: string) => void;
  onOpenStyleGuide: (returnTo?: string) => void;
};

export function ProductSheetsHomePage({
  onOpenAdminHome,
  onOpenMarketingSignals,
  onOpenProductDetail,
  onOpenStyleGuide,
}: ProductSheetsHomePageProps) {
  const [isCreateDialogOpen, setCreateDialogOpen] = useState(false);
  const { data, isPending, error } = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    retry: false,
  });
  const {
    data: taxonomiesData,
    isPending: isTaxonomiesPending,
    error: taxonomiesError,
  } = useQuery({
    queryKey: ["product-taxonomies"],
    queryFn: listProductTaxonomies,
    retry: false,
  });
  const products = data?.products ?? EMPTY_PRODUCTS;
  const taxonomies = taxonomiesData?.taxonomies ?? EMPTY_TAXONOMIES;

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
                        : undefined
                  }
                >
                  {item}
                  {item === "Accueil admin" ? <ArrowRight className="size-4" /> : null}
                  {item === "Guide de style" ? <ArrowRight className="size-4" /> : null}
                </button>
              ))}
            </nav>
          </div>
        </aside>

        <section className="px-7 py-6 max-md:px-4">
          <header>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-teak)]">
                Catalogue
              </p>
              <h1 className="mt-2 font-serif text-4xl font-semibold tracking-[-0.045em] text-[var(--color-ink)] max-md:text-3xl">
                Fiches produit
              </h1>
            </div>
          </header>

          <section className="mt-8">
            <Card className="relative overflow-hidden bg-[linear-gradient(135deg,#173124,#2d4739)] p-8 text-white">
              <div className="absolute -right-24 -top-24 size-72 rounded-full bg-[#cde5d3]/18 blur-3xl" />
              <div className="absolute -bottom-28 left-12 size-72 rounded-full bg-[#d4b374]/12 blur-3xl" />
              <div className="relative grid grid-cols-[1fr_24rem] gap-8 max-xl:grid-cols-1">
                <div>
                  <Badge className="bg-white/15 text-white">Cockpit produit</Badge>
                  <h2 className="mt-4 max-w-3xl font-serif text-4xl font-semibold leading-tight tracking-[-0.045em] max-md:text-3xl">
                    Préparer les fiches produit à générer.
                  </h2>
                  <p className="mt-5 max-w-2xl text-sm leading-7 text-white/76">
                    Ouvrez une fiche pour ajouter ses dossiers techniques, suivre l’analyse,
                    puis préparer la génération. La suite du parcours se passe toujours depuis
                    la fiche produit.
                  </p>
                </div>
                <div className="rounded-[1.5rem] border border-white/12 bg-white/10 p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.14)] backdrop-blur">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-white/58">
                    Parcours d’une fiche
                  </p>
                  <div className="mt-4 grid gap-3">
                    {productJourneySteps.map((step, index) => (
                      <div key={step.label} className="flex items-center gap-3">
                        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-white text-xs font-bold text-[var(--color-forest)]">
                          {index + 1}
                        </span>
                        <span>
                          <span className="block text-sm font-bold">{step.label}</span>
                          <span className="block text-xs text-white/62">{step.text}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </section>

          <section className="mt-6">
            <Card className="overflow-hidden p-0">
              <div className="flex flex-wrap items-start justify-between gap-4 p-6">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
                    Fiches du catalogue
                  </p>
                  <CardTitle className="mt-2">Fiches à préparer</CardTitle>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--color-muted)]">
                    Chaque ligne ouvre le parcours complet de la fiche : dossiers techniques,
                    analyse, contexte, puis génération.
                  </p>
                </div>
              </div>

              {isPending ? (
                <div className="grid min-h-72 place-items-center border-t border-[var(--color-stone)] text-sm font-semibold text-[var(--color-muted)]">
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="size-4 animate-spin" />
                    Chargement des fiches produit...
                  </span>
                </div>
              ) : error ? (
                <div className="border-t border-[var(--color-stone)] p-6">
                  <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/45 p-4 text-sm font-semibold text-[var(--color-error)]">
                    Impossible de charger les fiches produit.
                  </div>
                </div>
              ) : products.length === 0 ? (
                <EmptyProductsState onCreate={() => setCreateDialogOpen(true)} />
              ) : (
                <ProductTaskList
                  onOpenProductDetail={onOpenProductDetail}
                  onOpenMarketingSignals={onOpenMarketingSignals}
                  onOpenStyleGuide={onOpenStyleGuide}
                  products={products}
                  onCreate={() => setCreateDialogOpen(true)}
                />
              )}
            </Card>
          </section>
        </section>
      </div>

      <CreateProductDialog
        existingProducts={products}
        isTaxonomiesPending={isTaxonomiesPending}
        open={isCreateDialogOpen}
        onOpenChange={setCreateDialogOpen}
        taxonomies={taxonomies}
        taxonomiesError={taxonomiesError}
      />
    </main>
  );
}

function ProductTaskList({
  onOpenProductDetail,
  onOpenMarketingSignals,
  onOpenStyleGuide,
  products,
  onCreate,
}: {
  onOpenProductDetail: (productId: string) => void;
  onOpenMarketingSignals: (productId: string, returnTo: string) => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  products: ProductSheet[];
  onCreate: () => void;
}) {
  return (
    <div className="border-t border-[var(--color-stone)] bg-[linear-gradient(180deg,#f8f3e8,#fbf9f5)] p-4">
      <div className="grid gap-3">
        {products.map((product) => (
          <ProductTaskRow
            key={product.id}
            onOpen={() => onOpenProductDetail(product.id)}
            onPrimaryAction={() =>
              openProductPrimaryAction({
                onOpenMarketingSignals,
                onOpenProductDetail,
                onOpenStyleGuide,
                product,
              })
            }
            product={product}
          />
        ))}
      </div>
      <div className="mt-4 flex justify-end">
        <Button variant="secondary" onClick={onCreate}>
          <Plus className="size-4" />
          Ajouter un produit
        </Button>
      </div>
    </div>
  );
}

function ProductTaskRow({
  onOpen,
  onPrimaryAction,
  product,
}: {
  onOpen: () => void;
  onPrimaryAction: () => void;
  product: ProductSheet;
}) {
  return (
    <article
      className="group cursor-pointer overflow-hidden rounded-[1.45rem] border border-[var(--color-stone)] bg-[linear-gradient(135deg,#fffdf8,#fbf5ea)] p-4 shadow-[0_12px_30px_rgba(27,28,26,0.04)] transition hover:-translate-y-0.5 hover:border-[var(--color-gold-soft)] hover:shadow-[0_18px_44px_rgba(27,28,26,0.08)]"
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
      role="button"
      tabIndex={0}
    >
      <div className="grid grid-cols-[1fr_auto] items-center gap-5 max-lg:grid-cols-1">
        <div className="grid grid-cols-[auto_1fr] gap-4">
          <div className="grid size-12 place-items-center rounded-2xl bg-[linear-gradient(135deg,var(--color-sage-soft),var(--color-gold-soft))] text-[var(--color-forest)]">
            {productStatusIcon(product.readinessStatus)}
          </div>
          <div>
            <div className="flex flex-wrap items-start gap-3">
              <h3 className="font-serif text-2xl font-semibold tracking-[-0.04em] text-[var(--color-ink)]">
                {product.name}
              </h3>
              <Badge tone={productStatusTone(product.readinessStatus)}>
                {productReadinessLabel(product.readinessStatus)}
              </Badge>
            </div>
            <p className="mt-2 text-sm font-semibold text-[var(--color-ink)]">
              {product.sku}
              <span className="mx-2 text-[var(--color-gold)]">•</span>
              <span className="text-[var(--color-muted)]">{formatCode(product.familleCode)}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 max-lg:justify-between">
          <div className="text-right max-lg:text-left">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-teak)]">
              Prochaine étape
            </p>
            <p className="mt-1 text-sm font-semibold text-[var(--color-muted)]">
              {productListActionHint(product)}
            </p>
          </div>
          <Button
            className="min-w-48 justify-between"
            size="sm"
            onClick={(event) => {
              event.stopPropagation();
              onPrimaryAction();
            }}
          >
            {productListActionLabel(product)}
            <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
          </Button>
        </div>
      </div>
    </article>
  );
}

function openProductPrimaryAction({
  onOpenMarketingSignals,
  onOpenProductDetail,
  onOpenStyleGuide,
  product,
}: {
  onOpenMarketingSignals: (productId: string, returnTo: string) => void;
  onOpenProductDetail: (productId: string) => void;
  onOpenStyleGuide: (returnTo?: string) => void;
  product: ProductSheet;
}) {
  const returnTo = `/product-sheets/${product.id}`;

  if (!product.styleGuideReady) {
    onOpenStyleGuide(returnTo);
    return;
  }

  if (!product.commercialSignalsReady) {
    onOpenMarketingSignals(product.id, returnTo);
    return;
  }

  onOpenProductDetail(product.id);
}

function productStatusIcon(status: ProductSheet["readinessStatus"]) {
  switch (status) {
    case "PRODUCT_CREATED":
      return <UploadCloud className="size-6" />;
    case "TECHNICAL_SOURCES_UPLOADED":
    case "INGESTION_RUNNING":
      return <Clock3 className="size-6" />;
    case "PENDING_TECH_REVIEW":
    case "FAILED":
      return <FileText className="size-6" />;
    case "CONTEXT_READY":
      return <CheckCircle2 className="size-6" />;
  }
}

function EmptyProductsState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="grid min-h-72 place-items-center border-t border-[var(--color-stone)] bg-[var(--color-surface-raised)]/35 p-8 text-center">
      <div>
        <div className="mx-auto grid size-14 place-items-center rounded-3xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
          <PackagePlus className="size-7" />
        </div>
        <h2 className="mt-5 font-serif text-2xl font-semibold tracking-[-0.035em]">
          Aucune fiche à préparer
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-[var(--color-muted)]">
          Créez un premier produit, puis ouvrez sa fiche pour ajouter les dossiers
          techniques et préparer la génération.
        </p>
        <Button className="mt-5" onClick={onCreate}>
          <Plus className="size-4" />
          Créer un produit
        </Button>
      </div>
    </div>
  );
}

function CreateProductDialog({
  existingProducts,
  isTaxonomiesPending,
  open,
  onOpenChange,
  taxonomies,
  taxonomiesError,
}: {
  existingProducts: ProductSheet[];
  isTaxonomiesPending: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taxonomies: ProductTaxonomy[];
  taxonomiesError: Error | null;
}) {
  const titleId = useId();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<ProductFormValues>(initialProductFormValues);
  const [fieldErrors, setFieldErrors] = useState<ProductFormErrors>({});
  const familyTaxonomies = useMemo(
    () => taxonomies.filter((taxonomy) => taxonomy.parentId === null),
    [taxonomies],
  );
  const selectedFamily = familyTaxonomies.find(
    (taxonomy) => taxonomy.code === values.familleCode,
  );
  const subFamilyTaxonomies = useMemo(
    () =>
      selectedFamily === undefined
        ? []
        : taxonomies.filter((taxonomy) => taxonomy.parentId === selectedFamily.id),
    [selectedFamily, taxonomies],
  );
  const existingSkus = useMemo(
    () => new Set(existingProducts.map((product) => product.sku.trim().toLowerCase())),
    [existingProducts],
  );
  const mutation = useMutation({
    mutationFn: (payload: CreateProductRequest) => createProduct(payload),
    onSuccess: async () => {
      setValues(normalizeProductFormValues(initialProductFormValues, taxonomies));
      setFieldErrors({});
      onOpenChange(false);
      await queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  useEffect(() => {
    if (!open) {
      return;
    }

    setFieldErrors({});
    setValues((currentValues) =>
      normalizeProductFormValues(currentValues, taxonomies),
    );
  }, [open, taxonomies]);

  if (!open) {
    return null;
  }

  function updateField(field: keyof ProductFormValues, value: string) {
    mutation.reset();
    setFieldErrors((currentErrors) => removeProductFormError(currentErrors, field));

    if (field !== "familleCode") {
      setValues((currentValues) => ({ ...currentValues, [field]: value }));
      return;
    }

    setValues((currentValues) => ({
      ...currentValues,
      familleCode: value,
      sousFamilleCode: firstSubFamilyCodeForFamily(taxonomies, value),
    }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const sku = values.sku.trim();
    const validationErrors = validateProductForm(values, existingSkus);

    if (Object.keys(validationErrors).length > 0) {
      setFieldErrors(validationErrors);
      return;
    }

    mutation.mutate({
      sku,
      name: values.name.trim(),
      familleCode: values.familleCode,
      sousFamilleCode: values.sousFamilleCode.trim(),
      seasonCode: emptyToNull(values.seasonCode),
      segmentPrixCode: emptyToNull(values.segmentPrixCode),
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.42)] px-4 py-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="w-full max-w-2xl overflow-hidden rounded-[2rem] bg-[var(--color-surface-card)] shadow-[0_28px_80px_rgba(27,28,26,0.24)]">
        <div className="flex items-start justify-between gap-6 border-b border-[var(--color-stone)] px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Nouvelle fiche
            </p>
            <h2
              id={titleId}
              className="mt-2 font-serif text-2xl font-semibold tracking-[-0.04em]"
            >
              Créer un produit
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-muted)]">
              Cette création démarre le workflow produit. Les PDFs techniques seront ajoutés ensuite.
            </p>
          </div>
          <button
            type="button"
            className="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--color-surface-raised)] text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]"
            aria-label="Fermer"
            onClick={() => onOpenChange(false)}
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="grid gap-5 px-6 py-6" onSubmit={submit}>
          <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
            <Field label="SKU" error={fieldErrors.sku}>
              <input
                className={inputClassName}
                onChange={(event) => updateField("sku", event.target.value)}
                placeholder="AX-TB-RIV-220-TKGR"
                value={values.sku}
              />
            </Field>
            <Field label="Nom produit" error={fieldErrors.name}>
              <input
                className={inputClassName}
                onChange={(event) => updateField("name", event.target.value)}
                placeholder="Table Rivage 220"
                value={values.name}
              />
            </Field>
            <Field label="Famille produit" error={fieldErrors.familleCode}>
              <select
                className={inputClassName}
                disabled={isTaxonomiesPending || familyTaxonomies.length === 0}
                onChange={(event) =>
                  updateField("familleCode", event.target.value)
                }
                value={values.familleCode}
              >
                <option value="">
                  {isTaxonomiesPending ? "Chargement des familles..." : "Choisir une famille"}
                </option>
                {familyTaxonomies.map((taxonomy) => (
                  <option key={taxonomy.id} value={taxonomy.code}>
                    {taxonomy.libelleFr}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Sous-famille" error={fieldErrors.sousFamilleCode}>
              <select
                className={inputClassName}
                disabled={isTaxonomiesPending || subFamilyTaxonomies.length === 0}
                onChange={(event) =>
                  updateField("sousFamilleCode", event.target.value)
                }
                value={values.sousFamilleCode}
              >
                <option value="">
                  {isTaxonomiesPending
                    ? "Chargement des sous-familles..."
                    : "Choisir une sous-famille"}
                </option>
                {subFamilyTaxonomies.map((taxonomy) => (
                  <option key={taxonomy.id} value={taxonomy.code}>
                    {taxonomy.libelleFr}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Saison" error={fieldErrors.seasonCode}>
              <input
                className={inputClassName}
                onChange={(event) => updateField("seasonCode", event.target.value)}
                placeholder="printemps_ete"
                value={values.seasonCode}
              />
            </Field>
            <Field label="Segment prix" error={fieldErrors.segmentPrixCode}>
              <input
                className={inputClassName}
                onChange={(event) => updateField("segmentPrixCode", event.target.value)}
                placeholder="premium"
                value={values.segmentPrixCode}
              />
            </Field>
          </div>

          {mutation.error ? (
            <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/50 p-4 text-sm font-semibold text-[var(--color-error)]">
              {mutation.error.message}
            </div>
          ) : null}
          {taxonomiesError ? (
            <div className="rounded-[1.25rem] bg-[var(--color-error-soft)]/50 p-4 text-sm font-semibold text-[var(--color-error)]">
              Impossible de charger les familles produit.
            </div>
          ) : null}

          <div className="flex flex-wrap justify-end gap-3 border-t border-[var(--color-stone)] pt-5">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              Annuler
            </Button>
            <Button
              type="submit"
              disabled={
                mutation.isPending ||
                familyTaxonomies.length === 0 ||
                subFamilyTaxonomies.length === 0
              }
            >
              {mutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              Créer le produit
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  children,
  error,
  label,
}: {
  children: ReactNode;
  error?: string;
  label: string;
}) {
  return (
    <label className="grid gap-2">
      <span className="text-xs font-bold uppercase tracking-[0.13em] text-[var(--color-muted)]">
        {label}
      </span>
      {children}
      {error ? (
        <span className="text-xs font-semibold text-[var(--color-error)]">
          {error}
        </span>
      ) : null}
    </label>
  );
}

const inputClassName =
  "h-12 rounded-2xl border border-[var(--color-stone)] bg-white px-4 text-sm font-semibold text-[var(--color-ink)] outline-none transition placeholder:text-[var(--color-muted)]/55 focus:border-[var(--color-forest)] focus:ring-4 focus:ring-[var(--color-sage-soft)]";

function normalizeProductFormValues(
  values: ProductFormValues,
  taxonomies: ProductTaxonomy[],
): ProductFormValues {
  const familyTaxonomies = taxonomies.filter((taxonomy) => taxonomy.parentId === null);
  const familyExists = familyTaxonomies.some((taxonomy) => taxonomy.code === values.familleCode);
  const familleCode = familyExists ? values.familleCode : (familyTaxonomies[0]?.code ?? "");
  const subFamilyCode = firstSubFamilyCodeForFamily(taxonomies, familleCode);
  const subFamilyExists = taxonomies.some(
    (taxonomy) =>
      taxonomy.code === values.sousFamilleCode &&
      familyTaxonomies.some((family) => family.id === taxonomy.parentId && family.code === familleCode),
  );
  const nextValues = {
    ...values,
    familleCode,
    sousFamilleCode: subFamilyExists ? values.sousFamilleCode : subFamilyCode,
  };

  return areProductFormValuesEqual(values, nextValues) ? values : nextValues;
}

function firstSubFamilyCodeForFamily(taxonomies: ProductTaxonomy[], familleCode: string) {
  const family = taxonomies.find(
    (taxonomy) => taxonomy.parentId === null && taxonomy.code === familleCode,
  );

  if (family === undefined) {
    return "";
  }

  return taxonomies.find((taxonomy) => taxonomy.parentId === family.id)?.code ?? "";
}

function validateProductForm(
  values: ProductFormValues,
  existingSkus: Set<string>,
): ProductFormErrors {
  const errors: ProductFormErrors = {};
  const sku = values.sku.trim();

  if (sku.length === 0) {
    errors.sku = "Le SKU est requis.";
  } else if (existingSkus.has(sku.toLowerCase())) {
    errors.sku = "Ce SKU existe déjà dans le catalogue.";
  }

  if (values.name.trim().length === 0) {
    errors.name = "Le nom produit est requis.";
  }

  if (values.familleCode.trim().length === 0) {
    errors.familleCode = "La famille est requise.";
  }

  if (values.sousFamilleCode.trim().length === 0) {
    errors.sousFamilleCode = "La sous-famille est requise.";
  }

  return errors;
}

function removeProductFormError(
  errors: ProductFormErrors,
  field: keyof ProductFormValues,
): ProductFormErrors {
  const nextErrors = { ...errors };
  delete nextErrors[field];

  return nextErrors;
}

function areProductFormValuesEqual(
  left: ProductFormValues,
  right: ProductFormValues,
): boolean {
  return (
    left.sku === right.sku &&
    left.name === right.name &&
    left.familleCode === right.familleCode &&
    left.sousFamilleCode === right.sousFamilleCode &&
    left.seasonCode === right.seasonCode &&
    left.segmentPrixCode === right.segmentPrixCode
  );
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();

  return trimmed.length > 0 ? trimmed : null;
}
