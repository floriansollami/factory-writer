import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, UploadCloud, X } from "lucide-react";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useId, useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { reuploadStyleGuidePdf, uploadStyleGuidePdf } from "@/lib/api";
import type { StyleGuideUploadResponse } from "@/features/style-guide/schema";
import { persistStyleGuidePdf } from "@/features/style-guide/styleGuidePdfStore";

const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024;

const pdfFileSchema = z
  .instanceof(File)
  .refine((file) => file.name.toLowerCase().endsWith(".pdf"), "Le guide de style doit être un PDF.")
  .refine((file) => file.size > 0, "Le fichier PDF est vide.")
  .refine(
    (file) => file.size <= MAX_UPLOAD_SIZE_BYTES,
    "Le PDF dépasse la limite de 25 Mo.",
  );

type UploadGuideDialogProps = {
  open: boolean;
  mode?: "upload" | "reupload";
  replacedDocumentSourceId?: string | null;
  onClose: () => void;
  onUploaded?: (upload: StyleGuideUploadResponse, fileName: string) => void;
};

export function UploadGuideDialog({
  open,
  mode = "upload",
  replacedDocumentSourceId = null,
  onClose,
  onUploaded,
}: UploadGuideDialogProps) {
  const inputId = useId();
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      if (mode === "reupload") {
        if (replacedDocumentSourceId === null) {
          throw new Error("Aucun document source à remplacer n'a été fourni.");
        }
        return reuploadStyleGuidePdf(replacedDocumentSourceId, file);
      }
      return uploadStyleGuidePdf(file);
    },
    onSuccess: async (upload, file) => {
      await persistStyleGuidePdf(file).catch(() => undefined);
      onUploaded?.(upload, file.name);
      await queryClient.invalidateQueries({ queryKey: ["style-guide-overview"] });
      setSelectedFile(null);
      setValidationError(null);
      onClose();
    },
  });

  useEffect(() => {
    if (!open) {
      setSelectedFile(null);
      setValidationError(null);
      uploadMutation.reset();
    }
  }, [open, mode, replacedDocumentSourceId]);

  if (!open) {
    return null;
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setValidationError(file ? validatePdfFile(file) : null);
    uploadMutation.reset();
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (selectedFile === null) {
      setValidationError("Sélectionnez le PDF officiel du guide de style.");
      return;
    }

    const errorMessage = validatePdfFile(selectedFile);
    if (errorMessage !== null) {
      setValidationError(errorMessage);
      return;
    }

    uploadMutation.mutate(selectedFile);
  }

  const errorMessage = validationError ?? uploadMutation.error?.message ?? null;
  const isUploading = uploadMutation.isPending;
  const title = mode === "reupload" ? "Remplacer le guide importé" : "Importer le guide officiel";
  const submitLabel = mode === "reupload" ? "Remplacer le guide" : "Importer le guide";

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.22)] p-6 backdrop-blur-sm">
      <div className="w-full max-w-xl rounded-[1.5rem] bg-[var(--color-ivory)] p-6 shadow-[0_24px_70px_rgba(27,28,26,0.18)]">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Guide de style
            </p>
            <h2 className="mt-2 font-serif text-2xl font-semibold tracking-[-0.035em] text-[var(--color-ink)]">
              {title}
            </h2>
          </div>
          <button
            className="rounded-full p-2 text-[var(--color-muted)] transition hover:bg-[var(--color-surface-raised)]"
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            disabled={isUploading}
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="space-y-5" onSubmit={onSubmit}>
          <label htmlFor={inputId} className="block rounded-[1.35rem] bg-white/70 p-5 text-center shadow-inner">
            <UploadCloud className="mx-auto size-10 text-[var(--color-forest)]" />
            <span className="mt-4 block font-semibold text-[var(--color-ink)]">
              Sélectionner le PDF du guide de style
            </span>
            <input
              id={inputId}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={onFileChange}
              aria-label="Fichier PDF du guide de style"
              disabled={isUploading}
            />
            <span className="mt-5 inline-flex min-h-11 items-center rounded-full bg-[var(--color-surface-raised)] px-5 py-3 text-sm font-semibold text-[var(--color-ink)]">
              {selectedFile?.name ?? "Choisir un fichier PDF"}
            </span>
          </label>

          {errorMessage ? (
            <p className="text-sm font-semibold text-[var(--color-error)]">{errorMessage}</p>
          ) : null}

          <div className="flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isUploading}>
              Annuler
            </Button>
            <Button type="submit" disabled={isUploading || selectedFile === null}>
              {isUploading ? <Loader2 className="size-4 animate-spin" /> : null}
              {submitLabel}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function validatePdfFile(file: File): string | null {
  const result = pdfFileSchema.safeParse(file);
  if (result.success) {
    return null;
  }
  return result.error.issues[0]?.message ?? "Fichier PDF invalide.";
}
