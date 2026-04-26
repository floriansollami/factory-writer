import { describe, expect, it } from "vitest";

import {
  productOverviewSchema,
  productTaxonomiesResponseSchema,
  productsListResponseSchema,
  resolveTechnicalReviewCaseResponseSchema,
  startTechnicalIngestionResponseSchema,
  uploadTechnicalSourcesResponseSchema,
} from "@/features/product-sheets/schema";

describe("productsListResponseSchema", () => {
  it("parses the product listing payload", () => {
    const payload = productsListResponseSchema.parse({
      products: [
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
          styleGuideReady: true,
          commercialSignalsReady: true,
          createdAt: "2026-04-25T08:58:00.000Z",
        },
      ],
    });

    expect(payload.products).toHaveLength(1);
    expect(payload.products[0]?.sku).toBe("AX-TB-RIV-220-TKGR");
  });

  it("parses the product taxonomy payload", () => {
    const payload = productTaxonomiesResponseSchema.parse({
      taxonomies: [
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
      ],
    });

    expect(payload.taxonomies).toHaveLength(2);
    expect(payload.taxonomies[1]?.code).toBe("table_repas_exterieur");
  });

  it("parses the product overview payload", () => {
    const payload = productOverviewSchema.parse({
      product: {
        id: "product-1",
        sku: "AX-TB-RIV-220-TKGR",
        name: "Table Rivage 220",
        famille_code: "mobilier_jardin",
        sous_famille_code: "table_repas_exterieur",
        season_code: "printemps_ete",
        segment_prix_code: "premium",
        langue_principale: "fr-FR",
      },
      technical_collection: {
        id: "collection-1",
        kind: "TECHNICAL_DOSSIER",
        statut: "EN_COURS",
      },
      sources: [
        {
          id: "source-1",
          collection_id: "collection-1",
          original_file_name: "fiche_atelier.pdf",
          storage_uri: "gs://bucket/fiche_atelier.pdf",
          storage_content_type: "application/pdf",
          storage_size_bytes: 42_000,
          document_type: "TECHNICAL_SHEET",
          classification_confidence: 0.93,
          statut: "EN_COURS",
        },
      ],
      technical_classifications: [
        {
          source_id: "source-1",
          file_name: "fiche_atelier.pdf",
          document_type: "TECHNICAL_SHEET",
          confidence: 0.93,
          is_blocking: false,
          blocking_reason: null,
        },
        {
          source_id: "source-2",
          file_name: "cv.pdf",
          document_type: "OUT_OF_SCOPE_DOCUMENT",
          confidence: 0.99,
          is_blocking: true,
          blocking_reason: "OUT_OF_SCOPE",
        },
      ],
      run: {
        id: "run-1",
        collection_id: "collection-1",
        workflow_id: "product-lifecycle-AX-TB-RIV-220-TKGR",
        statut: "EN_COURS",
        current_step: "FACT_EXTRACTION",
        validation_summary_json: null,
        extraction_steps_json: { total_elapsed_seconds: 0 },
      },
      facts: [
        {
          id: "fact-1",
          field_name: "material_primary",
          value: "teck",
          unit: null,
          validation_source: "SYSTEM",
          validated_at: "2026-04-25T08:58:00.000Z",
        },
      ],
      fact_candidates: [],
      review_cases: [
        {
          id: "case-1",
          case_type: "LOW_CONFIDENCE",
          severity: "BLOCKING",
          status: "A_TRAITER",
          field_name: "dimension_width",
          title: "Largeur à confirmer",
          description: "La largeur extraite manque de confiance.",
          detected_value: "220",
          detected_unit: "cm",
          suggested_value: null,
          suggested_unit: null,
          corrected_value: null,
          corrected_unit: null,
          resolution_action: null,
          resolution_comment: null,
          metadata_json: {
            confidence: 0.89,
            threshold: 0.9,
          },
        },
      ],
      commercial_signal_snapshot: null,
      generation_readiness: {
        profile_code: "mobilier_jardin_table_repas_exterieur_product_sheet_v1",
        ready: false,
        blocking_count: 1,
        required_fields: ["sku", "product_name", "dimension_width"],
        required_missing: ["dimension_width"],
        low_confidence: [],
        out_of_bounds: [],
        contradictions: [],
        do_not_mention: ["eco_certifications"],
      },
      product_context_snapshot: null,
    });

    expect(payload.sources).toHaveLength(1);
    expect(payload.technical_classifications).toHaveLength(2);
    expect(payload.technical_classifications[1]?.blocking_reason).toBe("OUT_OF_SCOPE");
    expect(payload.review_cases[0]?.status).toBe("A_TRAITER");
    expect(payload.review_cases[0]?.metadata_json).toMatchObject({ threshold: 0.9 });
    expect(payload.generation_readiness?.required_missing).toEqual(["dimension_width"]);
    expect(payload.generation_readiness?.do_not_mention).toEqual(["eco_certifications"]);
  });

  it("parses technical source upload, ingestion start and review resolution payloads", () => {
    const upload = uploadTechnicalSourcesResponseSchema.parse({
      sources: [
        {
          id: "source-1",
          collection_id: "collection-1",
          original_file_name: "notice.pdf",
          storage_uri: "gs://bucket/notice.pdf",
          storage_content_type: "application/pdf",
          storage_size_bytes: 21_000,
          document_type: "UNKNOWN",
          classification_confidence: null,
          statut: "EN_ATTENTE",
        },
      ],
    });
    const start = startTechnicalIngestionResponseSchema.parse({
      product: {
        id: "product-1",
        sku: "AX-TB-RIV-220-TKGR",
        name: "Table Rivage 220",
        famille_code: "mobilier_jardin",
        sous_famille_code: "table_repas_exterieur",
        season_code: "printemps_ete",
        segment_prix_code: "premium",
        langue_principale: "fr-FR",
      },
      collection_id: "collection-1",
      run: {
        id: "run-1",
        collection_id: "collection-1",
        workflow_id: "product-lifecycle-AX-TB-RIV-220-TKGR",
        statut: "EN_COURS",
        current_step: "DOCUMENT_CLASSIFICATION",
        validation_summary_json: null,
        extraction_steps_json: null,
      },
      sources: upload.sources,
      reused_existing_run: false,
    });
    const resolution = resolveTechnicalReviewCaseResponseSchema.parse({
      case_id: "case-1",
      status: "APPROUVE",
      ingestion_run_id: "run-1",
      open_review_case_count: 0,
      review_complete: true,
    });

    expect(upload.sources[0]?.document_type).toBe("UNKNOWN");
    expect(start.run.current_step).toBe("DOCUMENT_CLASSIFICATION");
    expect(resolution.status).toBe("APPROUVE");
    expect(resolution.review_complete).toBe(true);
  });
});
