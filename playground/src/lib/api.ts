/**
 * Service for interacting with the INSPIRE HEP API
 */

const API_BASE_URL = "https://inspirehep.net/api";

export interface InspireSearchParams {
  q?: string;
  size?: number;
  page?: number;
  sort?: "mostrecent" | "mostcited";
  fields?: string[];
}

export interface InspirePaper {
  id: string;
  metadata: {
    titles: Array<{
      title: string;
    }>;
    authors: InspireAuthor[];
    collaborations?: Array<{
      value: string;
    }>;
    abstracts?: Array<{
      value: string;
      source?: string;
    }>;
    publication_info?: Array<{
      journal_title?: string;
      journal_volume?: string;
      journal_record?: string;
      year?: number;
      artid?: string;
      page_start?: string;
      page_end?: string;
    }>;
    citation_count?: number;
    citation_count_without_self_citations?: number;
    earliest_date?: string;
    arxiv_eprints?: Array<{
      value: string;
      categories: string[];
    }>;
    dois?: Array<{
      value: string;
    }>;
    document_type?: string[];
  };
  created: string;
  updated: string;
}

export interface InspireAuthor {
  full_name: string;
  affiliations?: Array<{
    value: string;
    record?: {
      $ref: string;
    };
  }>;
}

export interface InspireSearchResponse {
  hits: {
    hits: InspirePaper[];
    total: number;
  };
  links: {
    self: string;
    next?: string;
  };
}

/**
 * Search for papers in the INSPIRE HEP database
 */
export async function searchPapers(
  params: InspireSearchParams,
): Promise<InspireSearchResponse> {
  const queryParams = new URLSearchParams();

  if (params.q) {
    queryParams.append("q", params.q);
  }

  if (params.size) {
    queryParams.append("size", params.size.toString());
  }

  if (params.page) {
    queryParams.append("page", params.page.toString());
  }

  if (params.sort) {
    queryParams.append("sort", params.sort);
  }

  if (params.fields && params.fields.length > 0) {
    queryParams.append("fields", params.fields.join(","));
  }

  const url = `${API_BASE_URL}/literature?${queryParams.toString()}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching papers from INSPIRE:", error);
    throw error;
  }
}

/**
 * Get a specific paper by ID
 */
export async function getPaperById(id: string): Promise<InspirePaper> {
  const url = `${API_BASE_URL}/literature/${id}`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`API request failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error fetching paper ${id} from INSPIRE:`, error);
    throw error;
  }
}

/**
 * Convert an INSPIRE paper to our application's paper format
 */
export function convertInspirePaperToAppFormat(
  inspirePaper: InspirePaper,
  highlight?: string,
) {
  const metadata = inspirePaper.metadata;

  return {
    id: inspirePaper.id,
    title: metadata.titles[0]?.title || "Untitled",
    authors: metadata.authors.map((author) => author.full_name),
    collaborations:
      metadata.collaborations?.map((collab) => collab.value) || [],
    year:
      metadata.publication_info?.[0]?.year ||
      (metadata.earliest_date
        ? new Date(metadata.earliest_date).getFullYear()
        : undefined),
    journal:
      metadata.publication_info?.[0]?.journal_title ||
      (metadata.arxiv_eprints?.[0]
        ? `arXiv:${metadata.arxiv_eprints[0].value}`
        : "Unknown"),
    affiliation: metadata.authors[0]?.affiliations?.[0]?.value || "",
    abstract: metadata.abstracts?.[0]?.value || "No abstract available",
    highlight: highlight,
    citation_count: metadata.citation_count || 0,
    arxiv_id: metadata.arxiv_eprints?.[0]?.value,
    doi: metadata.dois?.[0]?.value,
    document_type: metadata.document_type?.[0] || "article",
  };
}

/**
 * Get random papers for initial display
 */
// export async function getRandomPapers(count = 4): Promise<any[]> {
//   // Get some recent papers with high citation counts
//   const params: InspireSearchParams = {
//     q: "topcite 100+",
//     sort: "mostrecent",
//     size: count,
//     fields: [
//       "titles",
//       "authors.full_name",
//       "authors.affiliations.value",
//       "collaborations",
//       "abstracts",
//       "publication_info",
//       "citation_count",
//       "earliest_date",
//       "arxiv_eprints",
//       "dois",
//       "document_type",
//     ],
//   };

//   try {
//     const response = await searchPapers(params);
//     return response.hits.hits.map(convertInspirePaperToAppFormat);
//   } catch (error) {
//     console.error("Error fetching random papers:", error);
//     return [];
//   }
// }
