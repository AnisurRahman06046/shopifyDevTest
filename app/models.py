# from sqlalchemy import (
#     Column,
#     Integer,
#     String,
#     Text,
#     Boolean,
#     DateTime,
#     JSON,
#     ForeignKey,
# )
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func
# from datetime import datetime
# from app.database import Base


# class Shop(Base):
#     """Shopify shop/store model"""

#     __tablename__ = "shops"

#     id = Column(Integer, primary_key=True, index=True)

#     # Core identification
#     shop_domain = Column(String(255), unique=True, index=True, nullable=False)
#     myshopify_domain = Column(String(255), nullable=True)

#     # OAuth & API access
#     access_token = Column(Text, nullable=True)  # Should be encrypted in production
#     scopes = Column(String(500), nullable=True)

#     # Shop information from Shopify API
#     shop_name = Column(String(255), nullable=True)
#     shop_email = Column(String(255), nullable=True)
#     shop_owner = Column(String(255), nullable=True)

#     # Location & settings
#     country_code = Column(String(10), nullable=True)
#     country_name = Column(String(100), nullable=True)
#     currency = Column(String(10), nullable=True)
#     timezone = Column(String(100), nullable=True)
#     primary_locale = Column(String(10), nullable=True)

#     # Plan information
#     plan_name = Column(String(50), nullable=True)
#     plan_display_name = Column(String(100), nullable=True)

#     # Domain information
#     primary_domain = Column(String(255), nullable=True)

#     # Installation tracking
#     installed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     uninstalled = Column(Boolean, default=False, nullable=False)
#     uninstalled_at = Column(DateTime, nullable=True)

#     # App-specific data
#     app_settings = Column(JSON, nullable=True, default={})
#     subscription_status = Column(String(20), default="trial", nullable=False)

#     # Timestamps
#     created_at = Column(DateTime, server_default=func.now(), nullable=False)
#     updated_at = Column(
#         DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
#     )

#     # Relationships
#     oauth_states = relationship(
#         "OAuthState", back_populates="shop", cascade="all, delete-orphan"
#     )
#     usage_records = relationship(
#         "ShopUsage", back_populates="shop", cascade="all, delete-orphan"
#     )

#     def __repr__(self):
#         return f"<Shop(domain='{self.shop_domain}', name='{self.shop_name}')>"


# class OAuthState(Base):
#     """OAuth state management for security"""

#     __tablename__ = "oauth_states"

#     id = Column(Integer, primary_key=True, index=True)
#     state = Column(String(255), unique=True, index=True, nullable=False)
#     shop_domain = Column(String(255), nullable=False)

#     # Timestamps
#     created_at = Column(DateTime, server_default=func.now(), nullable=False)
#     expires_at = Column(DateTime, nullable=True)  # Optional expiration

#     # Relationships
#     shop = relationship("Shop", back_populates="oauth_states")

#     def __repr__(self):
#         return f"<OAuthState(state='{self.state[:10]}...', shop='{self.shop_domain}')>"


# class ShopUsage(Base):
#     """Track API usage and metrics per shop"""

#     __tablename__ = "shop_usage"

#     id = Column(Integer, primary_key=True, index=True)
#     shop_domain = Column(String(255), ForeignKey("shops.shop_domain"), nullable=False)

#     # Usage metrics
#     metric_name = Column(
#         String(100), nullable=False
#     )  # 'api_calls', 'products_synced', etc.
#     metric_value = Column(Integer, default=0, nullable=False)
#     metric_data = Column(JSON, nullable=True)  # Additional metric data

#     # Timestamps
#     date = Column(DateTime, server_default=func.now(), nullable=False)
#     created_at = Column(DateTime, server_default=func.now(), nullable=False)

#     # Relationships
#     shop = relationship("Shop", back_populates="usage_records")

#     def __repr__(self):
#         return f"<ShopUsage(shop='{self.shop_domain}', metric='{self.metric_name}', value={self.metric_value})>"


# class WebhookEvent(Base):
#     """Track webhook events from Shopify"""

#     __tablename__ = "webhook_events"

#     id = Column(Integer, primary_key=True, index=True)
#     shop_domain = Column(String(255), ForeignKey("shops.shop_domain"), nullable=False)

#     # Webhook details
#     topic = Column(
#         String(100), nullable=False
#     )  # 'orders/create', 'app/uninstalled', etc.
#     webhook_id = Column(String(100), nullable=True)

#     # Event data
#     payload = Column(JSON, nullable=True)
#     headers = Column(JSON, nullable=True)

#     # Processing status
#     processed = Column(Boolean, default=False, nullable=False)
#     processed_at = Column(DateTime, nullable=True)
#     error_message = Column(Text, nullable=True)

#     # Timestamps
#     received_at = Column(DateTime, server_default=func.now(), nullable=False)

#     def __repr__(self):
#         return f"<WebhookEvent(shop='{self.shop_domain}', topic='{self.topic}', processed={self.processed})>"
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Shop(Base):
    """Shopify shop/store model"""

    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)

    # Core identification
    shop_domain = Column(String(255), unique=True, index=True, nullable=False)
    myshopify_domain = Column(String(255), nullable=True)

    # OAuth & API access
    access_token = Column(Text, nullable=True)  # Should be encrypted in production
    scopes = Column(String(500), nullable=True)

    # Shop information from Shopify API
    shop_name = Column(String(255), nullable=True)
    shop_email = Column(String(255), nullable=True)
    shop_owner = Column(String(255), nullable=True)

    # Location & settings
    country_code = Column(String(10), nullable=True)
    country_name = Column(String(100), nullable=True)
    currency = Column(String(10), nullable=True)
    timezone = Column(String(100), nullable=True)
    primary_locale = Column(String(10), nullable=True)

    # Plan information
    plan_name = Column(String(50), nullable=True)
    plan_display_name = Column(String(100), nullable=True)

    # Domain information
    primary_domain = Column(String(255), nullable=True)

    # Installation tracking
    installed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uninstalled = Column(Boolean, default=False, nullable=False)
    uninstalled_at = Column(DateTime, nullable=True)

    # App-specific data
    app_settings = Column(JSON, nullable=True, default={})
    subscription_status = Column(String(20), default="trial", nullable=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships - removed oauth_states relationship to break circular dependency
    usage_records = relationship(
        "ShopUsage", back_populates="shop", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Shop(domain='{self.shop_domain}', name='{self.shop_name}')>"


class OAuthState(Base):
    """OAuth state management for security - NO foreign key constraint"""

    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(255), unique=True, index=True, nullable=False)
    shop_domain = Column(String(255), nullable=False)  # REMOVED ForeignKey constraint

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # NO relationship back to Shop to avoid foreign key issues

    def __repr__(self):
        return f"<OAuthState(state='{self.state[:10]}...', shop='{self.shop_domain}')>"


class ShopUsage(Base):
    """Track API usage and metrics per shop"""

    __tablename__ = "shop_usage"

    id = Column(Integer, primary_key=True, index=True)
    shop_domain = Column(String(255), ForeignKey("shops.shop_domain"), nullable=False)

    # Usage metrics
    metric_name = Column(
        String(100), nullable=False
    )  # 'api_calls', 'products_synced', etc.
    metric_value = Column(Integer, default=0, nullable=False)
    metric_data = Column(JSON, nullable=True)  # Additional metric data

    # Timestamps
    date = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    shop = relationship("Shop", back_populates="usage_records")

    def __repr__(self):
        return f"<ShopUsage(shop='{self.shop_domain}', metric='{self.metric_name}', value={self.metric_value})>"


class WebhookEvent(Base):
    """Track webhook events from Shopify"""

    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    shop_domain = Column(String(255), ForeignKey("shops.shop_domain"), nullable=False)

    # Webhook details
    topic = Column(
        String(100), nullable=False
    )  # 'orders/create', 'app/uninstalled', etc.
    webhook_id = Column(String(100), nullable=True)

    # Event data
    payload = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)

    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    received_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<WebhookEvent(shop='{self.shop_domain}', topic='{self.topic}', processed={self.processed})>"
