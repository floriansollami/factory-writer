import { cn } from "@/lib/utils";

export type StyleGuideFlowStep = "upload" | "verify" | "analyze" | "review";

type StyleGuideFlowProgressProps = {
  className?: string;
  currentStep: StyleGuideFlowStep;
  mode?: "current" | "next";
  tone?: "light" | "dark";
};

const steps: Array<{ id: StyleGuideFlowStep; label: string }> = [
  { id: "upload", label: "Importer" },
  { id: "verify", label: "Vérifier" },
  { id: "analyze", label: "Analyser" },
  { id: "review", label: "Relire" },
];

export function StyleGuideFlowProgress({
  className,
  currentStep,
  mode = "current",
  tone = "light",
}: StyleGuideFlowProgressProps) {
  const currentIndex = steps.findIndex((step) => step.id === currentStep);
  const safeCurrentIndex = currentIndex >= 0 ? currentIndex : 0;
  const current = steps[safeCurrentIndex];

  return (
    <div
      className={cn("w-56", className)}
      aria-label={
        mode === "next"
          ? `Prochaine étape ${safeCurrentIndex + 1} sur ${steps.length} : ${current.label}`
          : `Étape ${safeCurrentIndex + 1} sur ${steps.length} : ${current.label}`
      }
    >
      <p
        className={cn(
          "text-[0.68rem] font-bold uppercase tracking-[0.14em]",
          tone === "dark" ? "text-white/58" : "text-[var(--color-muted)]",
        )}
      >
        {mode === "next" ? "Prochaine étape" : `Étape ${safeCurrentIndex + 1}/${steps.length}`} ·{" "}
        {current.label}
      </p>

      <div className="mt-1.5 grid grid-cols-4 gap-1" aria-hidden="true">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={cn(
              "h-1 rounded-full transition",
              index < safeCurrentIndex && "bg-[var(--color-sage-soft)]",
              index === safeCurrentIndex && "bg-[var(--color-gold)]",
              index > safeCurrentIndex && (tone === "dark" ? "bg-white/14" : "bg-[var(--color-stone)]"),
            )}
          />
        ))}
      </div>
    </div>
  );
}
