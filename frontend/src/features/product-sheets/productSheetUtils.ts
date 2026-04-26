import type { ProductOverview, ProductSheet, TechnicalRun } from "@/features/product-sheets/schema";

export type ProductFlowStep = "product" | "sources" | "analysis" | "context" | "generation";

function productReadinessLabel(status: ProductSheet["readinessStatus"]) {
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

export function productListStatusLabel(product: ProductSheet) {
  if (!product.styleGuideReady) {
    return "Guide de style requis";
  }

  return productReadinessLabel(product.readinessStatus);
}

export function productListStatusTone(product: ProductSheet) {
  if (!product.styleGuideReady) {
    return "warning";
  }

  return productStatusTone(product.readinessStatus);
}

export function productListActionLabel(product: ProductSheet) {
  if (!product.styleGuideReady) {
    return "Importer le guide de style";
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

function productStatusTone(status: ProductSheet["readinessStatus"]) {
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

export function technicalDocumentTypeLabel(value: string | null | undefined) {
  switch (value) {
    case "TECHNICAL_SHEET":
      return "Fiche technique produit";
    case "BLUEPRINT":
      return "Plan technique";
    case "ECO_CERTIFICATE":
      return "Certificat environnemental";
    case "ASSEMBLY_NOTICE":
      return "Notice d’assemblage";
    case "MATERIAL_SPECIFICATION":
      return "Fiche matière";
    case "OUT_OF_SCOPE_DOCUMENT":
      return "Document hors périmètre";
    case "MIXED_TECHNICAL_DOSSIER":
      return "Dossier technique mélangé";
    case "UNKNOWN":
      return "Type non reconnu";
    case null:
    case undefined:
      return "Type non renseigné";
    default:
      return formatCode(value);
  }
}

export function technicalFactFieldLabel(value: string | null | undefined) {
  switch (value) {
    case "sku":
      return "SKU";
    case "product_name":
      return "Nom produit";
    case "dimension_width":
    case "dimension_width_cm":
      return "Largeur";
    case "dimension_depth":
    case "dimension_depth_cm":
      return "Profondeur";
    case "dimension_height":
    case "dimension_height_cm":
      return "Hauteur";
    case "dimension_set_raw":
      return "Dimensions source";
    case "component_dimensions":
      return "Dimensions composant";
    case "weight":
    case "weight_kg":
      return "Poids";
    case "material_primary":
      return "Matière principale";
    case "material_secondary":
      return "Matière secondaire";
    case "finish_primary":
      return "Finition principale";
    case "usage_capacity":
      return "Capacité d’usage";
    case "feature_or_accessory":
      return "Accessoire ou caractéristique";
    case "quality_control_points":
      return "Points de contrôle qualité";
    case "assembly_constraints":
      return "Contraintes d’assemblage";
    case "required_tool":
      return "Outil requis";
    case "assembly_people_required":
      return "Personnes requises";
    case "assembly_time":
      return "Temps de montage";
    case "max_torque":
      return "Couple maximal";
    case "eco_certifications":
      return "Certifications environnementales";
    case "certification_claim_type":
      return "Type de certification";
    case "covered_component":
      return "Composant couvert";
    case "excluded_component":
      return "Composant exclu";
    case "unsupported_claims":
      return "Promesses non supportées";
    case "technical_claim_limits":
      return "Limites techniques";
    case null:
    case undefined:
      return "Champ non renseigné";
    default:
      return formatCode(value);
  }
}
