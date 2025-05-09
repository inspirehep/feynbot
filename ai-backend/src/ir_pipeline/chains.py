import logging

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langfuse import Langfuse
from langfuse.api.resources.commons.errors.not_found_error import NotFoundError

from src.ir_pipeline.schemas import LLMResponse, Terms

logger = logging.getLogger(__name__)

langfuse = Langfuse()


def _get_prompt(prompt_name: str):
    def fetch_prompt(label: str = None):
        return langfuse.get_prompt(
            prompt_name,
            cache_ttl_seconds=0 if langfuse.environment == "local" else None,
            label=label,
        )

    try:
        langfuse_prompt = fetch_prompt(label=langfuse.environment)
    except NotFoundError:
        logger.warning(
            f"Prompt '{prompt_name}' or label '{langfuse.environment}' "
            f"not found in Langfuse, trying label 'production'"
        )
        langfuse_prompt = fetch_prompt()

    prompt_template = PromptTemplate.from_template(
        langfuse_prompt.get_langchain_prompt(),
        metadata={"langfuse_prompt": langfuse_prompt},
    )
    return prompt_template, langfuse_prompt


def create_query_expansion_chain(llm: BaseLanguageModel):
    prompt_template, langfuse_prompt = _get_prompt("expand-query")
    output_parser = PydanticOutputParser(pydantic_object=Terms)
    config = RunnableConfig(
        run_name="expand-query", metadata={"langfuse_prompt": langfuse_prompt}
    )
    chain = prompt_template | llm | output_parser
    return chain.with_config(config)


def create_answer_generation_chain(
    llm: BaseLanguageModel, prompt_name: str = "generate-answer"
):
    prompt_template, langfuse_prompt = _get_prompt(prompt_name)
    output_parser = PydanticOutputParser(pydantic_object=LLMResponse)
    config = RunnableConfig(
        run_name=prompt_name, metadata={"langfuse_prompt": langfuse_prompt}
    )
    chain = prompt_template | llm | output_parser
    return chain.with_config(config)
