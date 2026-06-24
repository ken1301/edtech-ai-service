import unittest

from pydantic import ValidationError

from infrastructure.config import Settings


def _settings_overrides(**overrides):
    base = {
        "JWT_SECRET": "jwt-secret-for-tests",
        "AI_SERVICE_API_KEY": "internal-key",
        "LOCAL_REDIS_URL": "redis://localhost:6379/0",
        "REDIS_PASSWORD": "password",
        "REDIS_PORT": 6379,
        "MONGO_DB_NAME": "db",
        "LOCAL_MONGO_URL": "mongodb://localhost",
        "MONGO_USER": "mongo",
        "MONGO_PASSWORD": "password",
        "MONGO_PORT": 27017,
        "MINIO_API_PORT": 9000,
        "MINIO_CONSOLE_PORT": 9001,
        "MINIO_ROOT_USER": "minio",
        "MINIO_ROOT_PASSWORD": "password",
        "MINIO_ENDPOINT_URL": "http://localhost:9000",
        "REGION_NAME": "us-east-1",
        "OPENAI_API_KEY": "openai-key",
    }
    base.update(overrides)
    return base


class LLMSettingsValidationTests(unittest.TestCase):
    def test_settings_require_openai_key_when_openai_provider_configured(self):
        with self.assertRaises(ValidationError):
            Settings(**_settings_overrides(OPENAI_API_KEY=None))

    def test_settings_reject_unknown_openai_model(self):
        with self.assertRaises(ValidationError):
            Settings(**_settings_overrides(STRONG_LLM_MODEL="unknown-model"))

    def test_settings_require_groq_key_when_groq_provider_configured(self):
        with self.assertRaises(ValidationError):
            Settings(
                **_settings_overrides(
                    STRONG_LLM_PROVIDER="groq",
                    STRONG_LLM_MODEL="llama-3.1-8b-instant",
                    GROQ_API_KEY=None,
                )
            )

    def test_settings_accept_valid_provider_configuration(self):
        settings = Settings(
            **_settings_overrides(
                GROQ_API_KEY="groq-key",
                MID_LLM_PROVIDER="groq",
                MID_LLM_MODEL="llama-3.1-8b-instant",
            )
        )

        self.assertEqual(settings.MID_LLM_PROVIDER, "groq")
        self.assertEqual(settings.MID_LLM_MODEL, "llama-3.1-8b-instant")


if __name__ == "__main__":
    unittest.main()