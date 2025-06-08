import requests
import os
import typing as t

FAILSAFE_PROMPTS_PATH = "src/modules/document/failsafe_prompts"
POST_URL = "http://localhost:8080/api/prompt"


def read_jinja_to_string(load_only: str = None) -> t.Dict[str, str]:
    """Reads the Jinja templates in the specified directory and returns a dictionary of raw strings."""
    # Iterate over the .jinja files in the failsafe prompts directory and load them to a list of strings
    failsafe_prompts = dict()
    for file in os.listdir(FAILSAFE_PROMPTS_PATH):
        if file.endswith(".jinja"):
            if load_only and file != load_only:
                continue
            print(f"Loading prompt: {file}")
            with open(os.path.join(FAILSAFE_PROMPTS_PATH, file), 'r') as f:
                # Dict has {"prompt_name": "prompt_content"}
                failsafe_prompts[file.split(".")[0]] = f.read()
    # If no prompts were found, raise an error
    if not failsafe_prompts:
        raise ValueError("No failsafe prompts found in the specified directory.")

    print(f"Found {len(failsafe_prompts)} failsafe prompts to load to postgres.")
    return failsafe_prompts


def prepare_post_data(prompts: t.Dict[str, str], model_name: str = "gpt-4o") -> dict:
    """Prepares the data to be posted to the API."""
    return {
        "prompts": [
            {
                "name": name,
                "prompt": content,
                "model_name": model_name
            }
            for name, content in prompts.items()
        ]
    }


def post_json(data: dict, url: str):
    """Uploads the prompts to postgres via the back-end API"""
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=data, headers=headers, verify=False)
    response.raise_for_status()  # Raise an error for bad responses
    return response.json()


def load_failsafe_prompts(load_only: str = None, model_name: str = "gpt-4o"):
    """
    Loads failsafe prompts from Jinja templates and posts them to the API.

    :param load_only: If specified, only loads the prompt with this name.
    :param model_name: The model name to associate with the prompts.
    """
    try:
        # Read the Jinja templates and convert them to raw strings
        failsafe_prompts = read_jinja_to_string(load_only=load_only)
        # Prepare the data to be posted to the API
        post_data = prepare_post_data(failsafe_prompts, model_name=model_name)
        # Post the failsafe prompts to the API
        for prompt in post_data["prompts"]:
            result = post_json(
                data=prompt,
                url=POST_URL,
            )
            print(f"Successfully loaded prompt: {prompt['name']} with response: {result}")
    except requests.RequestException as e:
        print(f"Failed to load failsafe prompts: {e}")


if __name__ == "__main__":
    load_failsafe_prompts()
