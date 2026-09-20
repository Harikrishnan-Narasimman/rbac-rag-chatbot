from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    qdrant_path: str = "resources/qdrant_db"
    qdrant_collection: str = "company_docs"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    jwt_secret_key: str

settings = Settings()