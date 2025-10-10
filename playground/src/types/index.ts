export type BoundingBox = {
  page_no: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
  coord_origin: string;
};

export type LLMCitation = {
  doc_id: number;
  control_number: number;
  snippet: string;
  bboxes: BoundingBox[];
};

export type LLMResponse = {
  brief_answer: string;
  long_answer: string;
  citations: LLMCitation[];
  trace_id: string;
};

export type ChatMessage = {
  type: "user" | "assistant";
  content: string;
};

export type QueryRequest = {
  query: string;
  control_number?: number;
  history?: ChatMessage[];
};

export type PaperResponse = {
  long_answer: string;
  trace_id: string;
};

export type PaperDetails = {
  id: number;
  title: string;
  authors: string[];
  collaborations: string[];
  year?: number;
  journal: string;
  affiliation: string;
  abstract: string;
  citation_count: number;
  arxiv_id?: string;
  doi?: string;
  document_type?: string;
  document_url?: string;
};
