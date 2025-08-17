# 🚀 Shopify FastAPI App - Complete Setup Guide

This guide will walk you through setting up a production-ready Shopify app with FastAPI, PostgreSQL, and Alembic.

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Shopify Partner Account
- ngrok (for development)

## 🛠️ Step 1: Project Setup

### 1.1 Clone and Setup Directory

```bash
# Create project directory
mkdir shopify-app
cd shopify-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Create Project Structure

```
shopify-app/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── config.py
│   ├── security.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── webhooks.py
│   │   └── shops.py
│   └── utils/
│       ├── __init__.py
│       ├── oauth.py
│       └── shopify_api.py
├── alembic/
├── requirements.txt
├── .env
└── README.md
```

## 🗄️ Step 2: Database Setup

### 2.1 Install PostgreSQL

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS:**

```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download from [PostgreSQL.org](https://www.postgresql.org/download/windows/)

### 2.2 Create Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE shopify_app;
CREATE USER shopify_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE shopify_app TO shopify_user;
\q
```

### 2.3 Configure Environment

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://shopify_user:your_password@localhost:5432/shopify_app

# Shopify App Credentials (get from Partner Dashboard)
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
SHOPIFY_SCOPES=read_products,write_products,read_orders

# App Configuration
APP_URL=https://your-domain.ngrok-free.app
ENVIRONMENT=development

# Security
SECRET_KEY=your-very-secure-secret-key-change-in-production

# CORS
ALLOWED_ORIGINS=https://admin.shopify.com,https://*.myshopify.com
```

## 🔄 Step 3: Database Migrations

### 3.1 Initialize Alembic

```bash
# Initialize Alembic (already done in this setup)
alembic init alembic

# Generate initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 3.2 Verify Database

```bash
# Connect to database
psql postgresql://shopify_user:your_password@localhost:5432/shopify_app

# List tables
\dt

# Should see: shops, oauth_states, shop_usage, webhook_events
```

## 🛡️ Step 4: Shopify Partner Dashboard Setup

### 4.1 Create Shopify App

1. Go to [partners.shopify.com](https://partners.shopify.com)
2. Click "Create app" → "Create app manually"
3. Enter app name and select "Custom app"

### 4.2 Configure App URLs

In your app settings:

- **App URL**: `https://your-domain.ngrok-free.app`
- **Allowed redirection URL(s)**: `https://your-domain.ngrok-free.app/auth/callback`
- **Webhook URL**: `https://your-domain.ngrok-free.app/webhooks/shopify`

### 4.3 Set App Scopes

Configure the scopes your app needs:

- `read_products`
- `write_products` (if needed)
- `read_orders` (if needed)

### 4.4 Get API Credentials

Copy from your app dashboard:

- **API key** → `SHOPIFY_API_KEY`
- **API secret** → `SHOPIFY_API_SECRET`

## 🌐 Step 5: Development Server Setup

### 5.1 Install ngrok

```bash
# Download from ngrok.com or install via package manager
npm install -g ngrok
# OR
brew install ngrok
```

### 5.2 Start ngrok

```bash
# Start ngrok tunnel
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
# Update your .env file with this URL
```

### 5.3 Start Development Server

```bash
# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Server will be available at:
# - Local: http://localhost:8000
# - ngrok: https://abc123.ngrok-free.app
```

## 🧪 Step 6: Testing the Installation

### 6.1 Test Basic Endpoints

```bash
# Test root endpoint
curl https://your-domain.ngrok-free.app/

# Test health check
curl https://your-domain.ngrok-free.app/health

# View API docs
open https://your-domain.ngrok-free.app/docs
```

### 6.2 Test OAuth Installation

1. Create a development store in your Partner Dashboard
2. Use the install URL:
   ```
   https://your-domain.ngrok-free.app/auth/install?shop=your-dev-store.myshopify.com
   ```
3. Complete the OAuth flow
4. Verify installation success

### 6.3 Test Admin Endpoints

```bash
# List installed shops
curl https://your-domain.ngrok-free.app/api/admin/shops

# Get platform stats
curl https://your-domain.ngrok-free.app/api/admin/stats

# Get shop details
curl https://your-domain.ngrok-free.app/api/shops/your-dev-store.myshopify.com
```

## 🔗 Step 7: Webhook Setup

### 7.1 Configure Webhooks in Partner Dashboard

Add webhook endpoints:

- **URL**: `https://your-domain.ngrok-free.app/webhooks/shopify`
- **Events**:
  - `app/uninstalled`
  - `orders/create`
  - `products/update`

### 7.2 Test Webhooks

```bash
# List webhook events
curl https://your-domain.ngrok-free.app/webhooks/events

# Test uninstall (uninstall app from test store)
# Check webhook events to see if processed
```

## 📊 Step 8: Multi-Shop Testing

### 8.1 Install on Multiple Shops

Create multiple development stores and install your app:

```bash
# Install on shop 1
https://your-domain.ngrok-free.app/auth/install?shop=shop1.myshopify.com

# Install on shop 2
https://your-domain.ngrok-free.app/auth/install?shop=shop2.myshopify.com
```

### 8.2 Test Multi-Shop Features

```bash
# List all shops
curl https://your-domain.ngrok-free.app/api/admin/shops

# Get bulk products
curl https://your-domain.ngrok-free.app/api/admin/bulk/products

# Get usage analytics
curl https://your-domain.ngrok-free.app/api/admin/usage
```

## 🚀 Step 9: Production Deployment

### 9.1 Environment Setup

Create production `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/shopify_app
APP_URL=https://your-production-domain.com
ENVIRONMENT=production
SECRET_KEY=very-secure-production-key
SHOPIFY_API_KEY=your_production_api_key
SHOPIFY_API_SECRET=your_production_api_secret
```

### 9.2 Deploy Options

**Option 1: Docker**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Option 2: Railway/Heroku**

```bash
# Add Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy to Railway
railway login
railway new
railway add
railway deploy
```

**Option 3: VPS/Cloud**

```bash
# Use systemd service
sudo systemctl enable shopify-app
sudo systemctl start shopify-app
```

### 9.3 Production Database

```bash
# Run migrations on production
alembic upgrade head

# Set up database backups
pg_dump shopify_app > backup.sql
```

## 🔧 Step 10: Advanced Configuration

### 10.1 SSL/HTTPS Setup

```bash
# Using Let's Encrypt with nginx
sudo certbot --nginx -d your-domain.com
```

### 10.2 Monitoring Setup

```python
# Add to main.py
import logging
logging.basicConfig(level=logging.INFO)

# Use tools like:
# - Sentry for error tracking
# - Prometheus for metrics
# - Grafana for dashboards
```

### 10.3 Security Hardening

```python
# Add security headers
from fastapi.middleware.trustedhost import TrustedHostMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["your-domain.com"])

# Add rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
```

## 🐛 Troubleshooting

### Common Issues

**1. Database Connection Error**

```bash
# Check database status
sudo systemctl status postgresql

# Check connection
psql postgresql://user:pass@localhost:5432/shopify_app
```

**2. OAuth HMAC Verification Failed**

- Check `SHOPIFY_API_SECRET` is correct
- Ensure URL in Partner Dashboard matches exactly
- Verify no trailing slashes in URLs

**3. Webhook Signature Invalid**

- Check webhook URL in Partner Dashboard
- Verify `SHOPIFY_API_SECRET` matches

**4. Products API 403 Error**

- Verify shop is installed (`/api/admin/shops`)
- Check access token is not null
- Verify scopes include `read_products`

## 📚 Next Steps

1. **Add Frontend**: Build React/Vue app for embedded interface
2. **Add Authentication**: Implement shop-specific authentication
3. **Add Features**: Build your app's core functionality
4. **Add Tests**: Write comprehensive test suite
5. **Add Monitoring**: Set up logging and alerts
6. **Submit for Review**: Apply for Shopify App Store approval

## 🎯 Quick Commands Reference

```bash
# Development
uvicorn app.main:app --reload
ngrok http 8000

# Database
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Production
docker build -t shopify-app .
docker run -p 8000:8000 shopify-app

# Testing
curl https://your-domain.ngrok-free.app/health
curl https://your-domain.ngrok-free.app/api/admin/shops
```

## 🆘 Support

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Shopify API Docs**: https://shopify.dev/api
- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/

---

**Your clean, production-ready Shopify app is now ready to scale! 🎉**
