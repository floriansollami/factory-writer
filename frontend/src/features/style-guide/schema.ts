import { z } from "zod";

const sourceStatusSchema = z.enum([
  "EN_ATTENTE",
  "EN_COURS",
  "TERMINE",
  "ERREUR",
]);
const packStatusSchema = z.enum(["ACTIF", "ARCHIVE", "BROUILLON"]);
const ruleTypeSchema = z.enum([
  "VOIX",
  "TON",
  "FORMATAGE",
  "PROMESSE_INTERDITE",
]);
const constraintLevelSchema = z.enum(["HARD", "SOFT"]);
const editorialDecisionSchema = z.enum([
  "A_VALIDER",
  "APPROUVEE",
  "DESACTIVEE",
]);

const workflowStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string(),
  status: z.enum(["completed", "running", "pending", "failed"]),
  eta: z.string().optional(),
});

const executionMetadataSchema = z.object({
  documentAi: z.array(z.object({ label: z.string(), value: z.string() })),
  llm: z.array(z.object({ label: z.string(), value: z.string() })),
});

const activePackSchema = z.object({
  id: z.string(),
  version: z.string(),
  status: packStatusSchema,
  documentSourcePdf: z.string(),
  approvedBy: z.string().nullable(),
  approvedAt: z.string().nullable(),
  rulesCount: z.number(),
  hardRulesCount: z.number(),
  softRulesCount: z.number(),
  scopes: z.array(z.string()),
  metadata: executionMetadataSchema,
});

const recentPackSchema = z.object({
  version: z.string(),
  documentSourcePdf: z.string(),
  status: packStatusSchema,
  rulesCount: z.number(),
  approvedRulesCount: z.number(),
  disabledRulesCount: z.number(),
  approvedBy: z.string().nullable(),
  updatedAt: z.string(),
});

const styleRuleSchema = z.object({
  id: z.string(),
  typeRegle: ruleTypeSchema,
  niveauContrainte: constraintLevelSchema,
  texteRegle: z.string().min(1),
  taxonomieCode: z.string().nullable(),
  estActif: z.boolean(),
  decisionEditoriale: editorialDecisionSchema,
  origine: z.enum(["IA", "MODIFIEE"]),
  provenance: z.object({
    providerId: z.string().nullable(),
    indexChunk: z.number().nullable(),
    extrait: z.string(),
    pageStart: z.number().nullable(),
    pageEnd: z.number().nullable(),
    metadata: z.unknown().nullable(),
  }),
  review: z.object({
    commentaire: z.string().nullable(),
    reviewedAt: z.string().nullable(),
    reviewedBy: z.string().nullable(),
  }),
  runtime: z.object({
    packIsActive: z.boolean(),
    ruleIsActive: z.boolean(),
  }),
});

export const styleGuideOverviewSchema = z.object({
  activePack: activePackSchema.nullable(),
  pendingDocumentSource: z
    .object({
      documentSourceId: z.string(),
      fileName: z.string(),
      status: sourceStatusSchema,
      storageUri: z.string(),
      storageGeneration: z.string().nullable(),
      storageMetageneration: z.string().nullable(),
      uploadedAt: z.string(),
      updatedAt: z.string().optional(),
    })
    .nullable(),
  currentWorkflow: z
    .object({
      workflowId: z.string(),
      documentSourceId: z.string(),
      ingestionRunId: z.string(),
      status: z.string(),
      currentActivity: z.string(),
      elapsedTime: z.string(),
      progress: z.number().min(0).max(100),
      metadata: executionMetadataSchema,
      steps: z.array(workflowStepSchema),
    })
    .nullable(),
  metrics: z.object({
    activeRules: z.number(),
    needsReview: z.number(),
    disabledRules: z.number(),
    missingProvenance: z.number(),
  }),
  rules: z.array(styleRuleSchema),
  recentPacks: z.array(recentPackSchema),
});

export const styleGuideUploadResponseSchema = z.object({
  status: z.literal("EN_ATTENTE"),
  documentSourceId: z.string(),
  storageUri: z.string(),
  fileName: z.string(),
  storageGeneration: z.string(),
  storageMetageneration: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const styleGuideStartIngestionResponseSchema = z.object({
  status: z.literal("EN_COURS"),
  collectionId: z.string(),
  ingestionRunId: z.string(),
  documentSourceId: z.string(),
  storageUri: z.string(),
  workflowId: z.string(),
});

export type StyleGuideOverview = z.infer<typeof styleGuideOverviewSchema>;
export type StyleGuideUploadResponse = z.infer<
  typeof styleGuideUploadResponseSchema
>;
export type StyleGuideStartIngestionResponse = z.infer<
  typeof styleGuideStartIngestionResponseSchema
>;
export type RecentPack = z.infer<typeof recentPackSchema>;
export type StyleRule = z.infer<typeof styleRuleSchema>;
