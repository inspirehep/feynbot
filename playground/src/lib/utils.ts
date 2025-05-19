import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const getCitationsUrl = (paperId: string) => {
  return `https://inspirehep.net/literature?q=refersto%3Arecid%3A${paperId}`;
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
    return authors.join(", ");
  }
  return `${authors.slice(0, count).join(", ")} et al.`;
};
