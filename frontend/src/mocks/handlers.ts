import { HttpResponse, http } from "msw";

import { styleGuideOverviewMock } from "@/mocks/data";

const now = () => new Date().toISOString();

export const handlers = [
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
