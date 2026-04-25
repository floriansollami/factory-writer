import type {
  ProductOverview,
  ProductSheet,
  ProductTaxonomy,
} from "@/features/product-sheets/schema";
import type { StyleGuideOverview } from "@/features/style-guide/schema";

export const productTaxonomiesMock: ProductTaxonomy[] = [
  {
    id: "mock-taxonomy-mobilier-jardin",
    code: "mobilier_jardin",
    libelleFr: "Mobilier de jardin",
    parentId: null,
  },
  {
    id: "mock-taxonomy-table-repas-exterieur",
    code: "table_repas_exterieur",
    libelleFr: "Table repas extérieur",
    parentId: "mock-taxonomy-mobilier-jardin",
  },
  {
    id: "mock-taxonomy-outils-jardin",
    code: "outils_jardin",
    libelleFr: "Outils de jardin",
    parentId: null,
  },
  {
    id: "mock-taxonomy-secateur",
    code: "secateur",
    libelleFr: "Sécateur",
    parentId: "mock-taxonomy-outils-jardin",
  },
];

export const productSheetsMock: ProductSheet[] = [
  {
    id: "mock-product-rivage-220",
    sku: "AX-TB-RIV-220-TKGR",
    name: "Table Rivage 220",
    familleCode: "mobilier_jardin",
    sousFamilleCode: "table_repas_exterieur",
    seasonCode: "printemps_ete",
    segmentPrixCode: "premium",
    languePrincipale: "fr-FR",
    readinessStatus: "PRODUCT_CREATED",
    styleGuideReady: false,
    commercialSignalsReady: true,
    createdAt: "2026-04-25T08:58:00.000Z",
  },
];

export const productOverviewsMock: ProductOverview[] = [
  {
    product: {
      id: "mock-product-rivage-220",
      sku: "AX-TB-RIV-220-TKGR",
      name: "Table Rivage 220",
      famille_code: "mobilier_jardin",
      sous_famille_code: "table_repas_exterieur",
      season_code: "printemps_ete",
      segment_prix_code: "premium",
      langue_principale: "fr-FR",
    },
    technical_collection: null,
    sources: [],
    run: null,
    facts: [],
    fact_candidates: [],
    review_cases: [],
    commercial_signal_snapshot: null,
    product_context_snapshot: null,
  },
];

export const styleGuideOverviewMock: StyleGuideOverview = {
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
