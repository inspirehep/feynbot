import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

import { PaperDetails } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const getInspireBaseUrl = (() => {
  let cached: string | null = null;

  return (): string => {
    if (cached === null) {
      cached = window.location.hostname.includes("inspirehep.net")
        ? "https://inspirehep.net"
        : "https://inspirebeta.net";
    }
    return cached;
  };
})();

export const getInspireAiUrl = () =>
  `${import.meta.env.DEV ? "" : getInspireBaseUrl()}/ai`;

export const getCitationsUrl = (paperId: string) => {
  return `${getInspireBaseUrl()}/literature?q=refersto%3Arecid%3A${paperId}`;
};

export const formatAuthors = (
  authors: string[],
  collaborations: string[],
  count: number = 3,
) => {
  if (collaborations && collaborations.length > 0) {
    return (
      collaborations.join(", ") +
      ` Collaboration${collaborations.length > 1 ? "s" : ""}`
    );
  }

  if (authors.length <= count) {
    return authors.join("; ");
  }
  return `${authors.slice(0, count).join("; ")} et al.`;
};

export const getPaperUrl = (paper: PaperDetails) =>
  paper.arxiv_id &&
  (paper.document_url ||
    `https://browse-export.arxiv.org/pdf/${paper.arxiv_id}`);

export const getPDFWithCache = async (
  pdfUrl: string,
  getCachedPDF: (url: string) => string | null,
  cachePDF: (url: string, blob: string) => void,
  getPendingRequest: (url: string) => Promise<string | null> | null,
  setPendingRequest: (url: string, promise: Promise<string | null>) => void,
): Promise<string | null> => {
  const cached = getCachedPDF(pdfUrl);
  if (cached) {
    return cached;
  }

  const pending = getPendingRequest(pdfUrl);
  if (pending) {
    const result = await pending;
    return getCachedPDF(pdfUrl) || result;
  }

  const fetchPromise = (async () => {
    try {
      const response = await fetch(pdfUrl);
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      return blobUrl;
    } catch {
      return null;
    }
  })();

  setPendingRequest(pdfUrl, fetchPromise);

  const blobUrl = await fetchPromise;
  if (blobUrl) {
    cachePDF(pdfUrl, blobUrl);
  }

  return blobUrl;
};
