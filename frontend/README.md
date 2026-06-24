# Agent Test Dashboard - Production-Ready React Frontend

Modern, responsive SaaS-style interface for AI-powered test automation and scenario generation.

## 🚀 Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios (centralized API client)
- **Backend**: FastAPI (http://localhost:8000)
- **Icons**: Lucide React

## 📋 Prerequisites

- Node.js 16+ and npm
- Backend FastAPI running on http://localhost:8000

## 🔧 Installation & Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
# Create .env file
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
```

### 3. Start Development Server

```bash
npm run dev
```

App runs at: **http://localhost:3000**

### 4. Production Build

```bash
npm run build
npm run preview  # Test build locally
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts          # Centralized Axios API client with all endpoints
│   ├── components/
│   │   ├── layout/            # Layout components (Navbar, PageContainer, etc)
│   │   │   ├── Navbar.tsx
│   │   │   ├── KPICard.tsx
│   │   │   ├── Layout.tsx
│   │   │   └── index.ts
│   │   └── ui/                # Reusable UI components
│   │       ├── Button.tsx
│   │       ├── Card.tsx
│   │       ├── Input.tsx
│   │       ├── Alert.tsx
│   │       ├── Badge.tsx
│   │       ├── Table.tsx
│   │       ├── Loader.tsx
│   │       └── index.ts
│   ├── hooks/
│   │   └── index.ts           # Custom data fetching hooks
│   ├── pages/                 # Page components
│   │   ├── DashboardPage.tsx
│   │   ├── PipelinePage.tsx
│   │   ├── AnalysisPage.tsx
│   │   ├── HistoryPage.tsx
│   │   └── index.ts
│   ├── App.tsx               # Main app with router
│   ├── main.tsx
│   └── index.css             # TailwindCSS + custom styles
├── public/                   # Static assets
├── .env                      # Environment variables
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## ✨ Features

### Pages

1. **Dashboard** 📊
   - System overview with KPIs
   - Total stories, scenarios, API status
   - Recent activity feed
   - System information

2. **Pipeline** ⚙️
   - Run full orchestrator pipeline
   - Configure pipeline options (RAG, Legacy RAG, Agent4)
   - Real-time progress tracking
   - Step-by-step status monitoring
   - Start/stop controls

3. **Analysis** 🔍
   - Run analysis on specific stories
   - Generate testable points
   - Create test scenarios
   - Generate Agent5 reports with recommendations
   - View verdicts (APPROVED/REQUIRES_REVIEW/NEEDS_REWORK)

4. **History** 📚
   - Search past analyses
   - View analysis history by story
   - Track model versions
   - Filter by status

### UI Components

#### Base Components (`components/ui/`)
- **Button** - Multiple variants (primary, secondary, danger, success, outline)
- **Card** - Flexible card with header, body, footer
- **Input** - Text input with validation states
- **TextArea** - Multi-line input
- **Select** - Dropdown with options
- **Alert** - Info, Success, Warning, Error notifications
- **Badge** - Status indicators
- **Table** - Data table with sorting
- **Loader** - Spinners and skeleton loaders

#### Layout Components (`components/layout/`)
- **Navbar** - Responsive navigation with mobile menu
- **PageContainer** - Centered max-width container
- **PageHeader** - Page title and description
- **PageSection** - Consistent section spacing
- **KPICard** / **StatsGrid** - Key metrics display

### Custom Hooks (`hooks/`)
```typescript
// Orchestrator pipeline
useOrchestrator(storyId)
  .run(options)      // Run pipeline
  .cancel()          // Cancel execution
  .data              // Pipeline result
  .loading           // Loading state
  .progress          // Progress percentage
  .isCompleted       // Check completion
  .isFailed          // Check failure

// Analysis
useAnalysis(storyId).run(options)

// Stories
useStories(storedOnly)
useStory(storyId, stored)

// Scenarios
useScenarios(storyId)

// Reports
useAgent5Report(storyId)
  .generate(options)
  .getMarkdown()
  .getSummary()
```

### API Client (`api/client.ts`)

Centralized, type-safe API client with all FastAPI endpoints:

```typescript
// Orchestrator
apiClient.orchestrator.run(storyId, options)
apiClient.orchestrator.getStatus(jobId)
apiClient.orchestrator.cancel(jobId)

// Analysis
apiClient.analysis.run(storyId, options)

// Stories
apiClient.stories.fetch(storyId)
apiClient.stories.list()

// Database
apiClient.db.listStories()
apiClient.db.getStory(storyId)
apiClient.db.listAnalyses(storyId)
apiClient.db.getLatestAnalysis(storyId, model)
apiClient.db.listScenarios(storyId)
apiClient.db.getAllScenarios()

// Reports
apiClient.agent5.generateReport(storyId, options)
apiClient.agent5.getReportMarkdown(storyId)
apiClient.agent5.getReportSummary(storyId)
apiClient.agent5.generateBatchReports(storyIds)
```

## 🎨 Design & UX

- **Modern SaaS Style**: Clean, professional interface
- **Responsive**: Works on desktop, tablet, mobile
- **Accessibility**: WCAG compliant form inputs
- **Performance**: Optimized with code splitting
- **Loading States**: Skeleton loaders and spinners
- **Error Handling**: User-friendly error messages
- **Visual Feedback**: Smooth transitions and animations

## 🚀 Building & Deployment

### Development
```bash
npm run dev          # Start dev server on localhost:3000
npm run build        # Production build
npm run preview      # Preview production build
```

### Docker

```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine
RUN npm install -g serve
WORKDIR /app
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
```

Build and run:
```bash
docker build -t agent-test-frontend .
docker run -e VITE_API_BASE_URL=http://api:8000 -p 3000:3000 agent-test-frontend
```

### Kubernetes/Cloud Deployment

Set environment variables:
```bash
VITE_API_BASE_URL=https://api.example.com
```

## 🔧 Configuration

### Environment Variables

`.env` file options:

```bash
# Backend API
VITE_API_BASE_URL=http://localhost:8000

# Optional
VITE_APP_VERSION=1.0.0
VITE_LOG_LEVEL=info
```

### Vite Config

See `vite.config.ts` for build optimization settings.

## 🐛 Troubleshooting

### API Connection Fails
```
✓ Backend running? curl http://localhost:8000/
✓ Correct URL in .env? VITE_API_BASE_URL=...
✓ CORS enabled in FastAPI?
✓ Check browser console for errors
```

### Build Errors
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Port 3000 Already in Use
```bash
npm run dev -- --port 3001
```

## 📊 API Endpoints Used

```
POST /orchestrator/run/{story_id}        # Run pipeline
GET  /orchestrator/status/{job_id}       # Get pipeline status
POST /orchestrator/cancel/{job_id}       # Cancel pipeline

GET  /analysis/{story_id}                # Run analysis
POST /analysis/{story_id}                # Analysis options

GET  /db/stories                         # List stored stories
GET  /db/stories/{story_id}              # Get story
GET  /db/analyses/{story_id}             # List analyses
GET  /db/scenarios/{story_id}            # List scenarios

POST /agent5/story/{story_id}/report     # Generate report
GET  /agent5/story/{story_id}/report/markdown
GET  /agent5/story/{story_id}/report/summary
```

## 🎯 Performance Optimizations

- Code splitting with React.lazy()
- CSS minification with Tailwind
- Tree-shaking unused code
- Production builds without source maps
- Image lazy-loading ready
- Component memoization for expensive renders

## 🌐 Browser Support

| Browser | Support |
|---------|---------|
| Chrome  | Latest 2 versions |
| Firefox | Latest 2 versions |
| Safari  | Latest 2 versions |
| Edge    | Latest 2 versions |
| Mobile  | iOS 12+, Chrome Android |

## 📝 License

© 2026 Sopra Steria

---

**Status**: Production-Ready ✅
**Last Updated**: June 2026
**Version**: 1.0.0


