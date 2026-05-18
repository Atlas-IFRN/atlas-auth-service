# Atlas Auth Service 🔐

Microserviço de autenticação do ecossistema **ATLAS**, desenvolvido com **Django** + **Django REST Framework** e integrado ao **SUAP** (OAuth2). O serviço roda em **Docker** com **PostgreSQL** e entrega autenticação baseada em **JWT**.

## Principais Funcionalidades

- Login via SUAP (gera URL de autorização e processa o callback)
- Emissão de tokens **JWT** (`access` e `refresh`) via **SimpleJWT**
- Renovação de sessão (`refresh`) e logout com blacklist do refresh token
- Modelo de usuário customizado (UUID, CPF, matrícula e campos acadêmicos/perfil)

## Stack

- Python 3.11
- Django 4.2
- Django REST Framework
- SimpleJWT (com rotação e blacklist)
- PostgreSQL
- Docker / Docker Compose

## Estrutura do Projeto

- `apps/`: apps do Django (ex.: `apps.authentication`)
- `config/`: configuração do projeto (settings/urls/asgi/wsgi)
- `docs/`: documentação técnica e diagramas

## Modelagem de Dados (DER)

O banco foi modelado para suportar autenticação integrada ao **SUAP** e dados de perfil (ex.: IRA, curso/campus, links de portfólio). O diagrama utiliza **UUIDs** para garantir unicidade e segurança.

> [!TIP]
> Visualização do diagrama (DER):
>
> ![DER Inicial](docs/DER-inicial.png)

Entidades principais (resumo):

- **User**: CPF, matrícula, nome, papel (aluno/professor) e atributos acadêmicos
- **Institution** e **Course**: normalização de campus/curso
- **Notification**: mensagens do sistema (ex.: boas-vindas no primeiro login)

## Requisitos

- Docker
- Docker Compose (comando `docker compose`)

## Configuração (variáveis de ambiente)

O projeto usa `.env` (lido via `django-environ`). Comece copiando o exemplo:

**Linux/macOS**
```bash
cp .env.example .env
```

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env
```

**Windows (CMD)**
```bat
copy .env.example .env
```

Variáveis importantes (ver `.env.example`):

- **Django**: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`
- **PostgreSQL/Docker**: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- **DB URL**: `DATABASE_URL`
- **SUAP**: `SUAP_CLIENT_ID`, `SUAP_CLIENT_SECRET`, `SUAP_REDIRECT_URI`, `SUAP_AUTHORIZATION_URL`, `SUAP_TOKEN_URL`, `SUAP_USER_INFO_URL`

> [!IMPORTANT]
> Garanta que `SUAP_REDIRECT_URI` esteja consistente com o que você cadastrou no SUAP.

## Como Rodar (Docker)

Suba o Postgres e a API:

```bash
docker compose up --build
```

Em outro terminal, rode as migrações:

```bash
docker compose exec web python manage.py migrate
```

Opcional (acesso ao Django Admin):

```bash
docker compose exec web python manage.py createsuperuser
```

Para parar tudo:

```bash
docker compose down
```

## Endpoints

Base URL (local): `http://localhost:8000`

### Saúde

- `GET /health/` → `{"status": "ok"}`

### Admin

- `GET /admin/`

### Autenticação (SUAP + JWT)

Prefixo: `/api/auth/`

- `GET /api/auth/suap/login/` (público)
   - Retorna `login_url` para o frontend redirecionar o usuário ao SUAP.

- `POST /api/auth/suap/callback/` (público)
   - Body: `{"code": "..."}`
   - Troca o `code` por token no SUAP, sincroniza dados do usuário e retorna:
      - `access` e `refresh` (JWT)
      - payload mínimo do usuário (`id`, `first_name`, `role`, `is_new_user`)

   > Nota de integração: no OAuth2, o provedor normalmente redireciona o navegador para a `redirect_uri` com `?code=...`. Neste projeto, a API espera receber o `code` via `POST` (ex.: o frontend captura o `code` na URL e repassa para este endpoint).

- `POST /api/auth/refresh/` (público)
   - Body: `{"refresh": "..."}`
   - Retorna um novo `access` (e pode rotacionar refresh, conforme configuração).

- `POST /api/auth/logout/` (autenticado)
   - Requer header: `Authorization: Bearer <access>`
   - Body: `{"refresh": "..."}`
   - Faz blacklist do refresh token.

### Configuração dos tokens (SimpleJWT)

Configuração atual (em `config/settings/base.py`):

- `ACCESS_TOKEN_LIFETIME`: 60 minutos
- `REFRESH_TOKEN_LIFETIME`: 1 dia
- `ROTATE_REFRESH_TOKENS`: habilitado
- `BLACKLIST_AFTER_ROTATION`: habilitado

> Observação: o projeto define por padrão `IsAuthenticated` como permissão global do DRF. Por isso, endpoints públicos explicitam `AllowAny`.

## Exemplos de Requisições (cURL)

### 1) Obter URL de login do SUAP

```bash
curl -X GET http://localhost:8000/api/auth/suap/login/
```

### 2) Enviar o `code` do SUAP e receber JWT

```bash
curl -X POST http://localhost:8000/api/auth/suap/callback/ \
   -H "Content-Type: application/json" \
   -d '{"code":"SEU_CODE_AQUI"}'
```

### 3) Renovar sessão

```bash
curl -X POST http://localhost:8000/api/auth/refresh/ \
   -H "Content-Type: application/json" \
   -d '{"refresh":"SEU_REFRESH_AQUI"}'
```

### 4) Logout (blacklist do refresh)

```bash
curl -X POST http://localhost:8000/api/auth/logout/ \
   -H "Authorization: Bearer SEU_ACCESS_AQUI" \
   -H "Content-Type: application/json" \
   -d '{"refresh":"SEU_REFRESH_AQUI"}'
```

## Desenvolvimento (sem Docker) — opcional

Se você preferir rodar localmente (fora do container), garanta:

1) Python 3.11 e ambiente virtual ativo
2) `DATABASE_URL` apontando para um Postgres acessível localmente
3) `.env` configurado

Instale dependências e rode:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Qualidade de Código (pre-commit)

O projeto inclui hooks de formatação e validação (Black, isort, autoflake e `python manage.py check`). Para usar:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Troubleshooting rápido

- **Erro de conexão com DB**: confirme `DATABASE_URL` e se o container `db` está de pé (`docker compose ps`).
- **Callback do SUAP falhando**: revise `SUAP_REDIRECT_URI`, `SUAP_CLIENT_ID` e `SUAP_CLIENT_SECRET`.
- **`ALLOWED_HOSTS`**: em dev, mantenha `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`.
