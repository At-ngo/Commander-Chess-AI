"""
Commander Chess AI — API Configuration
"""

from typing import List


class Settings:
    PROJECT_NAME: str = "Commander Chess AI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",  # Cho phép phát triển nội bộ
    ]
    
    # Server Defaults
    HOST: str = "0.0.0.0"
    PORT: int = 8000


settings = Settings()
