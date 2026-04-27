import { FileCheck2, FileText, X } from "lucide-react";
import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CompactProviderMetadata,
  type ProductStepMetadataField,
} from "@/features/product-sheets/ProductStepMetadata";
import {
  loadTechnicalSourcePdf,
  loadTechnicalSourcePdfByFileName,
} from "@/features/product-sheets/technicalSourcePdfStore";
import type {
  TechnicalFactCandidate,
  TechnicalSource,
} from "@/features/product-sheets/schema";
import { technicalFactFieldLabel } from "@/features/product-sheets/productSheetUtils";
import { SourcePdfPreview } from "@/features/style-guide/SourcePdfDialog";
import { cn } from "@/lib/utils";

type TechnicalExtractionResultsDisclosureProps = {
  candidates: TechnicalFactCandidate[];
  metadata: ProductStepMetadataField[];
  sources: TechnicalSource[];
};

export function TechnicalExtractionResultsDisclosure({
  candidates,
  metadata,
  sources,
}: TechnicalExtractionResultsDisclosureProps) {
  const [selectedCandidate, setSelectedCandidate] = useState<TechnicalFactCandidate | null>(
    null,
  );
  const sourceById = new Map(sources.map((source) => [source.id, source]));
  const candidateGroups = groupExtractionCandidatesBySource(candidates, sources);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(
    candidateGroups[0]?.sourceId ?? null,
  );
  const selectedGroup =
    candidateGroups.find((group) => group.sourceId === selectedSourceId) ??
    candidateGroups[0] ??
    null;
  const selectedCandidates = selectedGroup?.candidates ?? [];
  const occurrenceLabels = buildExtractionCandidateOccurrenceLabels(selectedCandidates);

  return (
    <>
      <details className="group mt-3 w-full max-w-5xl">
        <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 rounded-2xl bg-[var(--color-surface-raised)]/55 px-4 py-2.5 text-sm font-semibold text-[var(--color-forest)] transition hover:bg-[var(--color-sage-soft)]/55 [&::-webkit-details-marker]:hidden">
          <span
            aria-hidden="true"
            className="size-0 border-y-[4px] border-l-[6px] border-y-transparent border-l-current transition-transform group-open:rotate-90"
          />
          Résultats d’extraction
        </summary>

        <div className="mt-3 rounded-[1.35rem] bg-[var(--color-surface-raised)]/35 p-2.5 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
          <div className="grid gap-2 lg:grid-cols-[15rem_minmax(0,1fr)]">
            <div className="rounded-2xl bg-[var(--color-ivory)] p-1.5">
              <div className="grid gap-1.5" role="tablist" aria-label="PDFs extraits">
                {candidateGroups.map((group, index) => {
                  const isSelected = selectedGroup?.sourceId === group.sourceId;

                  return (
                    <button
                      key={group.sourceId}
                      type="button"
                      role="tab"
                      aria-selected={isSelected}
                      className={cn(
                        "flex min-w-0 items-center gap-3 rounded-[1.05rem] px-3 py-2.5 text-left transition",
                        isSelected
                          ? "bg-white text-[var(--color-forest)] shadow-[0_10px_24px_rgba(27,28,26,0.07)]"
                          : "text-[var(--color-muted)] hover:bg-white/55 hover:text-[var(--color-ink)]",
                      )}
                      onClick={() => setSelectedSourceId(group.sourceId)}
                    >
                      <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[var(--color-sage-soft)] text-[var(--color-forest)]">
                        <FileCheck2 className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[0.68rem] font-bold uppercase tracking-[0.14em]">
                          PDF {index + 1}
                        </span>
                        <span className="mt-0.5 block break-all text-[0.58rem] font-semibold leading-3 text-[var(--color-muted)]">
                          {group.fileName}
                        </span>
                      </span>
                      <Badge tone="neutral" className="shrink-0">
                        {group.candidates.length}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="overflow-hidden rounded-2xl bg-white/60 shadow-[inset_0_0_0_1px_rgba(23,49,36,0.07)]">
              <div className="grid grid-cols-[minmax(14rem,0.85fr)_minmax(14rem,1fr)_5.5rem_6.5rem] gap-3 border-b border-black/5 px-3 py-2 text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:hidden">
                <span>Label</span>
                <span>Valeur brute extraite</span>
                <span>
                  Score<sup>*</sup>
                </span>
                <span className="text-right">Preuve</span>
              </div>

              {selectedCandidates.map((candidate) => {
                const source = sourceById.get(candidate.source_id) ?? null;
                const proofText = extractionCandidateProofText(candidate);
                const proofDisabled = source === null || proofText === null;
                const occurrenceLabel = occurrenceLabels.get(candidate.id);
                const labelMetadata = technicalFactLabelMetadata();
                const labelDescription = technicalFactLabelDescription(
                  candidate.field_name,
                  source?.document_type,
                );

                return (
                  <div
                    key={candidate.id}
                    className="grid grid-cols-[minmax(14rem,0.85fr)_minmax(14rem,1fr)_5.5rem_6.5rem] items-center gap-3 border-b border-black/5 bg-white/50 px-3 py-2.5 last:border-b-0 max-lg:grid-cols-[minmax(0,1fr)_auto] max-lg:gap-y-2"
                  >
                    <div className="min-w-0">
                      <p
                        className="min-w-0 cursor-help truncate text-sm font-semibold text-[var(--color-ink)]"
                        title={labelDescription}
                      >
                        {candidate.field_name}
                        {occurrenceLabel ? (
                          <span className="ml-1 text-[0.68rem] font-bold text-[var(--color-muted)]">
                            {occurrenceLabel}
                          </span>
                        ) : null}
                      </p>
                      <p className="mt-0.5 whitespace-nowrap text-[0.52rem] font-bold uppercase leading-3 tracking-[0.06em] text-[var(--color-muted)]">
                        {labelMetadata.dataType} · {labelMetadata.method} ·{" "}
                        {labelMetadata.occurrence}
                      </p>
                    </div>

                    <p
                      className="min-w-0 whitespace-normal break-words text-xs font-semibold leading-5 text-[var(--color-forest)] max-lg:col-start-1"
                      title={extractionCandidateDisplayValue(candidate)}
                    >
                      <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
                        Valeur
                      </span>
                      {extractionCandidateDisplayValue(candidate)}
                    </p>

                    <p className="text-xs font-semibold text-[var(--color-ink)] max-lg:col-start-1">
                      <span className="mr-1 hidden text-[0.64rem] font-bold uppercase tracking-[0.14em] text-[var(--color-muted)] max-lg:inline">
                        Score*
                      </span>
                      {formatGcpConfidence(candidate.extractor_confidence)}
                    </p>

                    <Button
                      className="justify-self-end"
                      size="sm"
                      variant="secondary"
                      disabled={proofDisabled}
                      onClick={() => setSelectedCandidate(candidate)}
                    >
                      <FileText className="size-4" />
                      Voir
                    </Button>
                  </div>
                );
              })}
              <p className="border-t border-black/5 bg-white/35 px-3 py-2 text-[0.68rem] font-medium leading-4 text-[var(--color-muted)]">
                <span className="font-bold text-[var(--color-forest)]">*</span> Score de
                confiance Document AI : confiance de l’entité de schéma détectée,
                comprise entre 0 et 1 dans la réponse Google, affichée ici en
                pourcentage. Ce score guide le contrôle, mais ne remplace pas la
                validation déterministe.
              </p>
            </div>
          </div>

          <CompactProviderMetadata fields={metadata} />
        </div>
      </details>

      {selectedCandidate ? (
        <TechnicalSourcePdfDialog
          candidate={selectedCandidate}
          onClose={() => setSelectedCandidate(null)}
          source={sourceById.get(selectedCandidate.source_id) ?? null}
        />
      ) : null}
    </>
  );
}

function TechnicalSourcePdfDialog({
  candidate,
  onClose,
  source,
}: {
  candidate: TechnicalFactCandidate;
  onClose: () => void;
  source: TechnicalSource | null;
}) {
  const proofText = extractionCandidateProofText(candidate) ?? "";
  const fileName = source?.original_file_name ?? "PDF technique";
  const sourceId = source?.id ?? null;
  const loadPdf = useCallback(async () => {
    if (sourceId === null) {
      return null;
    }

    return (await loadTechnicalSourcePdf(sourceId)) ?? loadTechnicalSourcePdfByFileName(fileName);
  }, [fileName, sourceId]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[rgba(23,49,36,0.26)] p-5 backdrop-blur-sm">
      <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-[1.6rem] bg-[var(--color-ivory)] shadow-[0_28px_90px_rgba(27,28,26,0.22)]">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-black/5 px-6 py-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--color-teak)]">
              Preuve PDF
            </p>
            <h2 className="mt-1 truncate font-serif text-2xl font-semibold tracking-[-0.035em] text-[var(--color-ink)]">
              {technicalFactFieldLabel(candidate.field_name)}
            </h2>
            <p className="mt-1 max-w-3xl truncate text-sm font-semibold text-[var(--color-muted)]">
              {fileName} · {extractionCandidateDisplayValue(candidate)}
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={onClose}>
            <X className="size-4" />
            Fermer
          </Button>
        </div>

        <div className="min-h-0 flex-1 p-4">
          {source === null ? (
            <div className="grid h-full place-items-center rounded-[1.25rem] bg-white/70 px-6 text-center">
              <div>
                <p className="font-serif text-2xl font-semibold tracking-[-0.04em] text-[var(--color-ink)]">
                  Source introuvable
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
                  Le document source n’est plus associé à ce fait extrait.
                </p>
              </div>
            </div>
          ) : (
            <SourcePdfPreview
              className="h-full"
              excerpt={proofText}
              fileName={fileName}
              loadPdf={loadPdf}
              pageEnd={candidate.source_page}
              pageStart={candidate.source_page}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function extractionCandidateProofText(candidate: TechnicalFactCandidate) {
  const value = candidate.raw_value ?? candidate.normalized_value;
  return value !== null && value.trim().length > 0 ? value : null;
}

function extractionCandidateDisplayValue(candidate: TechnicalFactCandidate) {
  const rawValue = candidate.raw_value?.trim();
  if (rawValue) {
    return rawValue;
  }

  const normalizedValue = candidate.normalized_value?.trim();
  if (!normalizedValue) {
    return "Non extrait";
  }

  return candidate.unit ? `${normalizedValue} ${candidate.unit}` : normalizedValue;
}

type ExtractionCandidateGroup = {
  sourceId: string;
  fileName: string;
  candidates: TechnicalFactCandidate[];
};

function groupExtractionCandidatesBySource(
  candidates: TechnicalFactCandidate[],
  sources: TechnicalSource[],
): ExtractionCandidateGroup[] {
  const candidatesBySourceId = new Map<string, TechnicalFactCandidate[]>();

  for (const candidate of candidates) {
    const group = candidatesBySourceId.get(candidate.source_id) ?? [];
    group.push(candidate);
    candidatesBySourceId.set(candidate.source_id, group);
  }

  const groups = sources.flatMap((source) => {
    const sourceCandidates = candidatesBySourceId.get(source.id) ?? [];
    return sourceCandidates.length === 0
      ? []
      : [
          {
            sourceId: source.id,
            fileName: source.original_file_name,
            candidates: sourceCandidates,
          },
        ];
  });

  for (const [sourceId, sourceCandidates] of candidatesBySourceId.entries()) {
    if (sources.some((source) => source.id === sourceId)) {
      continue;
    }

    groups.push({
      sourceId,
      fileName: "PDF technique",
      candidates: sourceCandidates,
    });
  }

  return groups;
}

function buildExtractionCandidateOccurrenceLabels(
  candidates: TechnicalFactCandidate[],
): Map<string, string> {
  const totalsByFieldName = new Map<string, number>();
  const seenByFieldName = new Map<string, number>();
  const labelsByCandidateId = new Map<string, string>();

  for (const candidate of candidates) {
    totalsByFieldName.set(
      candidate.field_name,
      (totalsByFieldName.get(candidate.field_name) ?? 0) + 1,
    );
  }

  for (const candidate of candidates) {
    const total = totalsByFieldName.get(candidate.field_name) ?? 0;
    if (total <= 1) {
      continue;
    }

    const index = (seenByFieldName.get(candidate.field_name) ?? 0) + 1;
    seenByFieldName.set(candidate.field_name, index);
    labelsByCandidateId.set(candidate.id, `${index}/${total}`);
  }

  return labelsByCandidateId;
}

function technicalFactLabelMetadata(): {
  dataType: string;
  method: string;
  occurrence: string;
} {
  return {
    dataType: "Plain text",
    method: "Extract",
    occurrence: "Optional multiple",
  };
}

export function technicalFactLabelDescription(
  fieldName: string,
  documentType: string | null | undefined,
) {
  const scopedDescription =
    TECHNICAL_FACT_LABEL_DESCRIPTIONS[`${documentType ?? ""}:${fieldName}`];
  return scopedDescription ?? TECHNICAL_FACT_LABEL_DESCRIPTIONS[fieldName] ?? fieldName;
}

const TECHNICAL_FACT_LABEL_DESCRIPTIONS: Record<string, string> = {
  "TECHNICAL_SHEET:component_dimensions":
    "Extraire les dimensions d’un composant important : plateau, piètement, cadre, assise, manche, lame, toile, roue ou bac. Conserver unités et tolérances. Ne pas extraire les dimensions globales du produit fini ni du colis.",
  "TECHNICAL_SHEET:dimension_depth":
    "Extraire la profondeur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la deuxième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant.",
  "TECHNICAL_SHEET:dimension_height":
    "Extraire la hauteur du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la troisième valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire la hauteur de colis.",
  "TECHNICAL_SHEET:dimension_set_raw":
    "Extraire la ligne ou cellule complète qui donne les dimensions du produit fini avec ordre et unité : L/P/H, L x P x H, largeur/profondeur/hauteur, mm, cm ou m. Ne pas convertir. Ne pas extraire dimensions colis ou composant.",
  "TECHNICAL_SHEET:dimension_width":
    "Extraire la largeur ou longueur principale du produit fini exactement comme écrite. Si les dimensions sont groupées (L/P/H, L x P x H), prendre la première valeur selon l’ordre annoncé. Conserver l’unité source si visible. Ne pas convertir. Ne pas extraire une dimension de colis ou composant.",
  "TECHNICAL_SHEET:feature_or_accessory":
    "Extraire les fonctionnalités ou accessoires techniques écrits : passage parasol, patins, poignée, lame, housse, verrouillage, batterie, réglage.",
  "TECHNICAL_SHEET:finish_primary":
    "Extraire la finition principale : huile, peinture, poudre, couleur, RAL, traitement de surface ou aspect. Ne pas transformer en promesse de durabilité.",
  "TECHNICAL_SHEET:material_primary":
    "Extraire la matière principale du produit ou de la partie dominante. Inclure essence, grade, alliage ou nom scientifique si présents. Ne rien inventer.",
  "TECHNICAL_SHEET:material_secondary":
    "Extraire les matières secondaires structurantes : piètement, cadre, visserie, manche, lame, textile, batterie. Inclure grade ou finition si écrit.",
  "TECHNICAL_SHEET:product_name":
    "Extraire le nom ou la désignation produit exacte couverte par la fiche technique. Prendre le nom le plus spécifique. Ne pas extraire une famille générique ni un autre produit cité.",
  "TECHNICAL_SHEET:quality_control_points":
    "Extraire les critères de contrôle qualité explicitement listés : stabilité, jeu, tolérance, nettoyage, conformité atelier. Garder les formulations techniques.",
  "TECHNICAL_SHEET:sku":
    "Extraire la référence produit, SKU ou code article exact. Conserver lettres, chiffres et tirets. Ne pas confondre avec lot, révision ou tampon documentaire.",
  "TECHNICAL_SHEET:technical_claim_limits":
    "Extraire les notes qui limitent l’usage marketing des données techniques : absence de garantie permanente, entretien limité, usage non absolu. Ne pas créer de restriction absente.",
  "TECHNICAL_SHEET:usage_capacity":
    "Extraire la capacité d’usage explicitement indiquée : nombre de places, charge, volume, surface couverte ou cadence recommandée. Ne pas déduire depuis les dimensions.",
  "TECHNICAL_SHEET:weight":
    "Extraire le poids du produit hors emballage exactement comme écrit. Conserver l’unité source, la tolérance ou la plage si présentes. Ne pas convertir. Ne pas extraire le poids du colis, de la palette ou de l’emballage.",
  "MATERIAL_SPECIFICATION:assembly_site":
    "Extraire le site d’assemblage, fabrication ou pays d’origine s’il est explicitement écrit. Ne pas déduire depuis une langue ou un code.",
  "MATERIAL_SPECIFICATION:certificate_valid_until":
    "Extraire la date de validité, expiration ou prochaine vérification. Ne pas extraire la date d’émission si aucune validité n’est indiquée.",
  "MATERIAL_SPECIFICATION:certification_claim_type":
    "Extraire le type exact de revendication certifiée, par exemple FSC Mix Credit. Ne jamais transformer en claim plus fort comme 100 % FSC.",
  "MATERIAL_SPECIFICATION:chain_of_custody_code":
    "Extraire le code de chaîne de contrôle, CoC ou audit associé. Conserver le format exact et ne pas le confondre avec une licence de marque.",
  "MATERIAL_SPECIFICATION:covered_component":
    "Extraire les composants explicitement couverts par la preuve ou certification. Ne pas inclure les composants seulement listés ou exclus.",
  "MATERIAL_SPECIFICATION:eco_certifications":
    "Extraire les certifications ou preuves environnementales explicitement valides : FSC, PEFC, SVLK, FLEGT, REACH, RoHS, recyclé, origine contrôlée.",
  "MATERIAL_SPECIFICATION:excluded_component":
    "Extraire les composants explicitement exclus du périmètre de certification ou d’attestation. Garder la formulation précise.",
  "MATERIAL_SPECIFICATION:legality_export_reference":
    "Extraire les références de légalité export ou traçabilité, par exemple SVLK, FLEGT ou batch export. Conserver le code complet.",
  "MATERIAL_SPECIFICATION:license_or_certificate_code":
    "Extraire les codes de licence, certificat, audit ou conformité. Conserver lettres, tirets et chiffres. Ne pas fusionner plusieurs codes.",
  "MATERIAL_SPECIFICATION:material_origin":
    "Extraire l’origine déclarée de la matière : pays, plantation, provenance, lot ou légalité export. Ne pas inventer depuis le fournisseur.",
  "MATERIAL_SPECIFICATION:material_primary":
    "Extraire la matière, essence, alliage ou composition principale déclarée. Inclure nom scientifique, grade ou origine si présents.",
  "MATERIAL_SPECIFICATION:product_name":
    "Extraire le produit couvert par l’attestation matière ou conformité. Ne pas extraire un produit mentionné comme exemple, exclusion ou référence secondaire.",
  "MATERIAL_SPECIFICATION:sku":
    "Extraire le SKU, référence article ou code produit concerné par l’attestation. Conserver le format exact. Ne pas confondre avec lot ou certificat.",
  "MATERIAL_SPECIFICATION:supplier_name":
    "Extraire le fournisseur, fabricant, site ou organisme émetteur de la déclaration. Ne pas extraire la marque commerciale si elle n’est pas l’émetteur.",
  "MATERIAL_SPECIFICATION:unsupported_claims":
    "Extraire les mentions que le document interdit ou ne permet pas d’affirmer : 100 % FSC, zéro entretien, garantie permanente, matériau certifié à tort.",
  "ASSEMBLY_NOTICE:assembly_constraints":
    "Extraire les contraintes de montage qui conditionnent la qualité ou la sécurité : support, ordre, jeu, serrage progressif, interdictions, tolérances.",
  "ASSEMBLY_NOTICE:assembly_people_required":
    "Extraire le nombre de personnes ou opérateurs nécessaires au montage. Conserver la formulation source, par exemple 2 adultes.",
  "ASSEMBLY_NOTICE:assembly_product_ref":
    "Extraire la référence de colis, article, notice ou version de montage. Conserver le format exact. Ne pas confondre avec le SKU commercial.",
  "ASSEMBLY_NOTICE:assembly_steps":
    "Extraire la séquence opératoire dans l’ordre : préparer, présenter, équerrer, serrer, régler, contrôler. Garder verbes et contraintes clés.",
  "ASSEMBLY_NOTICE:assembly_time":
    "Extraire le temps de montage indiqué ou constaté exactement comme écrit. Conserver l’unité source et la plage si présentes. Ne pas convertir. Ne pas additionner des étapes si aucun total n’est écrit.",
  "ASSEMBLY_NOTICE:clearance_or_tolerance":
    "Extraire les jeux, tolérances ou écarts acceptés : diagonales, jeu bois/métal, écart de montage, distance minimale. Conserver unités et tolérances. Ne pas convertir.",
  "ASSEMBLY_NOTICE:final_quality_check":
    "Extraire les contrôles finaux demandés après montage : stabilité, hauteur finie, patins, serrage, alignement, surface plane.",
  "ASSEMBLY_NOTICE:hardware_list":
    "Extraire la quincaillerie : vis, rondelles, inserts, patins, sachets. Inclure dimensions et quantités si disponibles. Ne pas extraire les outils.",
  "ASSEMBLY_NOTICE:max_torque":
    "Extraire le couple de serrage maximum ou recommandé exactement comme écrit. Conserver l’unité source, par exemple N·m. Ne pas convertir. Ne pas extraire un diamètre, une taille ou une référence de vis.",
  "ASSEMBLY_NOTICE:parts_list":
    "Extraire la liste des pièces principales à assembler : structure, cadre, pieds, assise, manche, lame, toile, roues, bac ou modules. Inclure quantités si écrites. Ne pas inclure les étapes.",
  "ASSEMBLY_NOTICE:product_name":
    "Extraire le nom, article ou référence du produit concerné par la notice. Ne pas extraire le nom d’une pièce ou d’un composant isolé.",
  "ASSEMBLY_NOTICE:prohibited_actions":
    "Extraire les actions explicitement interdites : visseuse à choc, reperçage, collage, levage incorrect, usage abrasif. Ne pas reformuler en bénéfice.",
  "ASSEMBLY_NOTICE:required_tool":
    "Extraire les outils nécessaires ou fournis : clé Allen, tournevis, maillet, gabarit, niveau. Ne pas extraire la visserie comme outil.",
  "ASSEMBLY_NOTICE:use_or_safety_warning":
    "Extraire les avertissements d’usage ou sécurité après montage. Ne pas transformer en argument marketing ni inventer de risque absent.",
};

function formatGcpConfidence(value: number | null) {
  if (value === null || !Number.isFinite(value)) {
    return "Non renseigné";
  }

  return `${truncateDecimal(value * 100, 2).toFixed(2)} %`;
}

function truncateDecimal(value: number, decimals: number) {
  const factor = 10 ** decimals;
  return Math.trunc(value * factor) / factor;
}
