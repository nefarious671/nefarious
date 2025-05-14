
"""Placeholder Gemini API adapter."""
import os

class GeminiAdapter:
    def __init__(self, api_key_env='GEMINI_API_KEY'):
        self.api_key = os.getenv(api_key_env)
        if not self.api_key:
            raise RuntimeError(f'Gemini API key not found in env var {api_key_env}')

    def call(self, prompt: str, model: str = 'gemini-pro', **kwargs) -> str:
        """Stub call that echoes prompt (replace with real API)."""
        # TODO: integrate real Gemini API client
        print(f"[GeminiAdapter] Would call model={model}:\n{prompt[:200]}...")
        return "[Gemini stub response]\n" + prompt[:100]
