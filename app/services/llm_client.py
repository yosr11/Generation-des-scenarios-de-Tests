# app/services/llm_client.py
import os
import time
import json
import httpx
from dotenv import load_dotenv
from groq import Groq
from groq import RateLimitError, BadRequestError

load_dotenv(override=True)

GROQ_MODELS = {
    "qwen3": "qwen/qwen3-32b",
    "gptoss": "openai/gpt-oss-20b",
    "gptoss120b": "openai/gpt-oss-120b",
    "llama4": "meta-llama/llama-4-scout-17b-16e-instruct",
    
}



ALL_MODELS = {**GROQ_MODELS}


def _build_client():
    transport = httpx.HTTPTransport(verify=False)
    return Groq(
        api_key=os.getenv("GROQ_API_KEY"),
        http_client=httpx.Client(transport=transport, timeout=60.0),
    )


def _resolve_model(model_alias: str) -> str:
    model_name = GROQ_MODELS.get(model_alias)
    if not model_name:
        raise ValueError(
            f"Unknown model alias '{model_alias}'. Allowed values: {list(GROQ_MODELS.keys())}"
        )
    return model_name


def call_groq(
    system_prompt: str,
    user_prompt: str,
    model_alias: str = "qwen3",
    temperature: float = 0.0,
    max_tokens: int = 1300,
    max_retries: int = 6,
    retry_sleep: float = 1.5,
) -> str:
    """
    JSON object mode (bien pour qwen3)
    """
    client = _build_client()
    model_name = _resolve_model(model_alias)

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.choices[0].message.content if response.choices else ""
            return (content or "").strip()

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(f"[RateLimit] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s")
                time.sleep(sleep_time)
            else:
                raise

    raise last_error


def call_groq_json_schema(
    system_prompt: str,
    user_prompt: str,
    schema: dict,
    model_alias: str = "gptoss120b",
    temperature: float = 0.0,
    max_tokens: int = 1300,
    max_retries: int = 6,
    retry_sleep: float = 1.5,
) -> str:
    """
    JSON schema mode (à utiliser pour gptoss120b)
    """
    client = _build_client()
    model_name = _resolve_model(model_alias)

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent1_judge_result",
                        "strict": False,
                        "schema": schema
                    }
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            content = response.choices[0].message.content if response.choices else ""
            return (content or "").strip()

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(f"[RateLimit] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s")
                time.sleep(sleep_time)
            else:
                raise
        except BadRequestError as e:
            if "json_validate_failed" in str(e):
                last_error = e
                if attempt < max_retries - 1:
                    sleep_time = retry_sleep * (attempt + 1)
                    print(f"[JSONValidateFailed] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                else:
                    raise
            else:
                raise

    raise last_error





def _resolve_any_model(model_alias: str) -> tuple:
    """Retourne (model_name, provider) depuis un alias."""
    if model_alias in GROQ_MODELS:
        return GROQ_MODELS[model_alias], "groq"
    raise ValueError(
        f"Unknown model alias '{model_alias}'. Allowed: {list(ALL_MODELS.keys())}"
    )


def build_llm_client(model_alias: str):
    """Retourne (client, model_name) pour n'importe quel alias (Groq ou OpenRouter)."""
    model_name, provider = _resolve_any_model(model_alias)
    if provider == "groq":
        return _build_client(), model_name
  