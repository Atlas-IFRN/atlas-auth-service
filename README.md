# Atlas Auth Service 🔐

Microserviço de autenticação desenvolvido com **Django** e **Django REST Framework**, rodando em containers **Docker** com banco de dados **PostgreSQL**.

## 🛠️ Requisitos

- Docker
- Docker Compose (o comando `docker compose`)

## ⚙️ Configuração Inicial

1. Clone o repositório.
2. Crie um arquivo `.env` na raiz do projeto baseando-se no `.env.example`:

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

3. Confira as variáveis no `.env` (principalmente `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).

## 🚀 Como Rodar

Para construir as imagens e subir os containers pela primeira vez:

```bash
docker compose up --build
```

## 🐘 Banco de Dados (Migrações)

Após os containers estarem ativos, execute as migrações para criar as tabelas no PostgreSQL:

```bash
docker compose exec web python manage.py migrate
```

## 🏥 Verificação de Saúde

O serviço expõe um endpoint para verificar se a API está online:

- URL: http://localhost:8000/health/
- Método: `GET`
- Resposta esperada: `{"status": "ok"}`

## 🧹 Como Parar

```bash
docker compose down
```