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

## Installation

1. Créez un environnement virtuel :
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Copiez le fichier d’exemple de configuration :
   ```bash
   copy .env.example .env
   ```

4. Modifiez .env avec vos valeurs réelles.

## Lancer l’application

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

Les migrations Alembic sont gérées dans le dossier alembic.

Pour appliquer les migrations :

```bash
alembic upgrade head
```

## Tests

Exécutez les tests avec :

```bash
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
