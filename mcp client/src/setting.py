from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def require_env(name:str)->str:
    value =os.getenv(name)
    if not value:
        raise RuntimeError(f"Missinng reuqired environment variable: {name}")
    return value


@dataclass
class Config:
    db_port: str
    db_host: str
    db_name: str
    db_username: str
    db_password: str
    port: int
    host: str
    log_level: str
    mcp_server_url: str
    error_log_url: str
    region: str | None
    model_id: str | None

def get_config():
    return Config(
        db_port=os.getenv('DB_PORT', '5432'),
        db_host=os.getenv('DB_HOST', 'localhost'),
        db_name=os.getenv('DB_NAME', 'mcp_chatbot'),
        db_username=os.getenv('DB_USERNAME', 'postgres'),
        db_password=require_env('DB_PASSWORD'),
        port=int(os.getenv('PORT', '8080')),
        host=os.getenv('HOST', '0.0.0.0'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        mcp_server_url=os.getenv('MCP_SERVER_URL', 'http://localhost:8000/mcp'),
        error_log_url=os.getenv('ERROR_LOG_URL',''),
        region=os.getenv('REGION'),
        model_id=os.getenv('MODEL_ID'),
    )

config = get_config()
