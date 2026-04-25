import type { ProductOverview, ProductSheet, TechnicalRun } from "@/features/product-sheets/schema";

export type ProductFlowStep = "product" | "sources" | "analysis" | "context" | "generation";

export function productReadinessLabel(status: ProductSheet["readinessStatus"]) {
  switch (status) {
    case "CONTEXT_READY":
      return "Prêt pour génération";
    case "INGESTION_RUNNING":
      return "Analyse technique en cours";
    case "PENDING_TECH_REVIEW":
      return "Points techniques à corriger";
    case "TECHNICAL_SOURCES_UPLOADED":
      return "Dossiers techniques reçus";
    case "FAILED":
      return "À vérifier";
    case "PRODUCT_CREATED":
      return "Dossiers techniques attendus";
  }
}

export function productListActionLabel(product: ProductSheet) {
  if (!product.styleGuideReady) {
    return "Activer le guide de style";
  }

  if (!product.commercialSignalsReady) {
    return "Préparer les signaux";
  }

  switch (product.readinessStatus) {
    case "PRODUCT_CREATED":
      return "Préparer la fiche";
    case "TECHNICAL_SOURCES_UPLOADED":
      return "Continuer la fiche";
    case "INGESTION_RUNNING":
      return "Voir la fiche";
    case "PENDING_TECH_REVIEW":
      return "Corriger la fiche";
    case "CONTEXT_READY":
      return "Générer bientôt";
    case "FAILED":
      return "Voir la fiche";
  }
}

export function productListActionHint(product: ProductSheet) {
  if (!product.styleGuideReady) {
    return "Requis avant génération";
  }

  if (!product.commercialSignalsReady) {
    return "Données ventes et retours à vérifier";
  }

  switch (product.readinessStatus) {
    case "PRODUCT_CREATED":
      return "Ajouter les dossiers techniques";
    case "TECHNICAL_SOURCES_UPLOADED":
      return "Lancer l’analyse technique";
    case "INGESTION_RUNNING":
      return "Suivre l’analyse technique";
    case "PENDING_TECH_REVIEW":
      return "Résoudre les points bloquants";
    case "CONTEXT_READY":
      return "Contexte prêt";
    case "FAILED":
      return "Contrôler le problème";
  }
}

export function productStatusTone(status: ProductSheet["readinessStatus"]) {
  switch (status) {
    case "CONTEXT_READY":
      return "success";
    case "PENDING_TECH_REVIEW":
    case "FAILED":
      return "danger";
    case "INGESTION_RUNNING":
    case "TECHNICAL_SOURCES_UPLOADED":
    case "PRODUCT_CREATED":
      return "warning";
  }
}

export function resolveProductFlowStep(overview: ProductOverview): ProductFlowStep {
  if (overview.product_context_snapshot !== null) {
    return "generation";
  }

  if (overview.run?.statut === "TERMINE" && overview.review_cases.length === 0) {
    return "context";
  }

  if (overview.run !== null) {
    return "analysis";
  }

  if (overview.sources.length > 0) {
    return "sources";
  }

  return "product";
}

export function isProductAnalysisActive(run: TechnicalRun | null) {
  return run !== null && ["EN_ATTENTE", "EN_COURS", "A_VALIDER"].includes(run.statut);
}

export function formatNullableCode(value: string | null) {
  return value === null || value.length === 0 ? "Non renseigné" : formatCode(value);
}

export function formatCode(value: string) {
  return value.replaceAll("_", " ");
}

export function formatDate(value: string | null) {
  if (value === null) {
    return "Non disponible";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
