const pdfCache = new Map<string, string>();
const pendingRequests = new Map<string, Promise<string | null>>();

export const usePDFCache = () => {
  const getCachedPDF = (url: string): string | null => {
    return pdfCache.get(url) || null;
  };

  const cachePDF = (url: string, blob: string) => {
    pdfCache.set(url, blob);
    pendingRequests.delete(url);
  };

  const getPendingRequest = (url: string): Promise<string | null> | null => {
    return pendingRequests.get(url) || null;
  };

  const setPendingRequest = (url: string, promise: Promise<string | null>) => {
    pendingRequests.set(url, promise);
  };

  const clearCache = () => {
    pdfCache.forEach((blobUrl) => {
      URL.revokeObjectURL(blobUrl);
    });
    pdfCache.clear();
    pendingRequests.clear();
  };

  return {
    getCachedPDF,
    cachePDF,
    getPendingRequest,
    setPendingRequest,
    clearCache,
  };
};
