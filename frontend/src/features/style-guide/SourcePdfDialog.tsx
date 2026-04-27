import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs, type TextContent } from "react-pdf";

import { Button } from "@/components/ui/button";
import { loadStyleGuidePdf } from "@/features/style-guide/styleGuidePdfStore";
import { cn } from "@/lib/utils";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

type SourcePdfPreviewProps = {
  className?: string;
  fileName: string;
  excerpt: string;
  loadPdf?: (fileName: string) => Promise<Blob | null>;
  pageStart: number | null;
  pageEnd: number | null;
};

export function SourcePdfPreview({
  className,
  fileName,
  excerpt,
  loadPdf = loadStyleGuidePdf,
  pageStart,
  pageEnd,
}: SourcePdfPreviewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [fileStatus, setFileStatus] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(Math.max(pageStart ?? 1, 1));
  const [pageWidth, setPageWidth] = useState<number>(720);
  const [highlightedItemIndexes, setHighlightedItemIndexes] = useState<Set<number>>(new Set());

  const initialPage = Math.max(pageStart ?? 1, 1);
  const lastRelevantPage = Math.max(pageEnd ?? initialPage, initialPage);
  const hasMultipleRelevantPages = lastRelevantPage > initialPage;
  const excerptText = excerpt.trim();

  useEffect(() => {
    setCurrentPage(initialPage);
    setHighlightedItemIndexes(new Set());
  }, [excerptText, initialPage]);

  useEffect(() => {
    let active = true;
    let localUrl: string | null = null;

    setFileStatus("loading");
    setNumPages(null);

    void loadPdf(fileName)
      .then((blob) => {
        if (!active) {
          return;
        }

        if (blob === null) {
          setBlobUrl(null);
          setFileStatus("missing");
          return;
        }

        localUrl = URL.createObjectURL(blob);
        setBlobUrl(localUrl);
        setFileStatus("ready");
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setBlobUrl(null);
        setFileStatus("error");
      });

    return () => {
      active = false;
      if (localUrl) {
        URL.revokeObjectURL(localUrl);
      }
    };
  }, [fileName, loadPdf]);

  useEffect(() => {
    if (containerRef.current === null) {
      return;
    }

    const updateWidth = () => {
      const nextWidth = Math.max((containerRef.current?.clientWidth ?? 760) - 32, 280);
      setPageWidth(Math.min(nextWidth, 960));
    };

    updateWidth();

    const observer = new ResizeObserver(updateWidth);
    observer.observe(containerRef.current);

    return () => observer.disconnect();
  }, []);

  const boundedCurrentPage = useMemo(() => {
    if (numPages === null) {
      return currentPage;
    }

    return Math.min(Math.max(currentPage, 1), numPages);
  }, [currentPage, numPages]);
  const pageRenderKey = useMemo(
    () => `${fileName}:${boundedCurrentPage}:${excerptText}`,
    [boundedCurrentPage, excerptText, fileName],
  );

  const focusHighlightedExcerpt = useCallback(() => {
    const container = containerRef.current;
    if (container === null) {
      return;
    }

    requestAnimationFrame(() => {
      const highlightedNode = container.querySelector("mark");
      if (!(highlightedNode instanceof HTMLElement)) {
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const highlightRect = highlightedNode.getBoundingClientRect();
      const targetTop =
        container.scrollTop + (highlightRect.top - containerRect.top) - container.clientHeight / 2 + highlightRect.height / 2;

      container.scrollTo({
        top: Math.max(targetTop, 0),
        behavior: "smooth",
      });
    });
  }, []);

  return (
    <div
      className={cn(
        "flex h-full min-h-0 flex-col overflow-hidden rounded-[1.25rem] border border-black/6 bg-[rgba(255,255,255,0.9)] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.03)]",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/5 px-4 py-2.5">
        <p className="text-sm text-[var(--color-muted)]">
          {hasMultipleRelevantPages ? `Pages ${initialPage} à ${lastRelevantPage}` : `Page ${initialPage}`}
        </p>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setCurrentPage((page) => Math.max(page - 1, 1))}
            disabled={fileStatus !== "ready" || boundedCurrentPage <= 1}
          >
            <ChevronLeft className="size-4" />
            Précédente
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() =>
              setCurrentPage((page) =>
                numPages === null ? page + 1 : Math.min(page + 1, numPages),
              )
            }
            disabled={fileStatus !== "ready" || (numPages !== null && boundedCurrentPage >= numPages)}
          >
            Suivante
            <ChevronRight className="size-4" />
          </Button>
        </div>
      </div>

      <div ref={containerRef} className="min-h-0 flex-1 overflow-auto bg-[#eef1eb] p-3">
        {fileStatus === "loading" ? (
          <div className="grid h-full place-items-center text-[var(--color-forest)]">
            <Loader2 className="size-8 animate-spin" aria-label="Chargement du PDF" />
          </div>
        ) : null}

        {fileStatus === "missing" ? <MissingPdfState fileName={fileName} /> : null}

        {fileStatus === "error" ? <ErrorPdfState /> : null}

        {fileStatus === "ready" && blobUrl !== null ? (
          <div className="mx-auto w-fit rounded-[1rem] bg-white p-3 shadow-[0_14px_34px_rgba(27,28,26,0.10)]">
            <Document
              file={blobUrl}
              loading={
                <div className="grid h-[18rem] w-[18rem] place-items-center text-[var(--color-forest)]">
                  <Loader2 className="size-7 animate-spin" aria-label="Chargement de la page" />
                </div>
              }
              onLoadSuccess={({ numPages: totalPages }) => {
                setNumPages(totalPages);
                setCurrentPage((page) => Math.min(Math.max(page, 1), totalPages));
              }}
            >
              <Page
                key={pageRenderKey}
                pageNumber={boundedCurrentPage}
                customTextRenderer={({ itemIndex, str }) => {
                  const safeText = escapeHtml(str);

                  return highlightedItemIndexes.has(itemIndex)
                    ? `<mark>${safeText}</mark>`
                    : safeText;
                }}
                onGetTextSuccess={(textContent) =>
                  setHighlightedItemIndexes(findMatchingItemIndexes(textContent, excerptText))
                }
                onRenderTextLayerSuccess={focusHighlightedExcerpt}
                renderAnnotationLayer
                renderTextLayer
                width={pageWidth}
              />
            </Document>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function findMatchingItemIndexes(textContent: TextContent, excerpt: string): Set<number> {
  const excerptCandidates = buildExcerptCandidates(excerpt);
  if (excerptCandidates.length === 0) {
    return new Set();
  }

  const itemRanges: Array<{ start: number; end: number; itemIndex: number }> = [];
  let combined = "";

  textContent.items.forEach((item, itemIndex) => {
    if (!("str" in item)) {
      return;
    }

    const itemText = normalizeSearchValue(item.str);
    if (!itemText) {
      return;
    }

    if (combined.length > 0) {
      combined += " ";
    }

    const start = combined.length;
    combined += itemText;
    itemRanges.push({ start, end: combined.length, itemIndex });
  });

  if (!combined) {
    return new Set();
  }

  for (const candidate of excerptCandidates) {
    const matchStart = combined.indexOf(candidate);
    if (matchStart === -1) {
      continue;
    }

    const matchEnd = matchStart + candidate.length;
    return new Set(
      itemRanges
        .filter((range) => range.end > matchStart && range.start < matchEnd)
        .map((range) => range.itemIndex),
    );
  }

  for (const candidate of excerptCandidates) {
    const compactMatch = findCompactMatchRange(combined, itemRanges, candidate);
    if (compactMatch !== null) {
      return new Set(
        itemRanges
          .filter((range) => range.end > compactMatch.start && range.start < compactMatch.end)
          .map((range) => range.itemIndex),
      );
    }
  }

  const fallbackMatches = excerptCandidates
    .map((candidate) => findApproximateMatchRange(combined, itemRanges, candidate))
    .filter((match): match is ApproximateMatchRange => match !== null)
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return (right.end - right.start) - (left.end - left.start);
    });

  if (fallbackMatches.length > 0) {
    const bestMatch = fallbackMatches[0];
    return new Set(
      itemRanges
        .filter((range) => range.end > bestMatch.start && range.start < bestMatch.end)
        .map((range) => range.itemIndex),
    );
  }

  return new Set();
}

function findCompactMatchRange(
  combined: string,
  itemRanges: Array<{ start: number; end: number; itemIndex: number }>,
  excerptCandidate: string,
): ApproximateMatchRange | null {
  const candidate = compactSearchValue(excerptCandidate);
  if (candidate.length < 3) {
    return null;
  }

  const combinedCompact = compactSearchValueWithIndexes(combined);
  const compactStart = combinedCompact.value.indexOf(candidate);
  if (compactStart === -1) {
    return null;
  }

  const compactEnd = compactStart + candidate.length - 1;
  const start = combinedCompact.indexes[compactStart];
  const end = combinedCompact.indexes[compactEnd];
  if (start === undefined || end === undefined) {
    return null;
  }

  const overlappingItems = itemRanges.filter((range) => range.end > start && range.start < end + 1);
  if (overlappingItems.length === 0) {
    return null;
  }

  return {
    start: overlappingItems[0].start,
    end: overlappingItems[overlappingItems.length - 1].end,
    score: candidate.length,
  };
}

function buildExcerptCandidates(excerpt: string): string[] {
  const normalizedExcerpt = normalizeSearchValue(excerpt);
  if (!normalizedExcerpt) {
    return [];
  }

  const candidates = [normalizedExcerpt];
  const segments = normalizedExcerpt
    .split("|")
    .map((segment) => segment.trim())
    .filter((segment) => segment.length >= 12);

  for (const segment of segments) {
    if (!candidates.includes(segment)) {
      candidates.push(segment);
    }
  }

  return candidates.sort((left, right) => right.length - left.length);
}

type ApproximateMatchRange = {
  start: number;
  end: number;
  score: number;
};

type SearchTokenRange = {
  token: string;
  start: number;
  end: number;
};

const META_TOKENS = new Set(["hard", "soft"]);
const SEARCH_STOPWORDS = new Set([
  "a",
  "au",
  "aux",
  "avec",
  "ce",
  "ces",
  "cette",
  "dans",
  "de",
  "des",
  "du",
  "en",
  "et",
  "est",
  "la",
  "le",
  "les",
  "ne",
  "ou",
  "par",
  "pas",
  "pour",
  "que",
  "qui",
  "sans",
  "se",
  "ses",
  "son",
  "sur",
  "une",
  "un",
]);

function findApproximateMatchRange(
  combined: string,
  itemRanges: Array<{ start: number; end: number; itemIndex: number }>,
  excerptCandidate: string,
): ApproximateMatchRange | null {
  const pageTokens = tokenizeNormalizedValue(combined).filter((token) =>
    isMeaningfulSearchToken(token.token),
  );
  const candidateTokens = tokenizeNormalizedValue(excerptCandidate)
    .map((token) => token.token)
    .filter(isMeaningfulSearchToken);

  if (pageTokens.length === 0 || candidateTokens.length === 0) {
    return null;
  }

  const bestRun = findLongestCommonTokenRun(pageTokens, candidateTokens);
  if (bestRun === null) {
    return null;
  }

  const minimumRunLength = Math.min(
    4,
    Math.max(2, Math.ceil(candidateTokens.length * 0.45)),
  );

  if (bestRun.length < minimumRunLength) {
    return null;
  }

  const ratio = bestRun.length / candidateTokens.length;
  if (ratio < 0.4) {
    return null;
  }

  const matchedCharLength = bestRun.end - bestRun.start;
  const minimumMatchedCharLength = candidateTokens.some((token) => /\d/.test(token)) ? 4 : 18;
  if (matchedCharLength < minimumMatchedCharLength) {
    return null;
  }

  const overlappingItems = itemRanges.filter(
    (range) => range.end > bestRun.start && range.start < bestRun.end,
  );
  if (overlappingItems.length === 0) {
    return null;
  }

  return {
    start: overlappingItems[0].start,
    end: overlappingItems[overlappingItems.length - 1].end,
    score: ratio * 100 + bestRun.length,
  };
}

function tokenizeNormalizedValue(value: string): SearchTokenRange[] {
  const matches = value.matchAll(/\S+/g);

  return Array.from(matches, (match) => ({
    token: match[0],
    start: match.index ?? 0,
    end: (match.index ?? 0) + match[0].length,
  }));
}

function isMeaningfulSearchToken(token: string): boolean {
  if (token === "|" || META_TOKENS.has(token) || SEARCH_STOPWORDS.has(token)) {
    return false;
  }

  return token.length >= 3 || token.includes("-") || /\d/.test(token);
}

function findLongestCommonTokenRun(
  pageTokens: SearchTokenRange[],
  candidateTokens: string[],
): { start: number; end: number; length: number } | null {
  const previousRow = new Array(candidateTokens.length + 1).fill(0);
  let bestLength = 0;
  let bestPageEndIndex = -1;

  for (let pageIndex = 1; pageIndex <= pageTokens.length; pageIndex += 1) {
    let previousDiagonal = 0;

    for (let candidateIndex = 1; candidateIndex <= candidateTokens.length; candidateIndex += 1) {
      const previousValue = previousRow[candidateIndex];

      if (pageTokens[pageIndex - 1]?.token === candidateTokens[candidateIndex - 1]) {
        previousRow[candidateIndex] = previousDiagonal + 1;
      } else {
        previousRow[candidateIndex] = 0;
      }

      if (previousRow[candidateIndex] > bestLength) {
        bestLength = previousRow[candidateIndex];
        bestPageEndIndex = pageIndex - 1;
      }

      previousDiagonal = previousValue;
    }
  }

  if (bestLength === 0 || bestPageEndIndex === -1) {
    return null;
  }

  const startToken = pageTokens[bestPageEndIndex - bestLength + 1];
  const endToken = pageTokens[bestPageEndIndex];

  if (startToken === undefined || endToken === undefined) {
    return null;
  }

  return {
    start: startToken.start,
    end: endToken.end,
    length: bestLength,
  };
}

function normalizeSearchValue(value: string): string {
  return value
    .normalize("NFD")
    .replace(/n\s*[·.-]\s*m/giu, "n m")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[Øø⌀]/gu, " diametre ")
    .toLowerCase()
    .replace(/(\p{Letter})(?=\p{Number})/gu, "$1 ")
    .replace(/(\p{Number})(?=\p{Letter})/gu, "$1 ")
    .replace(/[^\p{Letter}\p{Number}|-]+/gu, " ")
    .replace(/\s+/g, " ")
    .replace(/\bveri fi er\b/g, "verifier")
    .replace(/\bfi nie\b/g, "finie")
    .trim();
}

function compactSearchValue(value: string): string {
  return value.replace(/[^\p{Letter}\p{Number}]+/gu, "");
}

function compactSearchValueWithIndexes(value: string): { value: string; indexes: number[] } {
  let compact = "";
  const indexes: number[] = [];

  Array.from(value).forEach((character, index) => {
    if (!/[\p{Letter}\p{Number}]/u.test(character)) {
      return;
    }

    compact += character;
    indexes.push(index);
  });

  return { value: compact, indexes };
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function MissingPdfState({ fileName }: { fileName: string }) {
  return (
    <div className="grid h-full min-h-[24rem] place-items-center px-6 text-center">
      <div className="max-w-md">
        <p className="font-serif text-2xl font-semibold tracking-[-0.04em] text-[var(--color-ink)]">
          PDF indisponible dans ce navigateur
        </p>
        <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
          Le document “{fileName}” n’est plus présent localement. Réimportez le PDF depuis cet appareil
          pour réactiver la consultation de la source.
        </p>
      </div>
    </div>
  );
}

function ErrorPdfState() {
  return (
    <div className="grid h-full min-h-[24rem] place-items-center px-6 text-center">
      <div className="max-w-md">
        <p className="font-serif text-2xl font-semibold tracking-[-0.04em] text-[var(--color-ink)]">
          Impossible d’afficher le PDF
        </p>
        <p className="mt-3 text-sm leading-6 text-[var(--color-muted)]">
          Le document source n’a pas pu être relu correctement dans cette session.
        </p>
      </div>
    </div>
  );
}
