# Vnext Web Services

A modern multi-tenant web services platform built with FastAPI, implementing Clean Architecture principles with comprehensive authentication and extensible notification system.

## 🏗️ Architecture

### Tech Stack
- **Language**: Python 3.13 with full type safety
- **API Framework**: FastAPI with async/await throughout
- **ORM**: SQLAlchemy + Alembic migrations
- **Database**: PostgreSQL 17 with pgvector extension
- **Cache/Queue**: Redis 7 with ARQ for async background tasks
- **Monitoring**: Sentry for error tracking and performance monitoring
- **Architecture**: Clean Architecture with Domain-Driven Design (DDD)
- **Development**: Docker-based environment with hot reload

### Project Structure
```
src/
├── auth/              # JWT + OAuth authentication system
├── common/            # Shared infrastructure, domain entities, database models
│   ├── database/      # Database models
│   ├── domain/        # Base entities, value objects, enums
│   └── infrastructure/# Message buses, middleware, contexts
├── me/                # Current user endpoints and profile management
├── tenants/           # Multi-tenant architecture with branches & POS
├── users/             # User registration and management
└── notifications/     # Email service (implemented) + future channels
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Make (for command shortcuts)
- Python 3.13+ (for local development)

### Setup
```bash
# Clone repository
git clone https://github.com/llamitai/vnext-ws.git
cd backend

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Build and start services
make build
make up

# Run database migrations
make migrate

# Access the API documentation
open http://localhost/docs
```

### Service URLs
- **API Documentation (Swagger)**: http://localhost/docs
- **API (ReDoc)**: http://localhost/redoc
- **Email Testing (Mailpit)**: http://localhost:8025
- **MinIO Console**: http://localhost:9001
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🛠️ Development

### Essential Commands
```bash
# Development environment
make up          # Start all services
make down        # Stop all services
make bash        # Access API container shell
make logs        # View all logs
make logs SERVICE=api  # View specific service logs
make clean       # Clean containers and volumes

# Database operations (Alembic)
make migrate               # Apply all pending migrations
make migrations ARG="msg"  # Create new migration
make db_current            # Show current migration version
make db_history            # Show migration history
make downgrade             # Rollback one migration

# Code quality (ALWAYS run before commits)
make format      # Auto-format with ruff
make lint        # Lint with ruff
make tycheck     # Type check with ty (strict mode)
make test        # Run pytest suite

# Combined quality check
make format && make lint && make tycheck
```

### Development Workflow
1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Implement following Clean Architecture**: See CLAUDE.md for patterns
3. **Run quality checks**: `make format && make lint && make tycheck`
4. **Write tests**: Follow existing patterns in tests/
5. **Test locally**: Use Swagger UI at http://localhost/docs
6. **Create PR**: Ensure all checks pass

## 🔐 Authentication & Authorization

### Implemented Features
- **JWT Authentication**: Access (30min) + Refresh (7 days) tokens
- **Google OAuth**: Complete OAuth2 flow with user creation
- **Email/Password**: Traditional authentication with password reset
- **Session Management**: GET /v1/auth/session endpoint
- **Multi-tenant Support**: Users can belong to multiple tenants

### Key Endpoints
```bash
# Authentication
POST   /v1/auth/login           # Email/password login
POST   /v1/auth/google-login    # Google OAuth initiation
POST   /v1/auth/refresh-token   # Refresh access token
POST   /v1/auth/reset-password  # Password reset request
GET    /v1/auth/session         # Current session info

# Current User
GET    /v1/me/profile          # Get user profile
PUT    /v1/me/profile          # Update profile
PUT    /v1/me/password         # Change password
GET    /v1/me/tenants          # List user's tenants
PUT    /v1/me/tenants/{id}     # Switch active tenant

# User Management
POST   /v1/users/              # Register new user

# Tenants
POST   /v1/tenants/            # Create new tenant
```

## 🏢 Multi-Tenant Architecture

### Tenant Hierarchy
```
Tenant (Company/Organization)
├── TenantUser         # User memberships
├── TenantBranch       # Physical locations/offices
│   ├── TenantBranchUser  # Staff assignments
│   └── TenantPOS         # Point of sale terminals
└── TenantBankAccount  # Banking information
```

### Key Features
- Complete data isolation via tenant_id
- User can belong to multiple tenants
- Tenant switching functionality
- Branch and POS management

## 📧 Notification System

### Currently Implemented
- **Email Service**: SMTP-based email sending
- **Template System**: Email templates (password reset implemented)
- **Command Bus Integration**: Async email sending

### Planned Channels
- SMS notifications
- WhatsApp Business API
- Push notifications
- In-app notifications

## 📊 Monitoring & Error Tracking

### Sentry Integration
Comprehensive error tracking and performance monitoring with Sentry:

**Features:**
- Automatic error capture with full stack traces
- Performance monitoring for API endpoints
- Database query performance tracking (SQLAlchemy)
- Redis operations monitoring
- Request/response context capture
- Custom event filtering and tagging

**Setup:**
```bash
# 1. Get your Sentry DSN from https://sentry.io
# 2. Add to .env
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENVIRONMENT=dev
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_SEND_DEFAULT_PII=True

# 3. Test the integration
curl http://localhost/sentry-debug
```

**Key Configuration:**
- **Integrations**: FastAPI, Starlette, Redis, SQLAlchemy
- **Transaction Style**: Endpoint-based (function names)
- **Failed Status Codes**: 403 and 5xx errors
- **Event Filtering**: Health checks automatically excluded
- **Release Tracking**: Tagged with app version
- **Environment Aware**: Only active in non-local environments

For detailed configuration, see `config/monitoring.py` and CLAUDE.md.

## 🧪 Testing

### Current Status
⚠️ **Test coverage is very low (~5%)** - This is a priority area for improvement

### Test Structure
```bash
# Run all tests
make test

# Run with coverage
make test ARG="--cov=src --cov-report=html"

# Run specific module
make test ARG="src/auth/tests/"

# Run specific test
make test ARG="-k test_google_login"
```

### Testing Guidelines
- Write tests for all new features
- Use pytest with async support
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test data
- Mock external dependencies

## 📊 Database Management

### Current Schema Highlights
```sql
-- Multi-tenant base
tenant_id UUID NOT NULL  -- On most tables

-- Soft deletes
deleted_at TIMESTAMP     -- NULL = active

-- Audit fields
created_at TIMESTAMP NOT NULL
updated_at TIMESTAMP NOT NULL
```

### Migration Commands
```bash
# Create new migration
make migrations ARG="add invoice tables"

# Apply migrations
make migrate

# Rollback one migration
make downgrade

# View migration SQL
alembic show <revision_id>
```

## 🚦 Code Quality Standards

### Requirements
- **Type Safety**: All functions must have type hints
- **Async/Await**: All endpoints and repositories use async
- **Clean Architecture**: Strict layer separation
- **No Framework Coupling**: Domain layer is framework-agnostic
- **Error Handling**: Custom exceptions with proper HTTP mapping

### Pre-commit Checklist
```bash
# 1. Format code
make format

# 2. Fix linting issues
make lint

# 3. Fix type errors
make tycheck

# 4. Run tests
make test

# 5. Check migrations
make migrate
```

## 🚀 Production Deployment

### Environment Configuration
Production requires additional environment variables:

```bash
# Core Settings
DEBUG=False
ENVIRONMENT=production
SERVER_CONFIG=production

# Security
JWT_SECRET_KEY=<strong-secret>
CORS_ORIGINS=["https://app.vnext.com"]

# Database (Production)
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Redis (Production)
REDIS_URL=redis://user:pass@host:6379

# Email (Production SMTP)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=<sendgrid-api-key>

# Monitoring
SENTRY_DSN=https://key@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_SEND_DEFAULT_PII=False
```

### Deployment with GitHub Actions
The project includes GitHub Actions workflows for CI/CD. Required secrets:

```yaml
# Repository Variables
PORTAINER_URL
DEPLOYMENT_REPOSITORY_URI
DEPLOYMENT_SERVICE
PROJECT_ID

# Repository Secrets  
PORTAINER_TOKEN
INFISICAL_MACHINE_CLIENT_ID
INFISICAL_MACHINE_CLIENT_SECRET
```

## 🗺️ Implementation Roadmap

### ✅ Fully Implemented
- JWT authentication with refresh tokens
- Google OAuth integration
- Email/password authentication
- Password reset with email
- User profiles and management
- Multi-tenant foundation with switching
- Clean Architecture with DDD
- CQRS with command/query buses
- Repository pattern
- Email service with templates
- Docker development environment
- Sentry integration for error tracking and performance monitoring
- File storage with MinIO/S3 compatibility

### 🚧 In Progress
- Background task workers (ARQ configured)
- Test coverage improvement

### 📋 Not Yet Implemented
- WhatsApp Business API
- SMS notifications
- AI/LLM features (pgvector ready)
- WebSocket support
- Full-text search
- Advanced rate limiting
- API versioning
- Advanced caching strategies

## 🤝 Contributing

### For AI Agents (Claude Code)
See **CLAUDE.md** for detailed implementation patterns and examples. Key files:
- `CLAUDE.md` - Main AI agent guide
- `.claude/` - Detailed documentation by topic

### Code Standards
1. **Architecture**: Follow Clean Architecture strictly
2. **Types**: Use Python 3.13 type hints everywhere
3. **Async**: All I/O operations must be async
4. **Tests**: Write tests for new features
5. **Docs**: Update OpenAPI descriptions

### Pull Request Process
1. Branch from `main` or `dev`
2. Follow existing patterns (see examples in codebase)
3. Ensure `make format && make lint && make tycheck` passes
4. Write/update tests
5. Update documentation if needed
6. Create PR with clear description

## 🐛 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check PostgreSQL is running
docker compose ps

# Check connection
make bash
python -c "from src.common.infrastructure.database import get_db_session"
```

**Type Errors**
```bash
# See specific errors
make tycheck

# Common fix: Add type hints
def process_order(quantity: int, product_id: str) -> Order:
```

**Migration Conflicts**
```bash
# Check current version
make db_current

# Resolve conflicts
make downgrade  # If needed
make migrate
```

**Redis Connection Issues**
```bash
# Test Redis
make bash
python -c "import redis; r = redis.Redis(host='redis'); r.ping()"
```

## Minio Local Config

```bash
# Configurar Bucket
# e.g. mc alias set doxiq_local https://assets.vnext.tech CLIENT_ID SECRET_KEY
mc alias set doxiq_local http://localhost:9000 minioadmin minioadmin  # Config Alias
mc mb doxiq_local/vnext-ws  # Crear bucket
mc anonymous set public doxiq_local/vnext-ws # Configurar bucket como público
mc anonymous set download doxiq_local/vnext-ws  # Solo lectura

mc anonymous set upload doxiq_local/vnext-ws  # Lectura y escritura

# Verificar configuración
mc anonymous get doxiq_local/vnext-ws
mc ls doxiq_local/vnext-ws/
```

## 📚 Documentation

### Project Documentation
- [CLAUDE.md](AGENTS.md) - AI agent development guide
- [Project Overview](.claude/01-project-overview.md)
- [Architecture Guide](.claude/02-architecture.md)
- [Development Guide](.claude/03-development-guide.md)
- [API Conventions](.claude/04-api-conventions.md)
- [Database Models](.claude/05-database-models.md)
- [Testing Guide](.claude/06-testing-guide.md)
- [Implementation Status](.claude/09-implementation-status.md)

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)

## 📧 Support

For questions or issues:
- Create a GitHub issue
- Contact: support@llamitai.com

---

**Note**: This is an active development project. Features and APIs may change. Always refer to the latest documentation and use semantic versioning for production deployments.