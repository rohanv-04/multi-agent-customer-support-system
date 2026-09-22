# SupportOS AI — Production Readiness & Architecture Blueprint

## 1. System Architecture Overview

SupportOS AI is an enterprise-grade, autonomous multi-agent customer support operations platform designed with strict deterministic safety boundaries, autonomous action verification, and comprehensive auditability.

```mermaid
flowchart TB
    subgraph Inbound["Inbound Ingestion Layer"]
        WebChat["WebChat Widget"]
        Email["Email Provider (IMAP/SendGrid)"]
        WhatsApp["WhatsApp / Meta Webhook"]
        B2BAPI["Partner / B2B API"]
    end

    subgraph SecurityGateway["Edge & Security Layer"]
        CORS["Strict CORS Middleware"]
        AuthMiddleware["JWT Authentication & RBAC"]
        RateLimiter["Rate Limiting (120 req/min)"]
        ReqTracer["Request Correlation & Tracing (X-Request-ID)"]
    end

    subgraph CoreEngine["Multi-Agent Autonomous Engine"]
        Intake["Intake & Intent Agent"]
        C360["Customer 360 Intelligence Engine"]
        Investigator["Investigation Agent (DB & Order Tools)"]
        PolicyEngine["Policy Intelligence (RAG & Clause Matching)"]
        RiskEngine["Risk & Fraud Guardrails Engine"]
        DecisionEngine["Decision Matrix (Action Formulation)"]
        ActionGateway["Action Gateway & Idempotency Vault"]
        VerificationAgent["Post-Action Verification Agent"]
        Supervisor["Supervisor & Escalation Router"]
    end

    subgraph Storage["Persistent Data & Audit Layer"]
        RDBMS[("SQL Database (SQLite / Postgres)")]
        VectorStore[("Vector Store (Policy RAG)")]
        AuditLogStore[("Immutable Audit Vault & Traces")]
    end

    Inbound --> SecurityGateway
    SecurityGateway --> Intake
    Intake --> C360
    C360 --> Investigator
    Investigator --> PolicyEngine
    PolicyEngine --> RiskEngine
    RiskEngine --> DecisionEngine
    DecisionEngine --> ActionGateway
    ActionGateway --> VerificationAgent
    VerificationAgent --> Supervisor
    ActionGateway -.-> RDBMS
    PolicyEngine -.-> VectorStore
    Supervisor -.-> AuditLogStore
```

---

## 2. Deployment Requirements & Infrastructure

### 2.1 Hardware Sizing Recommendations
* **Minimum (Staging / Low-Volume < 50 req/min)**:
  * CPU: 2 vCPUs
  * RAM: 4 GB
  * Storage: 20 GB SSD
* **Production High-Throughput (> 500 req/min)**:
  * CPU: 4–8 vCPUs (horizontal scaling behind load balancer)
  * RAM: 8–16 GB
  * Storage: 100+ GB SSD (PostgreSQL cluster with read-replicas)

### 2.2 Process Management & Production Servers
* **ASGI Server**: Run with `uvicorn` workers managed by `gunicorn`:
  ```bash
  gunicorn backend.app.main:app \
      --workers 4 \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      --access-logfile - \
      --error-logfile - \
      --timeout 120
  ```
* **Reverse Proxy**: NGINX or Cloudflare terminating SSL, enforcing gzip/brotli compression, rate limiting, and forwarding `X-Forwarded-For` and `X-Request-ID`.

### 2.3 Docker & Containerization
* Multi-stage Dockerfile containing non-root execution user.
* Health & readiness probes mapped directly to `/health/live` and `/health/ready`.

---

## 3. Environment Variables Reference

| Variable Name | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `production` | Environment mode (`development`, `staging`, `production`) |
| `DEBUG` | Yes | `false` | Must remain `false` in production to prevent stack trace leaks |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ALLOWED_ORIGINS` | Yes | Explicit domains | Comma-delimited list of exact allowed CORS origins |
| `DATABASE_URL` | Yes | `sqlite:///./novacart.db` | Connection string (`postgresql://user:pass@host:5432/db`) |
| `JWT_SECRET_KEY` | Yes | - | 256-bit cryptographically secure secret key |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `RATE_LIMIT_PER_MINUTE` | No | `120` | Max requests per IP/tenant per minute |
| `LLM_PROVIDER` | No | `openai` | AI backend (`openai`, `groq`, `openrouter`, or `local`) |
| `LLM_API_KEY` | Conditional | - | API key for external LLM provider |
| `AUTO_REFUND_LIMIT` | No | `500.00` | Max dollar amount eligible for autonomous action without human approval |
| `SUPERVISOR_APPROVAL_THRESHOLD` | No | `500.00` | Action threshold requiring tier-2 supervisor sign-off |
| `SENSITIVE_DATA_REDACTION` | No | `true` | Enables regex-based masking for PII, emails, tokens, and credit cards |

---

## 4. Security Hardening & Controls

1. **Zero Secret Exposure**:
   - Secrets and keys are strictly read from environment variables; never hardcoded in source.
   - `.env` is explicitly ignored in `.gitignore`.
2. **PII and Sensitive Log Masking**:
   - `backend/app/core/logging.py` implements an active `SensitiveDataFilter` redacting credit card PANs, bearer tokens, JWTs, and email addresses from logs.
3. **Strict CORS Policy**:
   - Wildcard `*` CORS origins are rejected in production; only explicit whitelisted client origins are accepted.
4. **Role-Based Access Control (RBAC)**:
   - Granular authorization roles (`customer`, `agent`, `supervisor`, `admin`).
   - Sensitive financial and data-mutation endpoints enforce role validation via `@require_role`.
5. **Database Transaction Safety**:
   - All mutations in Action Gateway and tools execute inside scoped transactions with automatic rollback on error.
6. **Idempotency & Deduplication**:
   - `DeduplicationRegistry` hashes incoming webhook payloads and correlates client request IDs to prevent replay attacks or double-billing.

---

## 5. Health, Readiness & Observability

### 5.1 Endpoints
* **`GET /health`**: High-level system status, application uptime, active request ID.
* **`GET /health/live`**: Kubernetes liveness probe (returns 200 if ASGI loop is responsive).
* **`GET /health/ready`**: Kubernetes readiness probe (validates DB read/write connectivity and vector store index initialization; returns 503 if dependencies are unready).

### 5.2 Distributed Tracing & Correlation
* Every incoming HTTP request is assigned a unique `X-Request-ID` (or adopts incoming header) injected into Python `contextvars`.
* Logs and audit events automatically propagate `request_id` and `org_id` across asynchronous spans.
* Execution latency is measured and returned in `X-Response-Time-Ms`.

### 5.3 Prometheus & Metrics
* Metrics exposed on `/api/observability/metrics`:
  * `cases_total`, `cases_resolved_autonomous`, `cases_escalated`
  * `sla_breach_rate`, `sla_average_resolution_seconds`
  * `actions_executed_total`, `actions_verified_total`, `actions_failed_total`
  * `eval_accuracy_score`, `eval_hallucination_rate`, `eval_policy_compliance_rate`

---

## 6. Backup, Recovery & Disaster Considerations

1. **Database Backups**:
   - Continuous WAL archiving / Point-in-Time Recovery (PITR) for PostgreSQL.
   - Daily automated logical snapshots (`pg_dump`) retained for 30 days in off-site encrypted object storage (e.g. AWS S3 / GCS with Object Lock).
2. **Recovery Objectives**:
   - **RPO (Recovery Point Objective)**: < 5 minutes.
   - **RTO (Recovery Time Objective)**: < 15 minutes for complete automated container redeployment.
3. **Vector Store Persistence**:
   - Policy markdown files in `data/policies/` serve as the source of truth, re-indexed in < 2 seconds during application startup.

---

## 7. Known Limitations & Scaling Strategy

1. **Single-Node In-Memory Vector Store**:
   - Current implementation uses an optimized in-memory NumPy/cosine vector store with fast startup re-indexing.
   - *Scale pathway*: For > 100,000 policy documents, configure PGVector or Qdrant cluster backend.
2. **Ephemeral Deduplication Registry**:
   - Memory-based deduplication cache with 1-hour TTL.
   - *Scale pathway*: For multi-instance distributed deployments, configure Redis as the shared deduplication store.
3. **Synchronous Tool Fallback**:
   - Local deterministic fallback operates synchronously when external LLM endpoints experience outages.
   - *Scale pathway*: Celery or ARQ background queue for asynchronous heavy batch processing.
