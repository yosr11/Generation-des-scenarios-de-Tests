# Agent Test

Agent Test est une application FastAPI orientée orchestration d’agents pour l’analyse de stories, la génération de tests et l’intégration avec des services externes comme Jira, Groq et Microsoft.

## Fonctionnalités principales

- API FastAPI modulaire
- Authentification et JWT
- Base PostgreSQL avec SQLAlchemy et Alembic
- Routes d’administration, d’analyse, de génération et de gestion des stories
- Frontend Vite/Tailwind dans le dossier `frontend`

## Installation locale sans Docker

1. Créez un environnement virtuel :
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Installez les dépendances :
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. Configurez PostgreSQL local ou à distance.
   - Créez la base de données :
     ```sql
     CREATE DATABASE agent_test;
     ```

4. Copiez et éditez la configuration :
   ```powershell
   copy .env.example .env
   ```

5. Mettez à jour `.env` avec vos valeurs locales :
   ```ini
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_test
   JWT_SECRET=replace_with_a_long_random_secret
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=replace_with_strong_password
   GROQ_API_KEY=replace_with_your_groq_key
   JIRA_PROD_URL=https://jira.example.com
   JIRA_TEST_URL=https://jira-test.example.com
   JIRA_USERNAME=your_jira_username
   JIRA_PASSWORD=your_jira_password
   ```

## Lancer l’application

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Migrations de base de données

Les migrations sont stockées dans `alembic/`.

Pour appliquer les migrations :

```powershell
alembic upgrade head
```

> Si vous ne souhaitez pas exécuter Alembic, l’application tente d’initialiser les tables via `app/db/init_postgres.py` au démarrage.

## Tests

Exécutez le jeu de tests complet :

```powershell
pytest -q
```

Pour exécuter seulement les tests d’API et d’intégration :

```powershell
pytest -q tests/test_db_api_routes.py tests/test_db_integration.py tests/test_story_repository.py tests/test_auth_api.py
```

## CI GitHub Actions

Le workflow GitHub Actions est défini dans `.github/workflows/ci.yml`.
Il exécute :

- lint avec `ruff`
- format check avec `black`
- tests unitaires et d’intégration via `pytest`

## Structure du projet

- `app/` : code métier et routes FastAPI
- `alembic/` : migrations de base de données
- `tests/` : tests unitaires et d’intégration
- `frontend/` : interface utilisateur Vite/Tailwind
