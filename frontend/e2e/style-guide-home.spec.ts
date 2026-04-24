import { expect, type Page, test } from "@playwright/test";

async function openStyleGuide(page: Page) {
  await page
    .getByLabel("Navigation principale")
    .getByRole("button", { name: "Guide de style" })
    .click();
}

test("displays the style guide home screen", async ({ page }) => {
  await page.goto("/");
  await openStyleGuide(page);

  await expect(page.getByRole("heading", { name: "Guide de style", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Importer le guide de style officiel" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Importer le guide de style/i })).toBeVisible();
  await expect(page.getByText("Parcours du guide de style")).toBeVisible();
  await expect(page.getByText("4. Relire les règles")).toBeVisible();
  await expect(page.getByRole("button", { name: /Ouvrir la revue/i })).toHaveCount(0);
});

test("opens the upload dialog", async ({ page }) => {
  await page.goto("/");
  await openStyleGuide(page);

  await page.getByRole("button", { name: /Importer le guide de style/i }).click();

  await expect(page.getByRole("heading", { name: "Importer le guide officiel" })).toBeVisible();
  await expect(page.getByLabel("Fichier PDF du guide de style")).toBeAttached();
  await expect(page.getByText("Choisir un fichier PDF")).toBeVisible();
});

test("uploads a style guide PDF", async ({ page }) => {
  await page.goto("/");
  await openStyleGuide(page);

  await page.getByRole("button", { name: /Importer le guide de style/i }).click();
  await page.getByLabel("Fichier PDF du guide de style").setInputFiles({
    name: "AXOLOTL_STYLE_GUIDE_V2.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n% Factory Writer POC\n"),
  });
  await expect(page.getByText("AXOLOTL_STYLE_GUIDE_V2.pdf")).toBeVisible();

  await page.getByRole("button", { name: "Importer le guide", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Importer le guide officiel" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Vérifier le guide avant analyse" })).toBeVisible();
  await expect(page.getByText("L’analyse démarre uniquement après confirmation")).toBeVisible();

  await page.getByRole("button", { name: "Lancer l’analyse du guide" }).click();
  await expect(page.getByRole("heading", { name: "Analyse du guide en cours" })).toBeVisible();
  await expect(page.getByText("Extraction du contenu")).toBeVisible();
  await expect(page.getByText("Pack candidat", { exact: true })).toBeVisible();
  await expect(page.getByText("Revue éditoriale")).toBeVisible();
});
