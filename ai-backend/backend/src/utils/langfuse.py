import logging

from langchain_core.prompts import PromptTemplate
from langfuse import Langfuse
from langfuse.api.resources.commons.errors.not_found_error import NotFoundError

logger = logging.getLogger(__name__)

langfuse = Langfuse()


# Locally langfuse.environment should be unset (None)
def get_prompt(prompt_name: str):
    def fetch_prompt(label: str = None):
        return langfuse.get_prompt(
            prompt_name,
            cache_ttl_seconds=0 if langfuse.environment is None else None,
            label=label,
        )

    try:
        label = "latest" if langfuse.environment is None else langfuse.environment
        langfuse_prompt = fetch_prompt(label=label)
    except NotFoundError:
        logger.warning(
            f"Prompt '{prompt_name}' or label '{label}' "
            f"not found in Langfuse, trying label 'production'"
        )
        langfuse_prompt = fetch_prompt()

    prompt_template = PromptTemplate.from_template(
        langfuse_prompt.get_langchain_prompt(),
        metadata={"langfuse_prompt": langfuse_prompt},
    )
    return prompt_template, langfuse_prompt
