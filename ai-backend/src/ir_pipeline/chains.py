from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate

from src.ir_pipeline.llm_response import LLMResponse


def create_query_expansion_chain(llm: BaseLanguageModel, system_prompt: str):
    prompt_template = PromptTemplate.from_template(system_prompt)
    return prompt_template | llm | StrOutputParser()


def create_answer_generation_chain(llm: BaseLanguageModel, system_prompt: str):
    prompt_template = PromptTemplate.from_template(system_prompt)
    output_parser = PydanticOutputParser(pydantic_object=LLMResponse)
    return prompt_template | llm | output_parser
