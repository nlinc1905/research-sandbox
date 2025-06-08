import typing as t

from .models import Prompt, PromptCreateRequest, PromptDeleteRequest


def get_all_prompts(db_session) -> t.List[Prompt]:
    """
    Get the latest version of all prompts by name and model name.
    """
    return (
        db_session.query(Prompt)
        .order_by(Prompt.name, Prompt.model_name, Prompt.version.desc())
        .distinct(Prompt.name, Prompt.model_name)
        .all()
    )


def get_prompt(db_session, name: str, model_name: str, version: int) -> Prompt:
    """
    Get a prompt by name, model name, and version.
    """
    return (
        db_session.query(Prompt)
        .filter(
            Prompt.name == name,
            Prompt.model_name == model_name,
            Prompt.version == version,
        )
        .first()
    )


def get_latest_prompt(db_session, name: str, model_name: str) -> Prompt:
    """
    Get the latest version of a prompt by name and model name.
    """
    return (
        db_session.query(Prompt)
        .filter(
            Prompt.name == name,
            Prompt.model_name == model_name,
        )
        .order_by(Prompt.version.desc())
        .first()
    )


def get_prompt_versions(db_session, name: str, model_name: str) -> t.List[Prompt]:
    """
    Get all versions of a prompt by name and model name.
    """
    return (
        db_session.query(Prompt)
        .filter(
            Prompt.name == name,
            Prompt.model_name == model_name,
        )
        .order_by(Prompt.version.desc())
        .all()
    )


def new_prompt_version(db_session, prompt: PromptCreateRequest) -> Prompt:
    """
    Update an existing prompt by creating a new version, or create a new prompt
    if there are no existing prompt versions for the given name and model_name.
    """
    # Get the latest version of the prompt, if it exists
    latest_prompt = get_latest_prompt(db_session, prompt.name, prompt.model_name)
    if latest_prompt:
        # Increment the version number for the new prompt
        new_version = latest_prompt.version + 1
    else:
        # Start with version 1 if no existing prompt is found
        new_version = 1

    # Create the new prompt
    new_prompt = Prompt(
        name=prompt.name,
        prompt=prompt.prompt,
        model_name=prompt.model_name,
        version=new_version,
    )
    db_session.add(new_prompt)
    db_session.commit()
    db_session.refresh(new_prompt)
    return new_prompt


def delete_prompt(db_session, prompt: PromptDeleteRequest) -> bool:
    """
    Delete a specific version of a prompt.
    """
    db_prompt = (
        db_session.query(Prompt)
        .filter(
            Prompt.name == prompt.name,
            Prompt.model_name == prompt.model_name,
            Prompt.version == prompt.version,
        )
        .first()
    )
    if db_prompt:
        db_session.delete(db_prompt)
        db_session.commit()
        return True
    return False


def delete_model_prompts(db_session, model_name: str) -> bool:
    """
    Delete all prompts for a specific model.
    """
    db_prompts = db_session.query(Prompt).filter(Prompt.model_name == model_name).all()
    if db_prompts:
        for prompt in db_prompts:
            db_session.delete(prompt)
        db_session.commit()
        return True
    return False
