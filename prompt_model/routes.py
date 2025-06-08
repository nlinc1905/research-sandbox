import typing as t

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.postgres import postgres_session_init

from .crud import (
    delete_model_prompts,
    delete_prompt,
    get_all_prompts,
    get_latest_prompt,
    get_prompt,
    get_prompt_versions,
    new_prompt_version,
)
from .models import ListPromptsResponse, DeleteResponse, PromptCreateRequest, PromptDeleteRequest, PromptOutResponse

router = APIRouter(prefix="/prompt", tags=["Prompts"])


@router.get("/prompts")
async def get_prompts_list(
    db_session: Session = Depends(postgres_session_init),
) -> ListPromptsResponse:
    """
    Get the latest version of all prompts by name and model name.
    """
    prompts = get_all_prompts(db_session)
    response = ListPromptsResponse(
        prompts=[PromptOutResponse(**prompt.__dict__) for prompt in prompts]
    )
    return response


@router.post("")
async def create_new_prompt_version(
    payload: PromptCreateRequest,
    db_session: Session = Depends(postgres_session_init),
) -> PromptOutResponse:
    """
    Update an existing prompt by creating a new version, or create a new prompt
    if there are no existing prompt versions for the given name and model_name.
    """
    new_prompt = new_prompt_version(db_session, payload)
    response = PromptOutResponse(
        id=new_prompt.id,
        name=new_prompt.name,
        prompt=new_prompt.prompt,
        model_name=new_prompt.model_name,
        version=new_prompt.version,
        last_updated=new_prompt.last_updated,
    )
    return response


@router.get("/versions/{prompt_name}/{model_name}")
async def get_prompt_versions_by_name(
    prompt_name: str,
    model_name: str,
    db_session: Session = Depends(postgres_session_init),
) -> t.List[PromptOutResponse]:
    """
    Get all versions of a prompt by name and model name.
    """
    prompts = get_prompt_versions(db_session, prompt_name, model_name)
    if not prompts:
        raise HTTPException(status_code=404, detail=f"No prompts {prompt_name} found for model {model_name}.")
    response = [PromptOutResponse(**prompt.__dict__) for prompt in prompts]
    return response


@router.get("/latest/{prompt_name}/{model_name}")
async def get_latest_prompt_by_name(
    prompt_name: str,
    model_name: str,
    db_session: Session = Depends(postgres_session_init),
) -> PromptOutResponse:
    """
    Get the latest version of a prompt by name and model name.
    """
    prompt = get_latest_prompt(db_session, prompt_name, model_name)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    response = PromptOutResponse(**prompt.__dict__)
    return response


@router.get("/{prompt_name}/{model_name}/{version}")
async def get_prompt_by_name_model_version(
    prompt_name: str,
    model_name: str,
    version: int,
    db_session: Session = Depends(postgres_session_init),
) -> PromptOutResponse:
    """
    Get a prompt by name, model name, and version.
    """
    prompt = get_prompt(db_session, prompt_name, model_name, version)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    response = PromptOutResponse(**prompt.__dict__)
    return response


@router.delete("")
async def delete_prompt_version(
    payload: PromptDeleteRequest,
    db_session: Session = Depends(postgres_session_init),
) -> DeleteResponse:
    """
    Delete a prompt by name, model name, and version.
    """
    deleted = delete_prompt(db_session, payload)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prompt not found.")
    response = DeleteResponse(message={"deleted": True})
    return response


@router.delete("/model/{model_name}", include_in_schema=False)
async def delete_model_prompts_by_name(
    model_name: str,
    db_session: Session = Depends(postgres_session_init),
) -> DeleteResponse:
    """
    Delete all prompts for a specific model.
    """
    deleted = delete_model_prompts(db_session, model_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="No prompts found for this model.")
    response = DeleteResponse(message={"deleted": True})
    return response
