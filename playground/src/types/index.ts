import { convertInspirePaperToAppFormat } from "@/lib/api";

export type LLMCitation = {
  doc_id: number;
  control_number: number;
  snippet: string;
};

export type LLMResponse = {
  brief_answer: string;
  long_answer: string;
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
