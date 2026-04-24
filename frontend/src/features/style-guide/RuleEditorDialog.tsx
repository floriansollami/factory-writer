import { zodResolver } from "@hookform/resolvers/zod";
import { X } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import type { StyleRule } from "@/features/style-guide/schema";

const ruleFormSchema = z
  .object({
    typeRegle: z.enum(["VOIX", "TON", "FORMATAGE", "PROMESSE_INTERDITE"]),
    niveauContrainte: z.enum(["HARD", "SOFT"]),
    texteRegle: z.string().trim().min(8, "La règle doit être explicite."),
    taxonomieCode: z.string().trim(),
  })
  .superRefine((value, context) => {
    if (value.typeRegle === "TON" && value.taxonomieCode.length === 0) {
      context.addIssue({
        code: "custom",
        path: ["taxonomieCode"],
        message: "Une règle de ton doit cibler une famille produit.",
      });
    }
    if (value.typeRegle !== "TON" && value.taxonomieCode.length > 0) {
      context.addIssue({
        code: "custom",
        path: ["taxonomieCode"],
        message: "Seules les règles de ton peuvent cibler une famille produit.",
      });
    }
    if (
      value.typeRegle === "PROMESSE_INTERDITE" &&
      value.niveauContrainte !== "HARD"
    ) {
      context.addIssue({
        code: "custom",
        path: ["niveauContrainte"],
        message: "Une promesse interdite doit toujours être en niveau HARD.",
      });
    }
  });

type RuleForm = z.infer<typeof ruleFormSchema>;

type RuleEditorDialogProps = {
  open: boolean;
  rule: StyleRule;
  taxonomyOptions: string[];
  onClose: () => void;
  onSave: (rule: StyleRule) => void | Promise<void>;
};

export function RuleEditorDialog({
  open,
  rule,
  taxonomyOptions,
  onClose,
  onSave,
}: RuleEditorDialogProps) {
  const [isSaving, setIsSaving] = useState(false);
  const form = useForm<RuleForm>({
    resolver: zodResolver(ruleFormSchema),
    values: {
      typeRegle: rule.typeRegle,
      niveauContrainte: rule.niveauContrainte,
      texteRegle: rule.texteRegle,
      taxonomieCode: rule.taxonomieCode ?? "",
    },
  });
  const selectedTypeRegle = form.watch("typeRegle");

  useEffect(() => {
    if (selectedTypeRegle !== "TON" && form.getValues("taxonomieCode") !== "") {
      form.setValue("taxonomieCode", "", { shouldValidate: true });
    }
    if (
      selectedTypeRegle === "PROMESSE_INTERDITE" &&
      form.getValues("niveauContrainte") !== "HARD"
    ) {
      form.setValue("niveauContrainte", "HARD", { shouldValidate: true });
    }
  }, [form, selectedTypeRegle]);

  if (!open) {
    return null;
  }

  async function onSubmit(values: RuleForm) {
    setIsSaving(true);
    try {
      await onSave({
        ...rule,
        typeRegle: values.typeRegle,
        niveauContrainte:
          values.typeRegle === "PROMESSE_INTERDITE"
            ? "HARD"
            : values.niveauContrainte,
        texteRegle: values.texteRegle,
        taxonomieCode: values.taxonomieCode || null,
      });
      onClose();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.22)] p-6 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-[1.5rem] bg-[var(--color-ivory)] p-6 shadow-[0_24px_70px_rgba(27,28,26,0.18)]">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Règle de style
            </p>
            <h2 className="mt-2 font-serif text-2xl font-semibold tracking-[-0.035em] text-[var(--color-ink)]">
              Modifier la règle
            </h2>
          </div>
          <button
            className="rounded-full p-2 text-[var(--color-muted)] transition hover:bg-[var(--color-surface-raised)]"
            type="button"
            onClick={onClose}
            aria-label="Fermer"
          >
            <X className="size-5" />
          </button>
        </div>

        <form className="space-y-5" onSubmit={form.handleSubmit(onSubmit)}>
          <div className="grid grid-cols-2 gap-4 max-md:grid-cols-1">
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
                Type de règle
              </span>
              <select
                className="mt-2 w-full rounded-2xl bg-white/80 px-4 py-3 text-sm outline-none ring-1 ring-[var(--color-stone)] focus:ring-2 focus:ring-[var(--color-forest)]"
                {...form.register("typeRegle")}
              >
                <option value="VOIX">VOIX</option>
                <option value="TON">TON</option>
                <option value="FORMATAGE">FORMATAGE</option>
                <option value="PROMESSE_INTERDITE">PROMESSE_INTERDITE</option>
              </select>
            </label>

            <label className="block">
              <span className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
                Niveau de contrainte
              </span>
              <select
                className="mt-2 w-full rounded-2xl bg-white/80 px-4 py-3 text-sm outline-none ring-1 ring-[var(--color-stone)] focus:ring-2 focus:ring-[var(--color-forest)]"
                {...form.register("niveauContrainte")}
              >
                <option value="HARD">HARD</option>
                <option
                  value="SOFT"
                  disabled={selectedTypeRegle === "PROMESSE_INTERDITE"}
                >
                  SOFT
                </option>
              </select>
              {form.formState.errors.niveauContrainte ? (
                <span className="mt-2 block text-sm font-semibold text-[var(--color-error)]">
                  {form.formState.errors.niveauContrainte.message}
                </span>
              ) : null}
            </label>
          </div>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
              Portée produit
            </span>
            <select
              className="mt-2 w-full rounded-2xl bg-white/80 px-4 py-3 text-sm outline-none ring-1 ring-[var(--color-stone)] focus:ring-2 focus:ring-[var(--color-forest)]"
              disabled={selectedTypeRegle !== "TON"}
              {...form.register("taxonomieCode")}
            >
              <option value="">Globale</option>
              {taxonomyOptions.map((taxonomy) => (
                <option key={taxonomy} value={taxonomy}>
                  {taxonomy}
                </option>
              ))}
            </select>
            {form.formState.errors.taxonomieCode ? (
              <span className="mt-2 block text-sm font-semibold text-[var(--color-error)]">
                {form.formState.errors.taxonomieCode.message}
              </span>
            ) : null}
          </label>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-[0.14em] text-[var(--color-muted)]">
              Texte de la règle
            </span>
            <textarea
              className="mt-2 min-h-32 w-full resize-none rounded-[1.25rem] bg-white/80 px-4 py-3 text-sm leading-6 outline-none ring-1 ring-[var(--color-stone)] focus:ring-2 focus:ring-[var(--color-forest)]"
              {...form.register("texteRegle")}
            />
            {form.formState.errors.texteRegle ? (
              <span className="mt-2 block text-sm font-semibold text-[var(--color-error)]">
                {form.formState.errors.texteRegle.message}
              </span>
            ) : null}
          </label>

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isSaving}
            >
              Annuler
            </Button>
            <Button type="submit" disabled={isSaving}>
              Enregistrer
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
