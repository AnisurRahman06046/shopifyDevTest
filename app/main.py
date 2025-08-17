from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import create_tables
from app.routes.auth import router as auth_router
from app.routes.webhooks import router as webhook_router
from app.routes.shops import router as shops_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting Shopify FastAPI App")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"App URL: {settings.app_url}")

    # Create database tables (in production, use Alembic migrations)
    if settings.environment == "development":
        logger.info("Creating database tables...")
        await create_tables()

    yield

    # Shutdown
    logger.info("Shutting down Shopify FastAPI App")


# Create FastAPI app
app = FastAPI(
    title="Shopify Multi-Shop App",
    description="A production-ready Shopify app supporting multiple shops",
    version="1.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom HTTP exception handler
    """
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url.path),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions
    """
    logger.error(f"Unexpected error: {exc} - {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": str(request.url.path),
        },
    )


# Include routers
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(shops_router)


# Root endpoints
@app.get("/")
async def root():
    """
    Root endpoint with app information
    """
    return {
        "app": "Shopify Multi-Shop App",
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "running",
        "endpoints": {
            "install": f"{settings.app_url}/auth/install?shop={{shop}}.myshopify.com",
            "docs": (
                f"{settings.app_url}/docs"
                if settings.environment == "development"
                else None
            ),
            "admin_dashboard": f"{settings.app_url}/api/admin/shops",
            "platform_stats": f"{settings.app_url}/api/admin/stats",
        },
        "features": [
            "OAuth 2.0 authentication",
            "Multi-shop support",
            "Webhook handling",
            "Usage analytics",
            "Admin dashboard",
            "Bulk operations",
        ],
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "environment": settings.environment,
        "timestamp": "2025-01-17T12:00:00Z",
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """
    Simple admin dashboard
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=404, detail="Dashboard not available in production"
        )

    return HTMLResponse(
        content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Shopify App Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa;
                color: #333;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }}
            .card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .card h3 {{
                margin-top: 0;
                color: #007bff;
            }}
            .endpoint {{
                background: #f8f9fa;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }}
            .button {{
                display: inline-block;
                background: #007bff;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 4px;
                margin: 5px;
            }}
            .button:hover {{
                background: #0056b3;
            }}
            .status {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            .status.running {{
                background: #d4edda;
                color: #155724;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏪 Shopify Multi-Shop App Dashboard</h1>
                <p>Environment: <strong>{settings.environment}</strong></p>
                <p>App URL: <code>{settings.app_url}</code></p>
                <span class="status running">● Running</span>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>🔐 Authentication</h3>
                    <p>Install your app on any Shopify store:</p>
                    <div class="endpoint">
                        GET {settings.app_url}/auth/install?shop={{shop}}.myshopify.com
                    </div>
                    <a href="{settings.app_url}/auth/install?shop=example.myshopify.com" class="button">Test Install Flow</a>
                </div>
                
                <div class="card">
                    <h3>📊 Admin APIs</h3>
                    <p>Manage and monitor all connected shops:</p>
                    <div class="endpoint">GET {settings.app_url}/api/admin/shops</div>
                    <div class="endpoint">GET {settings.app_url}/api/admin/stats</div>
                    <a href="{settings.app_url}/api/admin/shops" class="button">View Shops</a>
                    <a href="{settings.app_url}/api/admin/stats" class="button">View Stats</a>
                </div>
                
                <div class="card">
                    <h3>🔗 Webhooks</h3>
                    <p>Handle Shopify webhooks:</p>
                    <div class="endpoint">POST {settings.app_url}/webhooks/shopify</div>
                    <div class="endpoint">GET {settings.app_url}/webhooks/events</div>
                    <a href="{settings.app_url}/webhooks/events" class="button">View Events</a>
                </div>
                
                <div class="card">
                    <h3>🛍️ Shop APIs</h3>
                    <p>Access shop-specific data:</p>
                    <div class="endpoint">GET {settings.app_url}/api/products?shop={{shop}}</div>
                    <div class="endpoint">GET {settings.app_url}/api/shops/{{shop}}</div>
                    <a href="{settings.app_url}/api/admin/bulk/products" class="button">Bulk Products</a>
                </div>
                
                <div class="card">
                    <h3>📈 Analytics</h3>
                    <p>Usage and performance metrics:</p>
                    <div class="endpoint">GET {settings.app_url}/api/admin/usage</div>
                    <a href="{settings.app_url}/api/admin/usage" class="button">View Usage</a>
                </div>
                
                <div class="card">
                    <h3>📚 Documentation</h3>
                    <p>API documentation and testing:</p>
                    <a href="{settings.app_url}/docs" class="button">Swagger UI</a>
                    <a href="{settings.app_url}/redoc" class="button">ReDoc</a>
                    <a href="{settings.app_url}/health" class="button">Health Check</a>
                </div>
            </div>
            
            <div class="card">
                <h3>🚀 Quick Start</h3>
                <ol>
                    <li>Configure your <code>.env</code> file with Shopify app credentials</li>
                    <li>Set up your Shopify Partner Dashboard with the correct URLs</li>
                    <li>Start installing the app on test shops using the install URL</li>
                    <li>Monitor installations and usage through the admin endpoints</li>
                    <li>Set up webhooks to handle app uninstalls and other events</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """
    )


# Development endpoints
if settings.environment == "development":

    @app.get("/dev/test-install")
    async def test_install_page():
        """Development helper for testing installations"""
        return HTMLResponse(
            content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test App Installation</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                input {{ padding: 10px; margin: 10px 0; width: 100%; box-sizing: border-box; }}
                button {{ background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <h1>Test App Installation</h1>
            <p>Enter a shop domain to test the installation flow:</p>
            <form onsubmit="startInstall(event)">
                <input type="text" id="shopDomain" placeholder="example.myshopify.com" required>
                <button type="submit">Start Installation</button>
            </form>
            
            <script>
                function startInstall(event) {{
                    event.preventDefault();
                    const shop = document.getElementById('shopDomain').value;
                    const url = `{settings.app_url}/auth/install?shop=${{shop}}`;
                    window.location.href = url;
                }}
            </script>
        </body>
        </html>
        """
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
    )
