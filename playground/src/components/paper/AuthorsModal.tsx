import { Users } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface AuthorsModalProps {
  authors: string[];
  collaborations?: string[];
}

export function AuthorsModal({
  authors,
  collaborations = [],
}: AuthorsModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const filteredAuthors = authors.filter((author) =>
    author.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  return (
    <Popover
      open={isOpen}
      onOpenChange={(open) => {
        setIsOpen(open);
        if (!open) {
          setSearchTerm("");
        }
      }}
    >
      <PopoverTrigger asChild>
        <Button
          variant="link"
          size="sm"
          className="text-foreground h-4 px-2 align-middle text-xs"
        >
          <Users />
          <span>{authors.length} authors</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="flex max-h-[80vh] max-w-2xl flex-col overflow-hidden p-4">
        <div className="text-sm font-medium">
          {collaborations.length > 0
            ? `${collaborations.join(", ")} Collaboration`
            : "Authors"}
        </div>
        <p className="text-muted-foreground text-sm">
          {authors.length} authors contributed to this paper
        </p>

        <div className="my-4">
          <Input
            placeholder="Search authors..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />
        </div>

        <div className="flex-1 overflow-y-auto pr-2">
          <ul className="space-y-1">
            {filteredAuthors.map((author, index) => (
              <li
                key={index}
                className="hover:bg-muted rounded-md px-2 py-1 text-sm"
              >
                {author}
              </li>
            ))}
          </ul>
          {filteredAuthors.length === 0 && (
            <p className="text-muted-foreground py-4 text-center text-sm">
              No authors found matching your search
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
