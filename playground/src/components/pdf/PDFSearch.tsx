import {
  SearchResult,
  calculateHighlightRects,
  usePdf,
  usePdfJump,
  useSearch,
} from "@anaralabs/lector";
import { Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

import { BoundingBox } from "@/types";

const PDFSearch = ({ activeBboxes }: { activeBboxes?: BoundingBox[] }) => {
  const [searchText, setSearchText] = useState("");
  const [debouncedText, setDebouncedText] = useState("");
  const { jumpToHighlightRects } = usePdfJump();
  const { searchResults: results, search } = useSearch();
  const getPdfPageProxy = usePdf((state) => state.getPdfPageProxy);

  // Convert bounding boxes using PDF.js native coordinate transformation
  // as Docling uses a different coordinate system
  const highlightBboxes = useCallback(async () => {
    if (!activeBboxes || activeBboxes.length === 0) return;

    const rects = await Promise.all(
      activeBboxes.map(async (bbox) => {
        const pageProxy = getPdfPageProxy(bbox.page_no);
        if (!pageProxy) return null;

        const viewport = pageProxy.getViewport({ scale: 1 });
        let pdfRect: number[];

        if (bbox.coord_origin === "BOTTOMLEFT") {
          pdfRect = [bbox.left, bbox.bottom, bbox.right, bbox.top];
        } else {
          pdfRect = [
            bbox.left,
            viewport.height - bbox.bottom,
            bbox.right,
            viewport.height - bbox.top,
          ];
        }

        const viewportRect = viewport.convertToViewportRectangle(pdfRect);

        return {
          pageNumber: bbox.page_no,
          left: viewportRect[0],
          top: Math.min(viewportRect[1], viewportRect[3]),
          right: viewportRect[2],
          bottom: Math.max(viewportRect[1], viewportRect[3]),
          width: Math.abs(viewportRect[2] - viewportRect[0]),
          height: Math.abs(viewportRect[3] - viewportRect[1]),
        };
      }),
    );

    const validRects = rects.filter(
      (rect): rect is NonNullable<typeof rect> => rect !== null,
    );

    if (validRects.length > 0) {
      jumpToHighlightRects(validRects, "pixels");
    }
  }, [activeBboxes, jumpToHighlightRects, getPdfPageProxy]);

  useEffect(() => {
    if (activeBboxes && activeBboxes.length > 0) {
      highlightBboxes();
    }
  }, [activeBboxes, highlightBboxes]);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedText(searchText);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchText]);

  // Perform search when debounced text changes
  useEffect(() => {
    if (debouncedText) {
      search(debouncedText, { limit: 5 });
    }
  }, [debouncedText, search]);

  const onClick = async (result: SearchResult) => {
    const pageProxy = getPdfPageProxy(result.pageNumber);
    const rects = await calculateHighlightRects(pageProxy, {
      pageNumber: result.pageNumber,
      text: result.text,
      matchIndex: result.matchIndex,
      searchText: debouncedText,
    });
    jumpToHighlightRects(rects, "pixels");
  };

  return (
    <div className="absolute top-4 right-4 z-50">
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" size="icon" className="rounded-full">
            <Search className="h-5 w-5" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64" align="end">
          <Input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search in PDF..."
            className="mb-4"
          />
          {debouncedText && results.fuzzyMatches.length > 0 ? (
            <div className="max-h-[400px] space-y-2 overflow-y-auto">
              {results.fuzzyMatches.map((result, index) => (
                <Card
                  key={`${result.pageNumber}-${index}`}
                  className="hover:border-primary cursor-pointer p-3"
                  onClick={() => onClick(result)}
                >
                  <div className="flex w-full flex-col gap-2">
                    <p className="text-sm">...{result.text}...</p>
                    <span className="text-muted-foreground flex justify-between text-xs">
                      <span>{Math.round(result.score * 100)}% match</span>
                      <span>Page {result.pageNumber}</span>
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            debouncedText && (
              <p className="text-muted-foreground text-center text-sm">
                No search results found
              </p>
            )
          )}
          {activeBboxes && activeBboxes.length > 0 && (
            <div className="mt-4 rounded-md">
              <p className="text-muted-foreground text-center text-sm italic">
                Highlighting {activeBboxes.length} citation region
                {activeBboxes.length > 1 ? "s" : ""}
              </p>
            </div>
          )}
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default PDFSearch;
