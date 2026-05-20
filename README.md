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

### Perfil e Notificações

- `GET /api/auth/users/me/` (autenticado)
   - Retorna os dados do usuário autenticado (serializador `UserSerializer`).

- `GET /api/auth/users/<matricula>/` (autenticado)
   - Retorna os dados públicos do usuário identificado pela `matricula`.

- `GET /api/auth/notifications/` (autenticado)
   - Lista notificações recentes do usuário (últimos 5 dias por padrão).

Exemplo: obter perfil do usuário atual

```bash
# Atlas Auth Service 🔐

Microserviço de autenticação do ecossistema ATLAS. Implementado com Django + Django REST Framework, integrado ao SUAP (OAuth2) e com um servidor gRPC para expor perfis a outros microsserviços.

Este README reescrito documenta: visão geral, instalação, variáveis de ambiente, endpoints HTTP (campos de resposta), gRPC, execução local e em Docker, migrações, testes e troubleshooting.

---

## Visão geral

- API HTTP (Django) que lida com login via SUAP, emissão/renovação/revogação de tokens JWT e gerenciamento de perfil/notifications.
- gRPC service (arquivo [grpc_server.py](grpc_server.py)) que expõe `GetUserProfile` para consumo por outros serviços.
- Banco: PostgreSQL (container no `docker-compose.yaml`).

Arquivos importantes:
- Configuração do projeto: [config/](config/)
- App de autenticação: [apps/authentication/](apps/authentication/)
- Proto gRPC: [proto/user.proto](proto/user.proto)

---

## Requisitos

- Python 3.11
- Docker & Docker Compose (ou ambiente Python com Postgres acessível)
- (opcional) virtualenv / .venv

---

## Quickstart — Docker (recomendado)

1. Copie o arquivo de exemplo de variáveis:

```bash
cp .env.example .env
```

2. Suba os serviços:

```bash
docker compose up --build -d
```

3. Rode migrações e (opcional) crie superuser:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

4. Logs:

```bash
docker compose logs -f web
```

Parar/limpar:

```bash
docker compose down
```

---

## Execução local (sem Docker)

1. Crie e ative um virtualenv com Python 3.11.
2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Configure `DATABASE_URL` no `.env` apontando para um Postgres local.
4. Rode migrações e servidor:

```bash
python manage.py migrate
python manage.py runserver
```

Para executar o servidor gRPC localmente (fora do Django process):

```bash
python grpc_server.py
```

---

## Variáveis de ambiente (resumo)

Veja [`.env.example`](.env.example) para a lista completa. Principais variáveis:

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_SETTINGS_MODULE`
- `DATABASE_URL` (ex.: `postgres://user:pass@db:5432/dbname`)
- `POSTGRES_*` (quando usar docker-compose para o DB)
- SUAP: `SUAP_CLIENT_ID`, `SUAP_CLIENT_SECRET`, `SUAP_REDIRECT_URI`, `SUAP_AUTHORIZATION_URL`, `SUAP_TOKEN_URL`, `SUAP_USER_INFO_URL`

IMPORTANTE: garanta que `SUAP_REDIRECT_URI` esteja cadastrado no SUAP e igual ao valor em `.env`.

---

## Endpoints HTTP (detalhados)

Base URL local: `http://localhost:8000`

### Saúde

- `GET /health/` → 200 `{ "status": "ok" }`

### Admin

- `GET /admin/` (interface administrativa do Django)

### Autenticação (prefixo `/api/auth/`)

- `GET /api/auth/suap/login/` (public)
   - Retorna: `{ "login_url": "https://..." }` — frontend redireciona o usuário para o SUAP.

- `POST /api/auth/suap/callback/` (public)
   - Body: `{ "code": "..." }`
   - Fluxo: troca `code` pelo token do SUAP, busca dados do usuário, sincroniza ou cria o usuário local e retorna JWT.
   - Exemplo de resposta (200):

```json
{
   "access": "<jwt_access>",
   "refresh": "<jwt_refresh>",
   "user": { "id": "<uuid>", "first_name": "Nome", "role": "STUDENT|TEACHER", "is_new_user": true }
}
```

- `POST /api/auth/refresh/` (public)
   - Body: `{ "refresh": "..." }`
   - Retorna novo `access` (e possivelmente novo `refresh`, dependendo da rotação configurada).

- `POST /api/auth/logout/` (authenticated)
   - Header: `Authorization: Bearer <access>`
   - Body: `{ "refresh": "..." }`
   - Ação: marca o `refresh` na blacklist (invalidando-o).

### Perfil e Notificações (authenticated)

- `GET /api/auth/users/me/`
   - Retorna os campos do usuário autenticado (ver lista de campos abaixo).

- `GET /api/auth/users/<matricula>/`
   - Retorna o perfil público do usuário pela `matricula`.

- `GET /api/auth/notifications/`
   - Retorna notificações recentes do usuário (filtro por padrão: últimos 5 dias).

Campos retornados pelo `UserSerializer` (arquivo [apps/authentication/serializers.py](apps/authentication/serializers.py)):

- `id` (UUID)
- `matricula` (string)
- `first_name` (string)
- `full_name` (string)
- `email` (string)
- `cpf` (string)
- `role` ("STUDENT" | "TEACHER")
- `ira` (float | null)
- `period` (int | null)
- `about_me` (string | null)
- `linkedin` (url | null)
- `github` (url | null)
- `curriculo_lattes` (url | null)
- `course_name` (string | null)
- `institution_name` (string | null)

Campos retornados pelo `NotificationSerializer` (arquivo [apps/authentication/serializers.py](apps/authentication/serializers.py)):

- `id` (UUID)
- `title` (string)
- `message` (string)
- `is_read` (boolean)
- `type` (string — ex.: `BOLSA`, `AVALIACAO`, `SISTEMA`)
- `created_at` (datetime)

Exemplos (cURL):

Obter URL de login SUAP:

```bash
curl -X GET http://localhost:8000/api/auth/suap/login/
```

Enviar `code` e trocar por JWT:

```bash
curl -X POST http://localhost:8000/api/auth/suap/callback/ \
   -H "Content-Type: application/json" \
   -d '{"code":"SEU_CODE_AQUI"}'
```

Obter perfil autenticado:

```bash
curl -X GET http://localhost:8000/api/auth/users/me/ \
   -H "Authorization: Bearer SEU_ACCESS_AQUI"
```

Listar notificações:

```bash
curl -X GET http://localhost:8000/api/auth/notifications/ \
   -H "Authorization: Bearer SEU_ACCESS_AQUI"
```

---

## gRPC: serviço de perfil

- Proto principal: [proto/user.proto](proto/user.proto)
- Serviço exposto: `UserService.GetUserProfile(UserRequest) -> UserResponse`.
- Campos do `UserResponse` espelham o perfil (sem CPF) — ver o proto para o esquema completo.
- Servidor gRPC: [grpc_server.py](grpc_server.py) (escuta na porta `50051`).

Regenerar stubs (quando alterar `.proto`):

```bash
python -m grpc_tools.protoc -I=proto --python_out=proto --grpc_python_out=proto proto/user.proto
```

No container, a porta `50051` já está mapeada pelo `docker-compose.yaml`.

---

## Migrações e administração

- Rodar migrações:

```bash
python manage.py migrate
```

- Criar superuser:

```bash
python manage.py createsuperuser
```

---

## Testes e qualidade de código

- Atualmente não existem testes automatizados implementados ([apps/authentication/tests.py](apps/authentication/tests.py) está vazio).
- Hooks pre-commit configurados em [`.pre-commit-config.yaml`](.pre-commit-config.yaml) (Black, isort, autoflake, checagem Django).

Instalar e usar pre-commit:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## Troubleshooting rápido

- Erro de conexão com DB: verifique `DATABASE_URL` e se o serviço `db` está ativo (`docker compose ps`).
- Callback do SUAP falhando: confirme `SUAP_REDIRECT_URI`, `SUAP_CLIENT_ID` e `SUAP_CLIENT_SECRET`.
- Erros de permissão no DRF: por padrão `IsAuthenticated` é global — confirme `permission_classes` nas views públicas.

---

## Próximos passos recomendados

- Adicionar testes unitários e de integração para o fluxo SUAP e para o servidor gRPC.
- Adicionar um entrypoint que rode Django + gRPC em processos separados (ex.: `gunicorn` + supervisor) ou dividir gRPC em outro serviço no `docker-compose`.
- Documentar contrato de API gRPC e exemplos de chamadas de cliente (Python/Go).

---

Se quiser, eu:
- adiciono os exemplos de payloads JSON completos em cada endpoint,
- documento os campos com exemplos reais retornados pelo `UserSerializer`, ou
- altero o `docker-compose` para executar Django + gRPC em serviços separados.
