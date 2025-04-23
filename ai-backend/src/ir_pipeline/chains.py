from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langfuse import Langfuse

from src.ir_pipeline.schemas import LLMResponse, Terms

langfuse = Langfuse()


def _get_prompt(prompt_name: str):
    langfuse_prompt = langfuse.get_prompt(prompt_name)  # default cache_ttl_seconds=0
    return PromptTemplate.from_template(
        langfuse_prompt.get_langchain_prompt(),
        metadata={"langfuse_prompt": langfuse_prompt},
    )


def create_query_expansion_chain(llm: BaseLanguageModel):
    output_parser = PydanticOutputParser(pydantic_object=Terms)
    config = RunnableConfig(run_name="expand_query")
    get_prompt = RunnableLambda(lambda _: _get_prompt("expand-query"))
    chain = get_prompt | llm | output_parser
    return chain.with_config(config)


def create_answer_generation_chain(llm: BaseLanguageModel):
    output_parser = PydanticOutputParser(pydantic_object=LLMResponse)
    config = RunnableConfig(run_name="generate_answer")
    get_prompt = RunnableLambda(lambda _: _get_prompt("generate-answer"))
    chain = get_prompt | llm | output_parser
    return chain.with_config(config)
