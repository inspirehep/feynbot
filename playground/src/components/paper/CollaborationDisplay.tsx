import { getInspireBaseUrl } from "@/lib/utils";

import { Button } from "@/components/ui/button";

export function CollaborationDisplay({
  collaborations,
}: {
  collaborations: string[];
}) {
  return (
    <span>
      {collaborations.map((collaboration, index) => (
        <span key={collaboration}>
          <Button variant="link" size="sm" className="h-4 p-0" asChild>
            <a
              href={`${getInspireBaseUrl()}/literature?q=collaboration:${collaboration}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {collaboration}
            </a>
          </Button>
          {index < collaborations.length - 2
            ? ", "
            : index === collaborations.length - 2
              ? " and "
              : ""}
        </span>
      ))}
      {` Collaboration${collaborations.length > 1 ? "s" : ""}`}
    </span>
  );
}
