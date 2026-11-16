"""Validated application settings. Secrets are supplied only through environment variables."""
from functools import lru_cache
from pathlib import Path
import os
from typing import Literal
import yaml
from pydantic import Field,model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict
CONFIG_YAML_PATH=Path(__file__).parent/"config.yaml"
def _load_yaml_config():
    with CONFIG_YAML_PATH.open("r",encoding="utf-8") as f: data=yaml.safe_load(f) or {}
    if not isinstance(data,dict): raise ValueError("config.yaml must contain a mapping")
    return data
class Settings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore")
    groq_api_key:str=Field(...,min_length=1)
    documind_api_key:str|None=None
    groq_model:str="openai/gpt-oss-120b"
    supabase_url:str=""
    supabase_anon_key:str=""
    supabase_bucket:str="documind-documents"
    supabase_timeout_seconds:int=Field(default=20,gt=0,le=60)
    vector_db_path:str="./data/vector_db"
    upload_path:str="./data/uploads"
    chunking_strategy:Literal["recursive","fixed"]="recursive"
    chunk_size:int=Field(default=1000,gt=0)
    chunk_overlap:int=Field(default=200,ge=0)
    top_k:int=Field(default=4,ge=1,le=20)
    temperature:float=Field(default=.1,ge=0,le=2)
    max_tokens:int=Field(default=1024,gt=0)
    llm_timeout_seconds:int=Field(default=30,gt=0)
    embedding_model:str="sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size:int=Field(default=8,gt=0)
    app_name:str="DocuMind RAG"
    app_version:str="0.3.0"
    environment:Literal["development","production"]="development"
    search_type:Literal["similarity","mmr"]="similarity"
    mmr_diversity:float=Field(default=.5,ge=0,le=1)
    max_file_size_mb:int=Field(default=20,gt=0)
    allowed_extensions:list[str]=[".pdf"]
    log_level:str="INFO"
    log_format:Literal["json","text"]="json"
    collection_name:str="documind_documents"
    @model_validator(mode="after")
    def validate_runtime_settings(self):
        if self.chunk_overlap>=self.chunk_size: raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.environment=="production" and (not self.supabase_url or not self.supabase_anon_key):
            raise ValueError("Supabase URL and publishable key are required in production")
        return self
@lru_cache
def get_settings():
    c=_load_yaml_config(); app=c.get("app") or {}; llm=c.get("llm") or {}; emb=c.get("embeddings") or {}; ch=c.get("chunking") or {}; ret=c.get("retrieval") or {}; vs=c.get("vector_store") or {}; up=c.get("upload") or {}; log=c.get("logging") or {}
    ex=os.getenv("ALLOWED_EXTENSIONS",up.get("allowed_extensions",[".pdf"]))
    if isinstance(ex,str): ex=[x.strip().lower() for x in ex.split(",") if x.strip()]
    return Settings(app_name=os.getenv("APP_NAME",app.get("name","DocuMind RAG")),app_version=os.getenv("APP_VERSION",app.get("version","0.3.0")),environment=os.getenv("ENVIRONMENT",app.get("environment","development")),groq_model=os.getenv("GROQ_MODEL",llm.get("model","openai/gpt-oss-120b")),temperature=os.getenv("LLM_TEMPERATURE",llm.get("temperature",.1)),max_tokens=os.getenv("LLM_MAX_TOKENS",llm.get("max_tokens",1024)),llm_timeout_seconds=os.getenv("LLM_TIMEOUT_SECONDS",llm.get("timeout_seconds",30)),embedding_model=os.getenv("EMBEDDING_MODEL",emb.get("model_name","sentence-transformers/all-MiniLM-L6-v2")),embedding_batch_size=os.getenv("EMBEDDING_BATCH_SIZE",emb.get("batch_size",8)),chunking_strategy=os.getenv("CHUNKING_STRATEGY",ch.get("strategy","recursive")),chunk_size=os.getenv("CHUNK_SIZE",ch.get("chunk_size",1000)),chunk_overlap=os.getenv("CHUNK_OVERLAP",ch.get("chunk_overlap",200)),top_k=os.getenv("TOP_K",ret.get("top_k",4)),search_type=os.getenv("SEARCH_TYPE",ret.get("search_type","similarity")),mmr_diversity=os.getenv("MMR_DIVERSITY",ret.get("mmr_diversity",.5)),collection_name=os.getenv("COLLECTION_NAME",vs.get("collection_name","documind_documents")),vector_db_path=os.getenv("VECTOR_DB_PATH",vs.get("persist_directory","./data/vector_db")),upload_path=os.getenv("UPLOAD_PATH",up.get("directory","./data/uploads")),max_file_size_mb=os.getenv("MAX_FILE_SIZE_MB",up.get("max_file_size_mb",20)),allowed_extensions=ex,log_level=os.getenv("LOG_LEVEL",log.get("level","INFO")),log_format=os.getenv("LOG_FORMAT",log.get("format","json")),supabase_url=os.getenv("SUPABASE_URL",""),supabase_anon_key=os.getenv("SUPABASE_ANON_KEY",""),supabase_bucket=os.getenv("SUPABASE_BUCKET","documind-documents"),supabase_timeout_seconds=os.getenv("SUPABASE_TIMEOUT_SECONDS",20))
settings=get_settings()
