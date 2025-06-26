import logging

from backend.src.ir_pipeline.schema import LLMResponse, Terms
from backend.src.utils.langfuse import get_prompt
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


def create_query_expansion_chain(llm: BaseLanguageModel):
    prompt_template, langfuse_prompt = get_prompt("expand-query")
    output_parser = PydanticOutputParser(pydantic_object=Terms)
    config = RunnableConfig(
        run_name="expand-query", metadata={"langfuse_prompt": langfuse_prompt}
    )
    chain = prompt_template | llm | output_parser
    return chain.with_config(config)


def create_answer_generation_chain(
    llm: BaseLanguageModel, prompt_name: str = "generate-answer"
):
    prompt_template, langfuse_prompt = get_prompt(prompt_name)
    output_parser = PydanticOutputParser(pydantic_object=LLMResponse)
    config = RunnableConfig(
        run_name=prompt_name, metadata={"langfuse_prompt": langfuse_prompt}
    )
    chain = prompt_template | llm | output_parser
    return chain.with_config(config)
