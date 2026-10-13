"""Deterministic demonstration adapter with basic identifier screening.

Provider names are retained for compatibility. No remote model is connected.
"""
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Vent Weaning Readiness Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return (
            f"[{self.system_name} demonstration]: A mock adapter is active. "
            "No model inference or clinical verification was performed."
        )


class LLMFactory:
    """Return the deterministic mock for all legacy provider selections."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Vent Weaning Readiness Agent"):
        return MockLLM(system_name)
