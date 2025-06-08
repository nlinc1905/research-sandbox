import typing as t
import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from core.postgres import Base

# ----------
# Pydantic models for API and database validation


class PromptCreateRequest(BaseModel):
    """
    Pydantic model for creating a new prompt.
    """

    name: str = Field(
        ..., 
        description="Name of the prompt. Prompts beginning with '_' are protected and used for the chat feature."
    )
    prompt: str = Field(
        ..., 
        description="""
        The prompt text. This field is heavily validated to ensure users cannot break prompts, and therefore 
        break the application (if a prompt used for generation breaks, all generation fails until the prompt 
        is reverted to an older version). If the prompt has variables, they must be formatted as follows:
        - Single curly brackets: {var_name} must contain a valid Python variable name.
        - Double curly brackets: {{ var_name }} must have exactly one space on each side of the variable name.
        - Prompt names beginning with "_" are protected and use single curly brackets only.
        """
    )
    model_name: str = Field(..., description="The name of the LLM that the prompt was written for.")

    @field_validator("prompt")
    def validate_prompt_format(cls, v: str) -> str:
        """
        Validate that the prompt string is correctly formatted with balanced brackets and valid variable names.
        This includes:
        - Double curly brackets: {{ var }} must have exactly one space on each side of the variable name.
        - Single curly brackets: {var} must be a valid variable name.
        - Ensure all brackets are balanced.

        :param v: The prompt string to validate.

        :return: The validated prompt string.

        :raises ValueError: If the prompt string does not meet the validation criteria.
        """
        # Validate double curly brackets: {{ var_name }}
        for match in re.finditer(r"{{(.*?)}}", v):
            content = match.group(1)
            # Must have exactly one space on each side
            if not re.match(r"^ [a-zA-Z_][a-zA-Z0-9_]* $", content):
                # Note that in f-strings, {{ escapes to { and }} escapes to }
                like_this = " var_name "
                raise ValueError(
                    f"Invalid variable format in double brackets: '{{{{{content}}}}}'. "
                    f"It should look '{{{{{like_this}}}}}'"
                )

        # Validate single curly brackets: {var_name}
        for match in re.finditer(r"(?<!{){([^{}]+)}(?!})", v):
            content = match.group(1)
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", content):
                # Note that in f-strings, {{ escapes to { and }} escapes to }
                like_this = "like_this"
                raise ValueError(
                    f"Invalid variable format in single brackets: '{{{content}}}'. "
                    f"It should look '{{{like_this}}}'"
                )

        # Ensure all brackets are balanced (simple stack)
        def check_bracket_balance(pattern: str, open_sym: str, close_sym: str, label: str) -> None:
            """
            Check that the brackets in the prompt are balanced.

            :param pattern: The regex pattern to match the brackets.
            :param open_sym: The opening symbol (e.g., '{{' or '{').
            :param close_sym: The closing symbol (e.g., '}}' or '}').
            :param label: A label for the type of brackets being checked (for error messages).
            """
            stack = []
            for match in re.finditer(pattern, v):
                token = match.group()
                if token == open_sym:
                    stack.append(open_sym)
                elif token == close_sym:
                    if not stack:
                        raise ValueError(f"Unmatched closing {label.split('/')[1]} in prompt.")
                    stack.pop()
            if stack:
                raise ValueError(f"Unmatched opening {label.split('/')[0]} in prompt.")

        check_bracket_balance(pattern=r"{{|}}", open_sym="{{", close_sym="}}", label="'{{' / '}}'")
        check_bracket_balance(pattern=r"{|}", open_sym="{", close_sym="}", label="'{' / '}'")

        return v

    @model_validator(mode="after")
    def validate_name_and_prompt(cls, values: dict) -> dict:
        """
        Validate that the prompt name and prompt content are compatible.
        If the name starts with '_', the prompt must not use double curly braces '{{ }}'.
        """
        name = values.name
        prompt = values.prompt

        # Check if the name starts with '_' and if the prompt contains double curly braces
        if name and name.startswith("_"):
            if "{{" in prompt or "}}" in prompt:
                raise ValueError("Prompts with names starting with '_' may not use double curly braces '{{ }}'. Use only single curly brackets '{ }'.")

        if name and name.startswith("_"):
            query_str = "query_str"
            context_str = ["context_str", "context_msg"]
            # Ensure the prompt contains the query
            if query_str not in prompt:
                raise ValueError(
                    f"Prompts with names starting with '_' must contain the variable "
                    f"'{query_str}' in single curly brackets in the prompt."
                )
            # Ensure the prompt contains only 1 of the context strings
            if not any(context in prompt for context in context_str):
                raise ValueError(
                    f"Prompts with names starting with '_' must contain one of the following "
                    f"variables in single curly brackets in the prompt: {context_str}"
                )
        return values


class PromptOutResponse(BaseModel):
    """
    Pydantic model for the outputting prompt data.
    """

    id: int = Field(..., description="Unique identifier for the prompt in the database.")
    name: str = Field(..., description="Name of the prompt.")
    prompt: str = Field(..., description="The prompt text.")
    model_name: str = Field(..., description="The name of the LLM that the prompt was written for.")
    version: int = Field(..., description="The version number of the prompt for a specific model.")
    last_updated: datetime = Field(..., description="Timestamp when the prompt version was last updated.")

    class ConfigDict:
        from_attributes = True


class ListPromptsResponse(BaseModel):
    """
    Pydantic model for the response containing a list of prompts.
    """
    prompts: t.List[PromptOutResponse] = Field(
        default_factory=list, description="List of prompts with their latest versions."
    )


class PromptDeleteRequest(BaseModel):
    """
    Pydantic model for deleting a prompt.
    """

    name: str = Field(..., description="Name of the prompt.")
    model_name: str = Field(..., description="The name of the LLM that the prompt was written for.")
    version: int = Field(..., description="The version number of the prompt for a specific model.")


class DeleteResponse(BaseModel):
    """
    Pydantic model for the response of a delete operation.
    """

    message: t.Dict[str, bool] = Field(
        default={"deleted": True}, description="Indicates whether the prompt was successfully deleted."
    )


# ----------
# SQLAlchemy models


class Prompt(Base):
    """
    SQLAlchemy model for the Prompt table.
    """

    __tablename__ = "prompts"
    __table_args__ = (UniqueConstraint("name", "model_name", "version", name="uq_prompt_name_model_version"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    model_name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
