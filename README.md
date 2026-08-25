# Agent Test

Agent Test est une application FastAPI orientée orchestration d’agents pour l’analyse de stories, la génération de tests et l’intégration avec des services externes comme Jira, Groq et Microsoft.

## Fonctionnalités principales

- API FastAPI modulaire
- Authentification et JWT
- Base PostgreSQL avec SQLAlchemy et Alembic
- Routes d’administration, d’analyse, de génération et de gestion des stories
- Frontend Vite/Tailwind dans le dossier `frontend`

## Installation locale 

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

L’application se lance avec deux processus séparés.

Terminal 1 — backend :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 — frontend :

```powershell
cd frontend
npm run dev
```

L’interface est accessible sur `http://localhost:3000` et l’API sur
`http://localhost:8000/docs`.

## Déploiement

Pour un déploiement de recette ou de production, utiliser deux services
séparés : FastAPI pour le backend et un serveur web (IIS, Nginx ou équivalent)
pour le frontend compilé.

### Préparation du serveur

1. Cloner le dépôt et installer Python, Node.js et PostgreSQL.
2. Créer l'environnement Python et installer les dépendances :

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Créer `.env` à partir de `.env.example` et renseigner les vraies valeurs :

   ```env
   DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<database>
   JWT_SECRET=<secret-aleatoire-long>
   ADMIN_EMAIL=<email-admin>
   ADMIN_PASSWORD=<mot-de-passe-admin>
   JIRA_PROD_URL=<url-jira>
   JIRA_USERNAME=<compte-jira>
   JIRA_PASSWORD=<mot-de-passe-jira>
   AWS_ACCESS_KEY_ID=<access-key>
   AWS_SECRET_ACCESS_KEY=<secret-key>
   AWS_REGION=eu-west-3
   LLM_PROVIDER=bedrock
   BEDROCK_MODEL_ID=eu.amazon.nova-2-lite-v1:0
   FRONTEND_BASE_URL=https://<domaine-frontend>
   ALLOWED_ORIGINS=https://<domaine-frontend>
   COOKIE_SECURE=true
   ```

Les secrets ne doivent jamais être commités dans Git. Le fichier `.env` est
ignoré par `.gitignore`.

### Premier administrateur

Le premier compte administrateur est créé automatiquement lors de l'initialisation
de l'application, à partir des variables `ADMIN_EMAIL` et `ADMIN_PASSWORD` du
fichier `.env`.

Cette création s'effectue uniquement si aucun administrateur n'existe encore dans
la base de données. Si la base contient déjà un administrateur, les valeurs du
`.env` ne modifient pas ses identifiants existants.

Avant le premier démarrage, l'encadrant ou l'administrateur du déploiement doit
remplacer les valeurs d'exemple dans le `.env` du serveur par ses propres
identifiants :

```env
ADMIN_EMAIL=son-vrai-email
ADMIN_PASSWORD=son-mot-de-passe-fort
```

`son-vrai-email` et `son-mot-de-passe-fort` sont des exemples de documentation :
ils doivent être remplacés par les vraies valeurs avant le déploiement.

Après le démarrage, se connecter sur `https://<domaine-frontend>/login` avec
cet email et ce mot de passe. Ces identifiants doivent être transmis par un
canal sécurisé et ne doivent jamais être ajoutés au README, au dépôt Git ou aux
logs.

### Base de données

Appliquer les migrations sur la base de production :

```powershell
alembic upgrade head
```

### Démarrage production

Démarrer le backend sans le mode développement `--reload` :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Construire le frontend puis publier le dossier `frontend/dist/` avec IIS,
Nginx ou un serveur web équivalent :

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL="https://<domaine-api>"
npm run build
```

Vérifications après déploiement :

- ouvrir `https://<domaine-frontend>` ;
- vérifier l'API sur `https://<domaine-api>/docs` ;
- tester la connexion admin et QA ;
- lancer une analyse complète jusqu'au rapport Agent 5 ;
- vérifier les appels Jira et Amazon Bedrock ;
- confirmer que HTTPS, CORS et les cookies fonctionnent.

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
