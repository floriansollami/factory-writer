import { z } from "zod";

const productReadinessStatusSchema = z.enum([
  "PRODUCT_CREATED",
  "TECHNICAL_SOURCES_UPLOADED",
  "INGESTION_RUNNING",
  "PENDING_TECH_REVIEW",
  "CONTEXT_READY",
  "FAILED",
]);

const technicalReviewResolutionActionSchema = z.enum([
  "APPROVE_DETECTED_VALUE",
  "CORRECT_VALUE",
  "REJECT_VALUE",
  "REQUEST_NEW_DOCUMENT",
]);

const productSheetSchema = z.object({
  id: z.string(),
  sku: z.string(),
  name: z.string(),
  familleCode: z.string(),
  sousFamilleCode: z.string().nullable(),
  seasonCode: z.string().nullable(),
  segmentPrixCode: z.string().nullable(),
  languePrincipale: z.string(),
  readinessStatus: productReadinessStatusSchema,
  styleGuideReady: z.boolean(),
  commercialSignalsReady: z.boolean(),
  createdAt: z.string().nullable(),
});

export const productsListResponseSchema = z.object({
  products: z.array(productSheetSchema),
});

const productTaxonomySchema = z.object({
  id: z.string(),
  code: z.string(),
  libelleFr: z.string(),
  parentId: z.string().nullable(),
});

export const productTaxonomiesResponseSchema = z.object({
  taxonomies: z.array(productTaxonomySchema),
});

const productOverviewProductSchema = z.object({
  id: z.string(),
  sku: z.string(),
  name: z.string(),
  famille_code: z.string(),
  sous_famille_code: z.string().nullable(),
  season_code: z.string().nullable(),
  segment_prix_code: z.string().nullable(),
  langue_principale: z.string(),
});

const technicalCollectionSchema = z.object({
  id: z.string(),
  kind: z.string(),
  statut: z.string(),
});

export const technicalSourceSchema = z.object({
  id: z.string(),
  collection_id: z.string(),
  original_file_name: z.string(),
  storage_uri: z.string(),
  storage_content_type: z.string().nullable().optional(),
  storage_size_bytes: z.number().nullable().optional(),
  document_type: z.string(),
  classification_confidence: z.number().nullable(),
  statut: z.string(),
});

export const technicalRunSchema = z.object({
  id: z.string(),
  collection_id: z.string(),
  workflow_id: z.string().nullable(),
  statut: z.string(),
  current_step: z.string(),
  validation_summary_json: z.unknown().nullable(),
  extraction_steps_json: z.unknown().nullable(),
});

export const technicalFactSchema = z.object({
  id: z.string(),
  field_name: z.string(),
  value: z.string(),
  unit: z.string().nullable(),
  validation_source: z.string(),
  validated_at: z.string(),
});

export const technicalFactCandidateSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  field_name: z.string(),
  raw_value: z.string().nullable(),
  normalized_value: z.string().nullable(),
  unit: z.string().nullable(),
  extractor_confidence: z.number().nullable(),
  validation_status: z.string(),
  review_required: z.boolean(),
  review_reason: z.string().nullable(),
  source_evidence_text: z.string().nullable(),
  source_page: z.number().nullable(),
  source_bbox_json: z.unknown().nullable(),
});

export const technicalReviewCaseSchema = z.object({
  id: z.string(),
  case_type: z.string(),
  severity: z.string(),
  status: z.string(),
  field_name: z.string().nullable(),
  title: z.string(),
  description: z.string(),
  detected_value: z.string().nullable(),
  detected_unit: z.string().nullable(),
  suggested_value: z.string().nullable(),
  suggested_unit: z.string().nullable(),
  corrected_value: z.string().nullable(),
  corrected_unit: z.string().nullable(),
  resolution_action: z.string().nullable(),
  resolution_comment: z.string().nullable(),
});

export const productOverviewSchema = z.object({
  product: productOverviewProductSchema,
  technical_collection: technicalCollectionSchema.nullable(),
  sources: z.array(technicalSourceSchema),
  run: technicalRunSchema.nullable(),
  facts: z.array(technicalFactSchema),
  fact_candidates: z.array(technicalFactCandidateSchema),
  review_cases: z.array(technicalReviewCaseSchema),
  commercial_signal_snapshot: z.unknown().nullable(),
  product_context_snapshot: z.unknown().nullable(),
});

export const uploadTechnicalSourcesResponseSchema = z.object({
  sources: z.array(technicalSourceSchema),
});

export const startTechnicalIngestionResponseSchema = z.object({
  product: productOverviewProductSchema,
  collection_id: z.string(),
  run: technicalRunSchema,
  sources: z.array(technicalSourceSchema),
  reused_existing_run: z.boolean(),
});

export const resolveTechnicalReviewCaseRequestSchema = z.object({
  action: technicalReviewResolutionActionSchema,
  resolvedBy: z.string().trim().min(1).optional(),
  correctedValue: z.string().trim().nullable().optional(),
  correctedUnit: z.string().trim().nullable().optional(),
  comment: z.string().trim().nullable().optional(),
});

export const resolveTechnicalReviewCaseResponseSchema = z.object({
  case_id: z.string(),
  status: z.string(),
  ingestion_run_id: z.string(),
});

const createProductRequestSchema = z.object({
  sku: z.string().trim().min(1, "Le SKU est requis."),
  name: z.string().trim().min(1, "Le nom produit est requis."),
  familleCode: z.string().trim().min(1, "La famille est requise."),
  sousFamilleCode: z.string().trim().min(1, "La sous-famille est requise."),
  seasonCode: z.string().trim().nullable(),
  segmentPrixCode: z.string().trim().nullable(),
  languePrincipale: z.string().trim().min(1, "La langue est requise.").optional(),
});

export const createProductResponseSchema = z.object({
  product: z.object({
    id: z.string(),
    sku: z.string(),
    name: z.string(),
    famille_code: z.string(),
    sous_famille_code: z.string().nullable(),
    season_code: z.string().nullable(),
    segment_prix_code: z.string().nullable(),
    langue_principale: z.string(),
  }),
  workflow_id: z.string().nullable(),
});

export type ProductSheet = z.infer<typeof productSheetSchema>;
export type ProductsListResponse = z.infer<typeof productsListResponseSchema>;
export type ProductTaxonomy = z.infer<typeof productTaxonomySchema>;
export type ProductTaxonomiesResponse = z.infer<typeof productTaxonomiesResponseSchema>;
export type ProductOverview = z.infer<typeof productOverviewSchema>;
export type TechnicalSource = z.infer<typeof technicalSourceSchema>;
export type TechnicalRun = z.infer<typeof technicalRunSchema>;
export type TechnicalFact = z.infer<typeof technicalFactSchema>;
export type TechnicalFactCandidate = z.infer<typeof technicalFactCandidateSchema>;
export type TechnicalReviewCase = z.infer<typeof technicalReviewCaseSchema>;
export type TechnicalReviewResolutionAction = z.infer<
  typeof technicalReviewResolutionActionSchema
>;
export type UploadTechnicalSourcesResponse = z.infer<
  typeof uploadTechnicalSourcesResponseSchema
>;
export type StartTechnicalIngestionResponse = z.infer<
  typeof startTechnicalIngestionResponseSchema
>;
export type ResolveTechnicalReviewCaseRequest = z.infer<
  typeof resolveTechnicalReviewCaseRequestSchema
>;
export type ResolveTechnicalReviewCaseResponse = z.infer<
  typeof resolveTechnicalReviewCaseResponseSchema
>;
export type CreateProductRequest = z.infer<typeof createProductRequestSchema>;
export type CreateProductResponse = z.infer<typeof createProductResponseSchema>;
