import {
  SearchResult,
  calculateHighlightRects,
  usePdf,
  usePdfJump,
  useSearch,
} from "@anaralabs/lector";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const PDFSearch = ({ highlight }: { highlight?: string }) => {
  const [searchText, setSearchText] = useState("");
  const [debouncedText, setDebouncedText] = useState("");
  const { jumpToHighlightRects } = usePdfJump();
  const { searchResults: results, search } = useSearch();
  const getPdfPageProxy = usePdf((state) => state.getPdfPageProxy);

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

  useEffect(() => {
    if (highlight) {
      setSearchText(highlight);
      setDebouncedText(highlight);
      search(highlight, { limit: 1 });
    }
  }, [highlight, search]);

  useEffect(() => {
    if (highlight && results.fuzzyMatches.length > 0) {
      onClick(results.fuzzyMatches[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlight, results.fuzzyMatches.length]);

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
            <p className="text-muted-foreground text-center text-sm">
              No results found
            </p>
          )}
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default PDFSearch;
