# Agent Test

Agent Test est une application FastAPI orientée orchestration d’agents pour l’analyse de stories, la génération de tests et l’intégration avec des services externes comme Jira, Groq et Azure/Microsoft.

## Fonctionnalités principales

- API FastAPI pour l’orchestration des agents
- Base PostgreSQL avec SQLAlchemy et Alembic
- Authentification administrateur et testeur
- Analyse de stories et génération de tests
- Frontend Vite/Tailwind dans le dossier frontend

## Prérequis

- Python 3.10+
- PostgreSQL local ou accessible
- Un fichier .env basé sur .env.example

## Installation locale sans Docker

1. Créez un environnement virtuel :
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Installez les dépendances :
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Installez PostgreSQL localement ou utilisez une base PostgreSQL accessible :
   - Windows : installez PostgreSQL via l’installateur officiel ou via le package manager de votre entreprise.
   - Linux : installez `postgresql` et démarrez le service.

4. Créez la base de données de développement ou de test :
   ```sql
   CREATE DATABASE agent_test;
   ```

5. Copiez le fichier d’exemple de configuration :
   ```powershell
   copy .env.example .env
   ```

6. Modifiez `.env` selon votre environnement, par exemple :
   ```ini
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_test
   JWT_SECRET=your-strong-secret
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=strong-test-password
   GROQ_API_KEY=test-groq-key
   JIRA_PROD_URL=https://jira.example.com
   JIRA_TEST_URL=https://jira-test.example.com
   JIRA_USERNAME=jira-user
   JIRA_PASSWORD=jira-password
   ```

## Lancer l’application

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

Exécutez les tests avec :

```powershell
pytest -q
```

## Base de données

Les migrations Alembic sont gérées dans le dossier `alembic`.

Pour appliquer les migrations :

```powershell
alembic upgrade head
```

Si vous n’utilisez pas Alembic pour démarrer, le service initialise également les tables de base à l’exécution via `app/db/init_postgres.py`.

### Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Base de données

Les migrations Alembic sont gérées dans le dossier `alembic`.

Pour appliquer les migrations :

```powershell
alembic upgrade head
```

Si vous n’utilisez pas Alembic pour démarrer, le service initialise également les tables de base à l’exécution via `app/db/init_postgres.py`.

## Tests

Exécutez les tests avec :

```powershell
pytest -q
```

## CI

Une workflow GitHub Actions est disponible dans .github/workflows/ci.yml.
Elle exécute automatiquement les tests à chaque push ou pull request.

## Structure du projet

- app/ : code applicatif principal
- alembic/ : migrations de base de données
- frontend/ : interface utilisateur Vite
- tests/ : tests automatisés
