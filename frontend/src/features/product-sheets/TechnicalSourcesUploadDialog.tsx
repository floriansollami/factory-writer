import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, UploadCloud, X } from "lucide-react";
import { type ChangeEvent, type FormEvent, useEffect, useId, useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { persistTechnicalSourcePdf } from "@/features/product-sheets/technicalSourcePdfStore";
import { replaceTechnicalSourcesLot, uploadTechnicalSources } from "@/lib/api";

const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

const pdfFileSchema = z
  .instanceof(File)
  .refine((file) => file.name.toLowerCase().endsWith(".pdf"), "Chaque dossier technique doit être un PDF.")
  .refine((file) => file.size > 0, "Un des fichiers PDF est vide.")
  .refine(
    (file) => file.size <= MAX_UPLOAD_SIZE_BYTES,
    "Un PDF dépasse la limite de 25 Mo.",
  );

type TechnicalSourcesUploadDialogProps = {
  mode?: "upload" | "replace-lot";
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
};

export function TechnicalSourcesUploadDialog({
  mode = "upload",
  open,
  onOpenChange,
  productId,
}: TechnicalSourcesUploadDialogProps) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (selectedFiles: File[]) =>
      mode === "replace-lot"
        ? replaceTechnicalSourcesLot(productId, selectedFiles)
        : uploadTechnicalSources(productId, selectedFiles),
    onSuccess: async (response, selectedFiles) => {
      await persistUploadedTechnicalSourcePdfs({
        files: selectedFiles,
        mode,
        productId,
        sources: response.sources,
      });
      await invalidateProductQueries(queryClient, productId);
      onOpenChange(false);
    },
  });

  useEffect(() => {
    if (open) {
      return;
    }

    setFiles([]);
    setValidationError(null);
    uploadMutation.reset();
  }, [open]);

  if (!open) {
    return null;
  }

  function updateFiles(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    setFiles(selectedFiles);
    setValidationError(validatePdfFiles(selectedFiles));
    uploadMutation.reset();
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (files.length === 0) {
      setValidationError("Sélectionnez au moins un PDF technique.");
      return;
    }

    const errorMessage = validatePdfFiles(files);
    if (errorMessage !== null) {
      setValidationError(errorMessage);
      return;
    }

    if (uploadMutation.isPending) {
      return;
    }

    uploadMutation.mutate(files);
  }

  const errorMessage = validationError ?? uploadMutation.error?.message ?? null;
  const isUploading = uploadMutation.isPending;
  const selectedFilesLabel = formatSelectedFiles(files);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.22)] p-6 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-[1.5rem] bg-[var(--color-ivory)] p-6 shadow-[0_24px_70px_rgba(27,28,26,0.18)]">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Dossiers techniques
            </p>
            <h2 className="mt-2 font-serif text-2xl font-semibold tracking-[-0.035em] text-[var(--color-ink)]">
              {mode === "replace-lot"
                ? "Remplacer les dossiers techniques"
                : "Importer les PDFs techniques"}
            </h2>
            {mode === "replace-lot" ? (
              <p className="mt-2 max-w-md text-sm leading-6 text-[var(--color-muted)]">
                Le nouveau lot remplacera l’ensemble des PDFs précédents et relancera la classification.
              </p>
            ) : null}
          </div>
          <button
            className="rounded-full p-2 text-[var(--color-muted)] transition hover:bg-[var(--color-surface-raised)]"
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label="Fermer"
            disabled={isUploading}
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="space-y-5" onSubmit={submit}>
          <label htmlFor={inputId} className="block rounded-[1.35rem] bg-white/70 p-5 text-center shadow-inner">
            <UploadCloud className="mx-auto size-10 text-[var(--color-forest)]" />
            <span className="mt-4 block font-semibold text-[var(--color-ink)]">
              Sélectionner les PDFs techniques
            </span>
            <input
              id={inputId}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              multiple
              onChange={updateFiles}
              aria-label="Fichiers PDF techniques"
              disabled={isUploading}
            />
            <span className="mt-5 inline-flex min-h-11 items-center rounded-full bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-semibold text-[var(--color-ink)]">
              {selectedFilesLabel}
            </span>
          </label>

          {errorMessage ? (
            <p className="text-sm font-semibold text-[var(--color-error)]">{errorMessage}</p>
          ) : null}

          <div className="flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)} disabled={isUploading}>
              Annuler
            </Button>
            <Button type="submit" disabled={isUploading || files.length === 0}>
              {uploadMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : null}
              {mode === "replace-lot" ? "Remplacer le lot" : "Importer les dossiers"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

async function invalidateProductQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  productId: string,
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["products"] }),
    queryClient.invalidateQueries({ queryKey: ["product-overview", productId] }),
  ]);
}

function validatePdfFiles(files: File[]): string | null {
  if (files.length === 0) {
    return null;
  }

  const normalizedFileNames = new Set<string>();

  for (const file of files) {
    const result = pdfFileSchema.safeParse(file);

    if (!result.success) {
      return result.error.issues[0]?.message ?? "Fichier PDF invalide.";
    }

    const normalizedFileName = file.name.trim().toLowerCase();
    if (normalizedFileNames.has(normalizedFileName)) {
      return "Deux PDFs portent le même nom. Renommez-les avant import pour éviter une preuve ambiguë.";
    }
    normalizedFileNames.add(normalizedFileName);
  }

  return null;
}

async function persistUploadedTechnicalSourcePdfs({
  files,
  mode,
  productId,
  sources,
}: {
  files: File[];
  mode: "upload" | "replace-lot";
  productId: string;
  sources: Array<{ id: string; original_file_name: string }>;
}) {
  const sourcesByFileName = new Map(
    sources.map((source) => [source.original_file_name, source]),
  );

  await Promise.all(
    files.map((file, index) => {
      const source =
        mode === "replace-lot"
          ? sourcesByFileName.get(file.name)
          : sources[index] ?? sourcesByFileName.get(file.name);

      if (source === undefined) {
        return Promise.resolve();
      }

      return persistTechnicalSourcePdf({
        file,
        fileName: source.original_file_name,
        productId,
        sourceId: source.id,
      });
    }),
  );
}

function formatSelectedFiles(files: File[]) {
  if (files.length === 0) {
    return "Choisir un ou plusieurs PDFs";
  }

  if (files.length === 1) {
    return files[0]?.name ?? "1 PDF sélectionné";
  }

  return `${files.length} PDFs sélectionnés`;
}
