# app/services/llm_client.py
import os
import time
import json
import logging
import httpx
from dotenv import load_dotenv
from groq import Groq
from groq import RateLimitError, BadRequestError, APIStatusError, APIError
from openai import OpenAI
from openai import RateLimitError as OpenAIRateLimitError
from openai import APIStatusError as OpenAIAPIStatusError
from openai import APIError as OpenAIAPIError
import boto3
from botocore.exceptions import ClientError
from app.services.token_tracker import record_from_response

logger = logging.getLogger(__name__)


load_dotenv()

GROQ_MODELS = {
    "qwen3": "qwen/qwen3-32b",
    "gptoss": "openai/gpt-oss-20b",
    "gptoss120b": "openai/gpt-oss-120b",
    "llama4": "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen3.6": "qwen/qwen3.6-27b",
    "llama33": "llama-3.3-70b-versatile",
}

# Bedrock Models — Amazon Nova
BEDROCK_MODELS = {
    "nova-lite-2": "eu.amazon.nova-2-lite-v1:0",
}

# GitHub Models — usage évaluation / prototypage uniquement (rate limits stricts)
GITHUB_MODELS = {
    "gpt-4.1": "openai/gpt-4.1",
    "gpt-4.1-mini": "openai/gpt-4.1-mini",
    "gpt-4o": "openai/gpt-4o",
    "gpt-5": "openai/gpt-5"
}

GITHUB_MODELS_ENDPOINT = "https://models.github.ai/inference"

ALL_MODELS = {**GROQ_MODELS, **BEDROCK_MODELS, **GITHUB_MODELS}

# Modeles "thinking" pour lesquels on demande a Groq de masquer le raisonnement
# (evite que <think>...</think> casse le mode JSON object).
_REASONING_MODELS = {"qwen3","qwen3.6",}


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


def _is_overloaded_error(err: Exception) -> bool:
    """503 over capacity / 502 / 504 -- erreurs serveur transitoires cote Groq."""
    status = getattr(err, "status_code", None)
    if status in (502, 503, 504):
        return True
    msg = str(err).lower()
    return (
        ("over capacity" in msg) or ("503" in msg) or ("internal_server_error" in msg)
    )


def _is_json_validate_failed(err: Exception) -> bool:
    """400 json_validate_failed -- qwen3 a genere du texte non-JSON (souvent du thinking)."""
    return "json_validate_failed" in str(err)


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
    JSON object mode. Robuste face a :
    - 429 RateLimitError -> retry exponentiel
    - 503 over capacity (Groq sature) -> retry exponentiel
    - 400 json_validate_failed (qwen3 thinking) -> retry exponentiel

    Pour qwen3, ajoute automatiquement reasoning_format="hidden" (Groq masque le
    raisonnement cote serveur, ne renvoie que le JSON final).
    """
    client = _build_client()
    model_name = _resolve_model(model_alias)

    extra_kwargs = {}
    if model_alias in _REASONING_MODELS:
        # Officiellement supporte par Groq pour les modeles qwen3 (voir model card)
        extra_kwargs["reasoning_format"] = "hidden"

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
                **extra_kwargs,
            )

            record_from_response(response, model_name)
            content = response.choices[0].message.content if response.choices else ""
            return (content or "").strip()

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[RateLimit] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

        except BadRequestError as e:
            last_error = e
            if _is_json_validate_failed(e) and attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[JSONValidateFailed] {model_alias} tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

        except (APIStatusError, APIError) as e:
            last_error = e
            if _is_overloaded_error(e) and attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[GroqOverloaded] {model_alias} tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

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
    """JSON schema mode (a utiliser pour gptoss120b)."""
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
                        "schema": schema,
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            record_from_response(response, model_name)
            content = response.choices[0].message.content if response.choices else ""
            return (content or "").strip()

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[RateLimit] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                raise
        except BadRequestError as e:
            if "json_validate_failed" in str(e):
                last_error = e
                if attempt < max_retries - 1:
                    sleep_time = retry_sleep * (attempt + 1)
                    print(
                        f"[JSONValidateFailed] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                    )
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
    if model_alias in BEDROCK_MODELS:
        return _resolve_bedrock_model(model_alias), "bedrock"
    if model_alias in GITHUB_MODELS:
        return GITHUB_MODELS[model_alias], "github"
    raise ValueError(
        f"Unknown model alias '{model_alias}'. Allowed: {list(ALL_MODELS.keys())}"
    )


# ═══════════════════════════════════════════════════════════════
#  Amazon Bedrock — Nova Lite 2
# ═══════════════════════════════════════════════════════════════


def _build_bedrock_client():
    """Initialise client Bedrock avec AWS credentials."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "eu-west-3")

    if not access_key or not secret_key:
        raise RuntimeError(
            "AWS_ACCESS_KEY_ID ou AWS_SECRET_ACCESS_KEY manquants dans .env. "
            "Demande les credentials à ton manager."
        )

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _build_bedrock_management_client():
    """Initie un client Bedrock (management) pour lister les modèles disponibles."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "eu-west-3")

    if not access_key or not secret_key:
        raise RuntimeError(
            "AWS_ACCESS_KEY_ID ou AWS_SECRET_ACCESS_KEY manquants dans .env. "
            "Demande les credentials à ton manager."
        )

    return boto3.client(
        "bedrock",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def _list_available_bedrock_models() -> list[str]:
    """Retourne une liste de modèles visibles dans le compte Bedrock."""
    try:
        client = _build_bedrock_management_client()
        response = client.list_models(MaxResults=50)
        models = response.get("models", []) or []
        return [m.get("modelId") or m.get("model_id") or "" for m in models if m]
    except Exception:
        return []


def _normalize_bedrock_model_id(model_id: str) -> str:
    """Normalise l'ID Bedrock pour ajouter le suffixe :0 si nécessaire."""
    if not model_id:
        return model_id
    normalized = model_id.strip()
    if ":" not in normalized:
        normalized = f"{normalized}:0"
    return normalized


def _resolve_bedrock_model(model_alias: str) -> str:
    """Résout alias en ID Bedrock complet."""
    default_model_id = BEDROCK_MODELS.get(model_alias, "")
    if default_model_id:
        model_id = os.getenv("BEDROCK_MODEL_ID", default_model_id)
    else:
        model_id = os.getenv("BEDROCK_MODEL_ID", "")

    model_id = _normalize_bedrock_model_id(model_id)

    if not model_id:
        raise ValueError(
            f"Unknown Bedrock model alias '{model_alias}' et aucune BEDROCK_MODEL_ID définie. "
            f"Allowed aliases: {list(BEDROCK_MODELS.keys())}."
        )

    return model_id


def call_bedrock(
    system_prompt: str,
    user_prompt: str,
    model_alias: str = "nova-lite-2",
    temperature: float = 0.0,
    max_tokens: int = 1300,
    max_retries: int = 6,
    retry_sleep: float = 1.5,
) -> str:
    """
    Appel Bedrock/Nova Lite 2 via l'API Converse (nouvelle API Bedrock).

    Robuste face à :
    - ThrottlingException (rate limit) → retry exponentiel
    - ValidationException (format error) → pas de retry
    - AccessDeniedException (credentials invalides) → erreur immédiate

    Note: Bedrock n'a PAS de mode JSON natif. On ajoute une instruction
    au prompt pour demander du JSON valide en sortie.
    """
    client = _build_bedrock_client()
    model_id = _resolve_bedrock_model(model_alias)

    # Ajouter une instruction JSON au prompt utilisateur
    user_prompt_with_json = (
        f"{user_prompt}\n\n"
        "Réponds UNIQUEMENT avec un objet JSON valide. Aucun autre texte avant ou après."
    )

    last_error = None

    for attempt in range(max_retries):
        try:
            # Format Bedrock Converse API (nouvelle API pour Nova)
            # Note: system doit être un array, pas une string!
            response = client.converse(
                modelId=model_id,
                system=[{"text": system_prompt}],
                messages=[
                    {"role": "user", "content": [{"text": user_prompt_with_json}]}
                ],
                inferenceConfig={
                    "temperature": temperature,
                    "maxTokens": min(max_tokens, 5120),
                },
            )

            # Récupérer le contenu de la réponse (format Converse API)
            content = ""
            if "output" in response and "message" in response["output"]:
                message = response["output"]["message"]
                if "content" in message and len(message["content"]) > 0:
                    content = message["content"][0].get("text", "").strip()

            # Enregistrer les tokens (Bedrock retourne usage dans la réponse)
            usage = response.get("usage", {})
            # Créer un objet compatible avec record_from_response
            mock_response = type(
                "obj",
                (object,),
                {
                    "usage": type(
                        "obj",
                        (object,),
                        {
                            "prompt_tokens": usage.get("inputTokens", 0),
                            "completion_tokens": usage.get("outputTokens", 0),
                        },
                    )(),
                    "model": model_id,
                },
            )()
            record_from_response(mock_response, model_id)

            return content

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            last_error = e

            # Throttling → retry avec pause
            if error_code == "ThrottlingException" and attempt < max_retries - 1:
                sleep_time = retry_sleep * (2**attempt)
                print(
                    f"[Bedrock Throttled] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            # Accès refusé → erreur immédiate
            elif error_code == "AccessDeniedException":
                raise RuntimeError(
                    "Credentials AWS invalides ou permissions insuffisantes. "
                    "Vérifie AWS_ACCESS_KEY_ID et AWS_SECRET_ACCESS_KEY."
                ) from e
            # Validation error → erreur explicite
            elif error_code == "ValidationException":
                if "model identifier is invalid" in error_message.lower():
                    available = _list_available_bedrock_models()
                    available_sample = (
                        ", ".join(available[:8])
                        if available
                        else "<liste indisponible>"
                    )
                    raise RuntimeError(
                        f"Model invalide pour Bedrock : {model_id}. "
                        "Vérifie la valeur BEDROCK_MODEL_ID dans .env et la disponibilité du modèle "
                        "dans la région eu-west-3."
                        f" Message AWS: {error_message}. "
                        f"Modèles visibles : {available_sample}"
                    ) from e
                raise RuntimeError(
                    f"Validation Bedrock échouée pour le modèle {model_id} : {error_message}"
                ) from e
            else:
                break

        except Exception as e:
            last_error = e
            # Erreurs réseau/transitoires
            if attempt < max_retries - 1 and not isinstance(
                e, (ValueError, RuntimeError)
            ):
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[Bedrock Error] {type(e).__name__} tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

    raise last_error


# ═══════════════════════════════════════════════════════════════
#  Wrapper Générique — Route vers Groq ou Bedrock
# ═══════════════════════════════════════════════════════════════


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model_alias: str = None,
    temperature: float = 0.0,
    max_tokens: int = 1300,
    max_retries: int = 6,
    retry_sleep: float = 1.5,
    provider: str = None,
) -> str:
    """
    Wrapper générique pour appeler Groq ou Bedrock selon la config.

    Si provider=None, utilise LLM_PROVIDER de .env (défaut: "groq")
    Si model_alias=None, utilise le modèle par défaut du provider
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "groq")

    if provider == "groq":
        if model_alias is None:
            model_alias = os.getenv("LLM_DEFAULT_MODEL", "qwen3")
        return call_groq(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_alias=model_alias,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            retry_sleep=retry_sleep,
        )
    elif provider == "bedrock":
        if model_alias is None:
            model_alias = os.getenv("BEDROCK_DEFAULT_MODEL", "nova-lite-2")
        return call_bedrock(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_alias=model_alias,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
            retry_sleep=retry_sleep,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. " f"Allowed: ['groq', 'bedrock']"
        )


# ═══════════════════════════════════════════════════════════════
#  GitHub Models — pour LLM-as-Judge (évaluation uniquement)
# ═══════════════════════════════════════════════════════════════


def _build_github_client() -> OpenAI:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN manquant dans .env. "
            "Crée un PAT sur https://github.com/settings/tokens (scope: models:read)."
        )
    return OpenAI(
        base_url=GITHUB_MODELS_ENDPOINT,
        api_key=token,
        http_client=httpx.Client(verify=False, timeout=60.0),
    )


def _resolve_github_model(model_alias: str) -> str:
    model_name = GITHUB_MODELS.get(model_alias)
    if not model_name:
        raise ValueError(
            f"Unknown GitHub model alias '{model_alias}'. "
            f"Allowed: {list(GITHUB_MODELS.keys())}"
        )
    return model_name


def call_github_models(
    system_prompt: str,
    user_prompt: str,
    model_alias: str = "gpt-4.1",
    temperature: float = 0.0,
    max_tokens: int = 1000,
    max_retries: int = 6,
    retry_sleep: float = 4.0,
) -> str:
    """
    Appel JSON object via GitHub Models (gratuit, rate-limited).
    Idéal pour LLM-as-Judge. NE PAS utiliser en production.

    Retries automatiques sur :
    - 429 RateLimitError (quota dépassé) -> pause exponentielle longue
    - 5xx transient errors -> retry exponentiel court
    """
    client = _build_github_client()
    model_name = _resolve_github_model(model_alias)

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
            record_from_response(response, model_name)
            content = response.choices[0].message.content if response.choices else ""
            return (content or "").strip()

        except OpenAIRateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Backoff long car GitHub Models a un quota par minute
                sleep_time = retry_sleep * (2**attempt)
                print(
                    f"[GitHub RateLimit] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

        except (OpenAIAPIStatusError, OpenAIAPIError) as e:
            last_error = e
            status = getattr(e, "status_code", None)
            if status in (500, 502, 503, 504) and attempt < max_retries - 1:
                sleep_time = retry_sleep * (attempt + 1)
                print(
                    f"[GitHub Overloaded {status}] tentative {attempt + 1}/{max_retries} -> pause {sleep_time:.1f}s"
                )
                time.sleep(sleep_time)
            else:
                break

    raise last_error


class BedrockChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(
        self, model, messages, temperature, response_format, max_tokens, **kwargs
    ):
        # Séparer system prompt et messages user/assistant
        system_content = ""
        converse_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, dict):
                content = content.get("text", "")
            elif not isinstance(content, str):
                content = str(content)

            if role == "system":
                system_content = content
            else:
                # Bedrock Converse accepte "user" et "assistant" uniquement
                converse_role = "assistant" if role == "assistant" else "user"
                converse_messages.append(
                    {
                        "role": converse_role,
                        "content": [{"text": content}],
                    }
                )

        # Bedrock Converse exige au moins un message et que le premier soit "user"
        if not converse_messages:
            converse_messages = [{"role": "user", "content": [{"text": "Continue."}]}]

        # Instruction JSON ajoutée au dernier message user (Nova Lite n'a pas de mode JSON natif)
        for msg in reversed(converse_messages):
            if msg["role"] == "user":
                msg["content"][0]["text"] += (
                    "\n\nRéponds UNIQUEMENT avec un objet JSON valide. "
                    "Aucun texte avant ou après le JSON."
                )
                break

        payload = {
            "messages": converse_messages,
            "inferenceConfig": {
                "temperature": temperature,
                "maxTokens": max_tokens,
            },
        }

        # Ajouter le system prompt si présent (format Converse)
        if system_content:
            payload["system"] = [{"text": system_content}]

        try:
            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload),
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")
            region = getattr(self.client, "meta", None)
            region_name = getattr(
                region, "region_name", os.getenv("AWS_REGION", "unknown")
            )

            if (
                error_code == "ValidationException"
                and "model identifier is invalid" in error_message.lower()
            ):
                available = _list_available_bedrock_models()
                available_sample = (
                    ", ".join(available[:8]) if available else "<liste indisponible>"
                )
                raise RuntimeError(
                    f"Bedrock model invalide pour '{model}' dans la région '{region_name}'. "
                    "Vérifie BEDROCK_MODEL_ID dans .env et la disponibilité du modèle. "
                    f"Modèles visibles : {available_sample}."
                ) from e
            if error_code == "AccessDeniedException":
                raise RuntimeError(
                    "Accès Bedrock refusé : vérifie AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY et les permissions."
                ) from e
            raise RuntimeError(
                f"Erreur Bedrock invoke_model ({error_code}): {error_message}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Échec de l'appel Bedrock : {e}") from e

        response_body = json.loads(response["body"].read().decode("utf-8"))

        # Nova Lite retourne via la clé "output" (Converse) ou "content" (Messages API)
        content = ""
        if "output" in response_body:
            # Format Converse API
            output_msg = response_body["output"].get("message", {})
            content_blocks = output_msg.get("content", [])
            if content_blocks:
                content = content_blocks[0].get("text", "").strip()
        elif "content" in response_body and response_body["content"]:
            # Format Messages API (Anthropic-style)
            content = response_body["content"][0].get("text", "").strip()
        else:
            content = response_body.get("outputText", "").strip()

        usage = response_body.get("usage", {})
        usage_obj = type(
            "usage",
            (),
            {
                "prompt_tokens": usage.get("inputTokens", 0),
                "completion_tokens": usage.get("outputTokens", 0),
            },
        )()
        message_obj = type("message", (), {"content": content})()
        choice_obj = type("choice", (), {"message": message_obj})()

        return type("resp", (), {"choices": [choice_obj], "usage": usage_obj})()


class BedrockChat:
    def __init__(self, client):
        self.completions = BedrockChatCompletions(client)


class BedrockClient:
    def __init__(self, client):
        self.chat = BedrockChat(client)


def build_llm_client(model_alias: str):
    """Retourne (client, model_name) pour n'importe quel alias Groq ou Bedrock."""
    model_name, provider = _resolve_any_model(model_alias)
    if provider == "groq":
        return _build_client(), model_name
    if provider == "bedrock":
        return BedrockClient(_build_bedrock_client()), model_name
    raise ValueError(f"Unsupported provider for alias '{model_alias}'")
