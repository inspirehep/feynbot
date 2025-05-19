import { convertInspirePaperToAppFormat } from "@/lib/api";

export type LLMCitation = {
  paperId: number;
  snippet: string;
  display: number;
};

export type LLMResponse = {
  brief: string;
  response: string;
  citations: Record<string, LLMCitation>;
};

// TODO: define proper type in api.ts
export type PaperDetails = ReturnType<typeof convertInspirePaperToAppFormat>;

export type FormattedCitation = {
  id: number;
  display: number;
  paper: PaperDetails;
  snippets: string[];
};
