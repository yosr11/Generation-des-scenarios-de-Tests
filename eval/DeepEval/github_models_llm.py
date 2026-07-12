"""
Wrapper DeepEval pour utiliser GitHub Models (gpt-4.1, gpt-4o, etc.)
comme juge LLM dans GEval, au lieu d'OpenAI directement.
"""

from deepeval.models.base_model import DeepEvalBaseLLM
from app.services.llm_client import call_github_models


class GitHubModelsLLM(DeepEvalBaseLLM):
    def __init__(self, model_alias: str = "gpt-4.1"):
        self.model_alias = model_alias
        super().__init__()

    def load_model(self):
        return self.model_alias

    def generate(self, prompt: str) -> str:
        return call_github_models(
            system_prompt="You are a helpful assistant.",
            user_prompt=prompt,
            model_alias=self.model_alias,
            temperature=0.0,
            max_tokens=1000,
        )

    async def a_generate(self, prompt: str) -> str:
        # Si call_github_models est synchrone, on l'appelle directement.
        # Si tu as une version async, remplace l'appel ci-dessous.
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return f"GitHub Models ({self.model_alias})"