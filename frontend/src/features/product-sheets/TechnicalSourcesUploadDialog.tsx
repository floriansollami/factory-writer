import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, PlayCircle, UploadCloud, X } from "lucide-react";
import { type ChangeEvent, type FormEvent, useEffect, useId, useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { uploadTechnicalSources, startTechnicalIngestion } from "@/lib/api";

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
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productId: string;
};

export function TechnicalSourcesUploadDialog({
  open,
  onOpenChange,
  productId,
}: TechnicalSourcesUploadDialogProps) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadedSourcesCount, setUploadedSourcesCount] = useState(0);
  const [startError, setStartError] = useState<string | null>(null);

  const startMutation = useMutation({
    mutationFn: () => startTechnicalIngestion(productId),
    onSuccess: async () => {
      await invalidateProductQueries(queryClient, productId);
      onOpenChange(false);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (selectedFiles: File[]) => {
      setStartError(null);
      const upload = await uploadTechnicalSources(productId, selectedFiles);
      setUploadedSourcesCount(upload.sources.length);

      try {
        return await startTechnicalIngestion(productId);
      } catch (error) {
        setStartError(error instanceof Error ? error.message : "Impossible de lancer l’analyse.");
        return null;
      }
    },
    onSuccess: async (started) => {
      await invalidateProductQueries(queryClient, productId);

      if (started !== null) {
        onOpenChange(false);
      }
    },
  });

  useEffect(() => {
    if (open) {
      return;
    }

    setFiles([]);
    setValidationError(null);
    setUploadedSourcesCount(0);
    setStartError(null);
    uploadMutation.reset();
    startMutation.reset();
  }, [open]);

  if (!open) {
    return null;
  }

  function updateFiles(event: ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(event.target.files ?? []);
    setFiles(selectedFiles);
    setValidationError(validatePdfFiles(selectedFiles));
    setUploadedSourcesCount(0);
    setStartError(null);
    uploadMutation.reset();
    startMutation.reset();
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

  const errorMessage =
    validationError ?? uploadMutation.error?.message ?? startError ?? startMutation.error?.message ?? null;
  const isUploading = uploadMutation.isPending || startMutation.isPending;
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
              Importer les PDFs techniques
            </h2>
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

          {uploadedSourcesCount > 0 && startError !== null ? (
            <p className="text-sm font-semibold text-[var(--color-teak)]">
              {uploadedSourcesCount} source{uploadedSourcesCount > 1 ? "s" : ""} importée
              {uploadedSourcesCount > 1 ? "s" : ""}. L’analyse n’a pas démarré automatiquement.
            </p>
          ) : null}

          {errorMessage ? (
            <p className="text-sm font-semibold text-[var(--color-error)]">{errorMessage}</p>
          ) : null}

          <div className="flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)} disabled={isUploading}>
              Annuler
            </Button>
            {uploadedSourcesCount > 0 && startError !== null ? (
              <Button
                type="button"
                disabled={startMutation.isPending}
                onClick={() => startMutation.mutate()}
              >
                {startMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <PlayCircle className="size-4" />
                )}
                Lancer l’analyse
              </Button>
            ) : (
              <Button type="submit" disabled={isUploading || files.length === 0}>
                {uploadMutation.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : null}
                Importer et analyser
              </Button>
            )}
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

  for (const file of files) {
    const result = pdfFileSchema.safeParse(file);

    if (!result.success) {
      return result.error.issues[0]?.message ?? "Fichier PDF invalide.";
    }
  }

  return null;
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
