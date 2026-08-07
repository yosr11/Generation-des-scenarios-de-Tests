# eval/DeepEval/groq_llm.py

from deepeval.models.base_model import DeepEvalBaseLLM
from app.services.llm_client import call_groq


class GroqLLM(DeepEvalBaseLLM):
    def __init__(self, model_alias="gptoss120b"):
        self.model_alias = model_alias
        super().__init__()

    def load_model(self):
        return self.model_alias

    def generate(self, prompt: str) -> str:
        return call_groq(
            system_prompt="You are an expert QA evaluation judge.",
            user_prompt=prompt,
            model_alias=self.model_alias,
            temperature=0.0,
            max_tokens=6000,  # qwen3.6 : reasoning_format=hidden consomme quand même
                              # des tokens de raisonnement dans le budget max_tokens ;
                              # 2000 était insuffisant → content vide → json_validate_failed
        )

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self):
        return f"Groq-{self.model_alias}"