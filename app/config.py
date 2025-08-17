from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Shopify App Configuration
    shopify_api_key: str
    shopify_api_secret: str
    shopify_scopes: str = "read_products"
    
    # App Configuration
    app_url: str
    environment: str = "development"
    secret_key: str
    
    # CORS
    allowed_origins: str = "https://admin.shopify.com"
    
    # JWT Configuration
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated origins to list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def shopify_scopes_list(self) -> List[str]:
        """Convert comma-separated scopes to list"""
        return [scope.strip() for scope in self.shopify_scopes.split(",")]


# Global settings instance
settings = Settings()