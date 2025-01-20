Combines INSPIRE HEP (High Energy Physics) database searches with AI-powered responses.

## Search Enhancement:

1. Takes a user query and uses GPT-4 to expand it into multiple relevant search variations
2. Searches the INSPIRE HEP database using these expanded queries

Example: "how far are black holes?" gets expanded into multiple variations like "distance from black holes", "remoteness of black holes", etc.

## Result Processing:

1. Retrieves academic papers from INSPIRE HEP
2. Formats the paper metadata including authors, year, title, and DOI
3. Creates a context from the papers' titles and abstracts

## AI Answer Generation:

1. Uses GPT-4 to generate a comprehensive answer based on the search results
2. Citations are included in the format [1], [2], etc.
3. Cleans up and renumbers the references to match only the cited papers
4. Provides a summary at the end of each answer
