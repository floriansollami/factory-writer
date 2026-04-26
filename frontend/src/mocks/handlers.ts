import { HttpResponse, http } from "msw";

import type { ProductOverview, TechnicalSource } from "@/features/product-sheets/schema";
import {
  productOverviewsMock,
  productSheetsMock,
  productTaxonomiesMock,
  styleGuideOverviewMock,
} from "@/mocks/data";

const now = () => new Date().toISOString();
let productSheets = [...productSheetsMock];
let productOverviews = new Map<string, ProductOverview>(
  productOverviewsMock.map((overview) => [overview.product.id, overview]),
);

export const handlers = [
  http.get("/api/products", () => {
    return HttpResponse.json({
      products: productSheets,
    });
  }),
  http.get("/api/products/taxonomies", () => {
    return HttpResponse.json({
      taxonomies: productTaxonomiesMock,
    });
  }),
  http.get("/api/products/:productId/overview", ({ params }) => {
    const productId = String(params.productId);
    const overview = productOverviews.get(productId);

    if (overview === undefined) {
      return HttpResponse.json({ detail: "Produit introuvable." }, { status: 404 });
    }

    return HttpResponse.json(overview);
  }),
  http.post("/api/products", async ({ request }) => {
    const payload = (await request.json()) as {
      sku: string;
      name: string;
      familleCode: string;
      sousFamilleCode?: string | null;
      seasonCode?: string | null;
      segmentPrixCode?: string | null;
      languePrincipale?: string;
    };
    const product = {
      id: `mock-product-${crypto.randomUUID()}`,
      sku: payload.sku,
      name: payload.name,
      familleCode: payload.familleCode,
      sousFamilleCode: payload.sousFamilleCode ?? null,
      seasonCode: payload.seasonCode ?? null,
      segmentPrixCode: payload.segmentPrixCode ?? null,
      languePrincipale: payload.languePrincipale ?? "fr-FR",
      readinessStatus: "PRODUCT_CREATED" as const,
      styleGuideReady: styleGuideOverviewMock.activePack?.status === "ACTIF",
      commercialSignalsReady:
        payload.familleCode === "mobilier_jardin" &&
        payload.seasonCode === "printemps_ete" &&
        payload.segmentPrixCode === "premium",
      createdAt: now(),
    };

    productSheets = [product, ...productSheets];
    productOverviews.set(product.id, {
      product: {
        id: product.id,
        sku: product.sku,
        name: product.name,
        famille_code: product.familleCode,
        sous_famille_code: product.sousFamilleCode,
        season_code: product.seasonCode,
        segment_prix_code: product.segmentPrixCode,
        langue_principale: product.languePrincipale,
      },
      technical_collection: null,
      sources: [],
      technical_classifications: [],
      run: null,
      facts: [],
      fact_candidates: [],
      review_cases: [],
      commercial_signal_snapshot: null,
      product_context_snapshot: null,
    });

    return HttpResponse.json(
      {
        product: {
          id: product.id,
          sku: product.sku,
          name: product.name,
          famille_code: product.familleCode,
          sous_famille_code: product.sousFamilleCode,
          season_code: product.seasonCode,
          segment_prix_code: product.segmentPrixCode,
          langue_principale: product.languePrincipale,
        },
        workflow_id: `product-lifecycle-${product.sku}`,
      },
      { status: 201 },
    );
  }),
  http.post("/api/products/:productId/technical-sources", async ({ params, request }) => {
    const productId = String(params.productId);
    const overview = productOverviews.get(productId);

    if (overview === undefined) {
      return HttpResponse.json({ detail: "Produit introuvable." }, { status: 404 });
    }

    const collectionId =
      overview.technical_collection?.id ?? `mock-technical-collection-${crypto.randomUUID()}`;
    const formData = await request.formData();
    const files = formData.getAll("files").filter((value): value is File => value instanceof File);
    const sources: TechnicalSource[] = files.map((file) => ({
      id: `mock-source-${crypto.randomUUID()}`,
      collection_id: collectionId,
      original_file_name: file.name,
      storage_uri: `gs://factory-writer-mock/technical-dossiers/${productId}/${file.name}`,
      storage_content_type: file.type || "application/pdf",
      storage_size_bytes: file.size,
      document_type: "UNKNOWN",
      classification_confidence: null,
      statut: "EN_ATTENTE",
    }));
    const nextOverview: ProductOverview = {
      ...overview,
      technical_collection: {
        id: collectionId,
        kind: "TECHNICAL_DOSSIER",
        statut: "EN_ATTENTE",
      },
      sources: [...overview.sources, ...sources],
      technical_classifications: [],
    };

    productOverviews.set(productId, nextOverview);
    productSheets = productSheets.map((product) =>
      product.id === productId
        ? { ...product, readinessStatus: "TECHNICAL_SOURCES_UPLOADED" }
        : product,
    );

    return HttpResponse.json({ sources }, { status: 201 });
  }),
  http.post("/api/products/:productId/technical-sources/start-ingestion", ({ params }) => {
    const productId = String(params.productId);
    const overview = productOverviews.get(productId);

    if (overview === undefined) {
      return HttpResponse.json({ detail: "Produit introuvable." }, { status: 404 });
    }

    const collectionId =
      overview.technical_collection?.id ?? `mock-technical-collection-${crypto.randomUUID()}`;
    const run = {
      id: `mock-technical-run-${crypto.randomUUID()}`,
      collection_id: collectionId,
      workflow_id: `product-lifecycle-${overview.product.sku}`,
      statut: "EN_COURS",
      current_step: "DOCUMENT_CLASSIFICATION",
      validation_summary_json: null,
      extraction_steps_json: {
        steps: [],
        total_elapsed_seconds: 0,
      },
    };
    const nextOverview: ProductOverview = {
      ...overview,
      technical_collection: {
        id: collectionId,
        kind: "TECHNICAL_DOSSIER",
        statut: "EN_COURS",
      },
      run,
      sources: overview.sources.map((source) => ({
        ...source,
        statut: "EN_COURS",
      })),
      technical_classifications: overview.sources.map((source) => ({
        source_id: source.id,
        file_name: source.original_file_name,
        document_type: "TECHNICAL_SHEET",
        confidence: 0.96,
        is_blocking: false,
        blocking_reason: null,
      })),
    };

    productOverviews.set(productId, nextOverview);
    productSheets = productSheets.map((product) =>
      product.id === productId ? { ...product, readinessStatus: "INGESTION_RUNNING" } : product,
    );

    return HttpResponse.json({
      product: overview.product,
      collection_id: collectionId,
      run,
      sources: nextOverview.sources,
      reused_existing_run: false,
    });
  }),
  http.post("/api/products/:productId/technical-sources/replace-lot", async ({ params, request }) => {
    const productId = String(params.productId);
    const overview = productOverviews.get(productId);

    if (overview === undefined) {
      return HttpResponse.json({ detail: "Produit introuvable." }, { status: 404 });
    }

    const collectionId = `mock-technical-collection-${crypto.randomUUID()}`;
    const formData = await request.formData();
    const files = formData.getAll("files").filter((value): value is File => value instanceof File);
    const sources: TechnicalSource[] = files.map((file) => ({
      id: `mock-source-${crypto.randomUUID()}`,
      collection_id: collectionId,
      original_file_name: file.name,
      storage_uri: `gs://factory-writer-mock/technical-dossiers/${productId}/${file.name}`,
      storage_content_type: file.type || "application/pdf",
      storage_size_bytes: file.size,
      document_type: "UNKNOWN",
      classification_confidence: null,
      statut: "EN_COURS",
    }));
    const run = {
      id: `mock-technical-run-${crypto.randomUUID()}`,
      collection_id: collectionId,
      workflow_id: `technical-dossier-${crypto.randomUUID()}`,
      statut: "EN_COURS",
      current_step: "DOCUMENT_CLASSIFICATION",
      validation_summary_json: null,
      extraction_steps_json: {
        steps: [],
        total_elapsed_seconds: 0,
      },
    };
    const nextOverview: ProductOverview = {
      ...overview,
      technical_collection: {
        id: collectionId,
        kind: "TECHNICAL_DOSSIER",
        statut: "EN_COURS",
      },
      sources,
      technical_classifications: [],
      run,
      review_cases: [],
    };

    productOverviews.set(productId, nextOverview);
    productSheets = productSheets.map((product) =>
      product.id === productId ? { ...product, readinessStatus: "INGESTION_RUNNING" } : product,
    );

    return HttpResponse.json({
      product: overview.product,
      collection_id: collectionId,
      run,
      sources,
      reused_existing_run: false,
    });
  }),
  http.patch("/api/products/:productId/technical-review-cases/:caseId", ({ params }) => {
    const productId = String(params.productId);
    const caseId = String(params.caseId);
    const overview = productOverviews.get(productId);

    if (overview === undefined || overview.run === null) {
      return HttpResponse.json({ detail: "Point de revue introuvable." }, { status: 404 });
    }

    productOverviews.set(productId, {
      ...overview,
      review_cases: overview.review_cases.map((reviewCase) =>
        reviewCase.id === caseId
          ? {
              ...reviewCase,
              status: "APPROUVE",
              resolution_action: "APPROVE_DETECTED_VALUE",
            }
          : reviewCase,
      ),
    });

    return HttpResponse.json({
      case_id: caseId,
      status: "APPROUVE",
      ingestion_run_id: overview.run.id,
      open_review_case_count: 0,
      review_complete: true,
    });
  }),
  http.get("/api/style-guide/overview", () => {
    return HttpResponse.json(styleGuideOverviewMock);
  }),
  http.post("/api/style-guide/upload", async ({ request }) => {
    const formData = await request.formData();
    const file = formData.get("file");
    const fileName = file instanceof File ? file.name : "AXOLOTL_STYLE_GUIDE_V2.pdf";

    return HttpResponse.json({
      status: "EN_ATTENTE",
      documentSourceId: "mock-document-source-1",
      storageUri: `gs://factory-writer-mock/style-guides/${fileName}`,
      fileName,
      storageGeneration: "1",
      storageMetageneration: "1",
      createdAt: now(),
      updatedAt: now(),
    });
  }),
  http.post("/api/style-guide/document-sources/:documentSourceId/start-ingestion", ({ params }) => {
    const documentSourceId = String(params.documentSourceId);

    return HttpResponse.json({
      status: "EN_COURS",
      collectionId: "mock-style-guide-collection-1",
      ingestionRunId: "mock-style-guide-run-1",
      documentSourceId,
      storageUri: "gs://factory-writer-mock/style-guides/AXOLOTL_STYLE_GUIDE_V2.pdf",
      workflowId: "mock-style-guide-workflow-1",
    });
  }),
];
