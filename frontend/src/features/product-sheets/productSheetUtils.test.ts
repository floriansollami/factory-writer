import { describe, expect, it } from "vitest";

import type { ProductSheet } from "@/features/product-sheets/schema";
import {
  productListActionHint,
  productListActionLabel,
} from "@/features/product-sheets/productSheetUtils";

const baseProduct: ProductSheet = {
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
};

describe("product next action", () => {
  it("prioritizes the active style guide before product sources", () => {
    const product = { ...baseProduct, styleGuideReady: false };

    expect(productListActionLabel(product)).toBe("Activer le guide de style");
    expect(productListActionHint(product)).toBe("Requis avant génération");
  });

  it("prioritizes commercial signals after the style guide", () => {
    const product = { ...baseProduct, commercialSignalsReady: false };

    expect(productListActionLabel(product)).toBe("Préparer les signaux");
    expect(productListActionHint(product)).toBe("Données ventes et retours à vérifier");
  });

  it("falls back to the product preparation action when prerequisites are ready", () => {
    expect(productListActionLabel(baseProduct)).toBe("Préparer la fiche");
    expect(productListActionHint(baseProduct)).toBe("Ajouter les dossiers techniques");
  });
});
