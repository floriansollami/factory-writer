import {
  createProductResponseSchema,
  productOverviewSchema,
  productTaxonomiesResponseSchema,
  productsListResponseSchema,
  resolveTechnicalReviewCaseResponseSchema,
  startTechnicalIngestionResponseSchema,
  uploadTechnicalSourcesResponseSchema,
  type CreateProductRequest,
  type CreateProductResponse,
  type ProductOverview,
  type ProductTaxonomiesResponse,
  type ProductsListResponse,
  type ResolveTechnicalReviewCaseRequest,
  type ResolveTechnicalReviewCaseResponse,
  type StartTechnicalIngestionResponse,
  type UploadTechnicalSourcesResponse,
} from "@/features/product-sheets/schema";
import {
  styleGuideOverviewSchema,
  styleGuideStartIngestionResponseSchema,
  styleGuideUploadResponseSchema,
  type StyleGuideOverview,
  type StyleGuideStartIngestionResponse,
  type StyleGuideUploadResponse,
} from "@/features/style-guide/schema";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";
const PRODUCT_REQUEST_TIMEOUT_MS = 12_000;
const PRODUCT_UPLOAD_TIMEOUT_MS = 60_000;

export async function getStyleGuideOverview(): Promise<StyleGuideOverview> {
  const response = await fetch(`${apiBaseUrl}/api/style-guide/overview`);

  if (!response.ok) {
    throw new Error(
      `Impossible de charger le guide de style (${response.status})`,
    );
  }

  return styleGuideOverviewSchema.parse(await response.json());
}

export async function listProducts(): Promise<ProductsListResponse> {
  const response = await _fetchProductApi(`${apiBaseUrl}/api/products`);

  if (!response.ok) {
    throw new Error(`Impossible de charger les fiches produit (${response.status})`);
  }

  return productsListResponseSchema.parse(await response.json());
}

export async function listProductTaxonomies(): Promise<ProductTaxonomiesResponse> {
  const response = await _fetchProductApi(`${apiBaseUrl}/api/products/taxonomies`);

  if (!response.ok) {
    throw new Error(`Impossible de charger les familles produit (${response.status})`);
  }

  return productTaxonomiesResponseSchema.parse(await response.json());
}

export async function createProduct(
  payload: CreateProductRequest,
): Promise<CreateProductResponse> {
  const response = await _fetchProductApi(`${apiBaseUrl}/api/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(detail ?? `Impossible de créer la fiche produit (${response.status})`);
  }

  return createProductResponseSchema.parse(await response.json());
}

export async function getProductOverview(productId: string): Promise<ProductOverview> {
  const response = await _fetchProductApi(
    `${apiBaseUrl}/api/products/${productId}/overview`,
  );

  if (!response.ok) {
    throw new Error(`Impossible de charger le produit (${response.status})`);
  }

  return productOverviewSchema.parse(await response.json());
}

export async function uploadTechnicalSources(
  productId: string,
  files: File[],
): Promise<UploadTechnicalSourcesResponse> {
  const formData = new FormData();

  for (const file of files) {
    formData.append("files", file);
  }

  const response = await _fetchProductApi(
    `${apiBaseUrl}/api/products/${productId}/technical-sources`,
    {
      method: "POST",
      body: formData,
    },
    PRODUCT_UPLOAD_TIMEOUT_MS,
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible d'importer les dossiers techniques (${response.status})`,
    );
  }

  return uploadTechnicalSourcesResponseSchema.parse(await response.json());
}

export async function startTechnicalIngestion(
  productId: string,
): Promise<StartTechnicalIngestionResponse> {
  const response = await _fetchProductApi(
    `${apiBaseUrl}/api/products/${productId}/technical-sources/start-ingestion`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible de lancer l'analyse technique (${response.status})`,
    );
  }

  return startTechnicalIngestionResponseSchema.parse(await response.json());
}

export async function resolveTechnicalReviewCase(
  productId: string,
  caseId: string,
  payload: ResolveTechnicalReviewCaseRequest,
): Promise<ResolveTechnicalReviewCaseResponse> {
  const response = await _fetchProductApi(
    `${apiBaseUrl}/api/products/${productId}/technical-review-cases/${caseId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible de résoudre le point bloquant (${response.status})`,
    );
  }

  return resolveTechnicalReviewCaseResponseSchema.parse(await response.json());
}

export async function uploadStyleGuidePdf(
  file: File,
): Promise<StyleGuideUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBaseUrl}/api/style-guide/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible d'importer le guide de style (${response.status})`,
    );
  }

  return styleGuideUploadResponseSchema.parse(await response.json());
}

export async function reuploadStyleGuidePdf(
  documentSourceId: string,
  file: File,
): Promise<StyleGuideUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${apiBaseUrl}/api/style-guide/document-sources/${documentSourceId}/reupload`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ??
        `Impossible de réimporter le guide de style (${response.status})`,
    );
  }

  return styleGuideUploadResponseSchema.parse(await response.json());
}

export async function startStyleGuideIngestion(
  documentSourceId: string,
): Promise<StyleGuideStartIngestionResponse> {
  const response = await fetch(
    `${apiBaseUrl}/api/style-guide/document-sources/${documentSourceId}/start-ingestion`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible de lancer l'ingestion (${response.status})`,
    );
  }

  return styleGuideStartIngestionResponseSchema.parse(await response.json());
}

export async function patchStyleRule(
  stylePackId: string,
  ruleId: string,
  payload: {
    texteRegle?: string;
    typeRegle?: "VOIX" | "TON" | "FORMATAGE" | "PROMESSE_INTERDITE";
    niveauContrainte?: "HARD" | "SOFT";
    taxonomieCode?: string | null;
    decisionEditoriale?: "A_VALIDER" | "APPROUVEE" | "DESACTIVEE";
    estActif?: boolean;
    commentaire?: string | null;
  },
): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/style-guide/packs/${stylePackId}/rules/${ruleId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible de mettre à jour la règle (${response.status})`,
    );
  }
}

export async function approveStylePack(stylePackId: string): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/style-guide/packs/${stylePackId}/approve`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible d'activer le pack (${response.status})`,
    );
  }
}

async function _fetchProductApi(
  input: RequestInfo | URL,
  init?: RequestInit,
  timeoutMs = PRODUCT_REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: init?.signal ?? controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Le backend produit ne répond pas. Réessayez dans quelques secondes.");
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function _extractErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as {
      detail?: unknown;
      error?: unknown;
    };
    const detail = payload.detail ?? payload.error;
    return typeof detail === "string" ? detail : null;
  } catch {
    return null;
  }
}
