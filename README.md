# Atlas · Auth Service 🔐

> Parte do **Projeto Atlas** — plataforma acadêmica desenvolvida para o **IFRN Campus Pau dos Ferros** como Projeto Integrador de Sistemas Distribuídos. O Atlas conecta alunos a trilhas de conhecimento e bolsas, com avaliação automática de código por IA.

Microsserviço responsável pela **identidade** do ecossistema: login via **SUAP (OAuth2)**, emissão e validação de **JWT** e gestão dos perfis de usuário. É a fonte de verdade sobre quem é o usuário e qual o seu papel (aluno ou professor).

## O que este serviço faz

- **Login SUAP (OAuth2):** gera a URL de autorização e processa o callback, criando/atualizando o usuário a partir dos dados do SUAP.
- **Sessão JWT:** emite `access` (60 min) e `refresh`, com rotação e *blacklist* do refresh no logout.
- **Claims ricos no token:** além do `user_id`, o JWT carrega `role`, `is_staff`, `ira`, `period` e `email`, consumidos localmente pelos demais serviços (validação *stateless*, sem bater no auth a cada request).
- **Validação de borda:** expõe `internal/validate/`, consumido pelo Nginx via `auth_request` para autenticar requisições antes de repassá-las e injetar `X-User-Id` / `X-User-Role`.
- **Perfis:** consulta do próprio perfil, busca de perfis, resolução **em lote** por UUID (evita N+1) e consulta por matrícula.
- **Produtor de notificações:** publica o evento `notifications.create` no RabbitMQ (não roda worker próprio).
- **Auditoria:** modelo `AuditLog` com registro automático de operações e endpoint de consulta.

## Stack

- Python · Django 4.2 · Django REST Framework
- SimpleJWT (rotação + blacklist) · OAuth2 (SUAP)
- PostgreSQL 16 (schema `auth`) · Redis · RabbitMQ (Celery, apenas produtor)
- Gunicorn · Docker · drf-spectacular (Swagger)

> **Nota histórica:** a comunicação interna que antes usava um servidor **gRPC** (`GetUserProfile`) foi migrada para **HTTP/JWT**. O gRPC não faz mais parte do serviço.

## Como se encaixa no Atlas

| Repositório | Responsabilidade |
|---|---|
| **atlas-auth-service** | **Identidade: SUAP OAuth2, JWT, perfis de usuário** |
| atlas-track-service | Trilhas, módulos, conteúdos, progresso e submissão de desafios |
| atlas-scholarship-service | Bolsas, candidaturas, banco de talentos e notas |
| atlas-feed-service | Feed institucional: posts, comentários, curtidas e banners |
| atlas-notification-service | Notificações (consumidor central via RabbitMQ) |
| atlas-ai-service | Avaliação de repositórios GitHub por LLM local (Ollama) |
| atlas-frontend | SPA React + TypeScript (aluno e professor) |
| atlas-infra | Docker Compose, Nginx (gateway), Postgres/Redis/RabbitMQ, deploy e backup |
| atlas-observability | Prometheus + Grafana (métricas dos serviços) |

**Fluxo de autenticação:** o usuário faz login pelo SUAP → o auth-service emite o JWT → o **Nginx** valida o token na borda (`auth_request` → `internal/validate/`) e injeta os headers de identidade → cada serviço *downstream* também valida o JWT localmente para ler os claims (`role`, `ira`, etc.) sem novas chamadas de rede.

## Principais endpoints (`/api/auth/`)

| Método | Rota | Descrição |
|---|---|---|
| GET | `suap/login/` | URL de autorização do SUAP |
| GET/POST | `suap/callback/` | Callback OAuth2 → emite JWT |
| POST | `refresh/` | Renova o access token |
| POST | `logout/` | Invalida o refresh (blacklist) |
| GET | `me/` · `users/me/` | Perfil do usuário autenticado |
| GET | `users/search/` | Busca de perfis |
| POST | `users/batch/` | Resolução de perfis em lote por UUID |
| GET | `users/<matricula>/` | Perfil por matrícula |
| GET | `audit-logs/` | Relatório de auditoria |
| — | `internal/validate/` | Validação interna (uso exclusivo do Nginx) |
| GET | `api/auth/docs/` | Documentação Swagger/OpenAPI |
| GET | `metrics/` | Métricas Prometheus |

## Estrutura

```
apps/authentication/   models, views, serializers, signals, middleware, audit, notifications
config/                settings (base/local/production), urls, asgi, wsgi, celery
docs/                  DER e diagramas
```

## Executando localmente

Este serviço é orquestrado junto com os demais pelo repositório central de infraestrutura:

> **[Atlas-IFRN/atlas-infra](https://github.com/Atlas-IFRN/atlas-infra)** — Docker Compose canônico, Nginx, deploy e backup.

Para rodar isolado em modo dev (com a infra compartilhada de pé):

```bash
# 1. Suba a infra compartilhada (Postgres, Redis, RabbitMQ)
git clone https://github.com/Atlas-IFRN/atlas-infra
cd atlas-infra && docker compose -f docker-compose.dev.yml up -d

# 2. Neste repositório
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

## Variáveis de ambiente

Baseie seu `.env` no `.env.example`. Principais: `DJANGO_SECRET_KEY` (**compartilhada** entre os serviços — é a chave de assinatura do JWT), `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `SUAP_CLIENT_ID`, `SUAP_CLIENT_SECRET`, `SUAP_REDIRECT_URI`.

## Observabilidade & Auditoria

- **Métricas:** endpoint `/metrics` (django-prometheus) coletado pelo [atlas-observability](https://github.com/Atlas-IFRN/atlas-observability).
- **Auditoria:** `AuditLog` registra automaticamente as operações relevantes com `user_id` e timestamp, consultáveis via `audit-logs/`.

## CI/CD

Workflows de GitHub Actions em `.github/workflows/` (lint, testes e apoio ao deploy).
