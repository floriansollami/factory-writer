import {
  styleGuideOverviewSchema,
  styleGuideStartIngestionResponseSchema,
  styleGuideUploadResponseSchema,
  type StyleGuideOverview,
  type StyleGuideStartIngestionResponse,
  type StyleGuideUploadResponse,
} from "@/features/style-guide/schema";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export async function getStyleGuideOverview(): Promise<StyleGuideOverview> {
  const response = await fetch(`${apiBaseUrl}/api/style-guide/overview`);

  if (!response.ok) {
    throw new Error(
      `Impossible de charger le guide de style (${response.status})`,
    );
  }

  return styleGuideOverviewSchema.parse(await response.json());
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

export async function rejectStylePack(stylePackId: string): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/style-guide/packs/${stylePackId}/reject`,
    {
      method: "POST",
    },
  );

  if (!response.ok) {
    const detail = await _extractErrorDetail(response);
    throw new Error(
      detail ?? `Impossible de rejeter le pack (${response.status})`,
    );
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
