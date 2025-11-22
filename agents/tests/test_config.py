"""Tests for agent configuration."""

import re

import pytest


# Known deprecated/removed model names that should not be used
DEPRECATED_MODELS = [
    r"claude-3-sonnet-20240229",  # Deprecated March 2025
    r"claude-3-opus-20240229",
    r"claude-3-haiku-20240307",
    r"gpt-4-0314",
    r"gpt-4-0613",
    r"gpt-3\.5-turbo-0301",
]


class TestModelConfiguration:
    """Tests for LLM model configuration."""

    def test_default_model_is_not_deprecated(self):
        """Default model should not be a deprecated model."""
        from src.config import Settings

        settings = Settings()

        for pattern in DEPRECATED_MODELS:
            assert not re.match(pattern, settings.llm_model), (
                f"Default model '{settings.llm_model}' matches deprecated pattern '{pattern}'. "
                f"Update to a current model version."
            )

    def test_model_name_format_is_valid(self):
        """Model name should follow expected format."""
        from src.config import Settings

        settings = Settings()

        # Should be non-empty
        assert settings.llm_model, "llm_model should not be empty"

        # Should not contain obvious placeholders
        assert "xxx" not in settings.llm_model.lower()
        assert "placeholder" not in settings.llm_model.lower()


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_settings_loads_without_error(self):
        """Settings should load without errors."""
        from src.config import get_settings

        settings = get_settings()
        assert settings is not None

    def test_api_base_has_valid_format(self):
        """API base URL should be valid."""
        from src.config import get_settings

        settings = get_settings()
        assert settings.agent_api_base.startswith("http")

    def test_mz_dsn_is_valid(self):
        """Materialize DSN should be properly formatted."""
        from src.config import get_settings

        settings = get_settings()
        assert "postgresql" in settings.mz_dsn
        assert settings.mz_host in settings.mz_dsn
