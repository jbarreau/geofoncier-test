# Géofoncier Frontend — Module Federation

Architecture micro-frontend basée sur [**@originjs/vite-plugin-federation**](https://github.com/originjs/vite-plugin-federation).

## Architecture

| App | Port | Rôle | Composants exposés |
|---|---|---|---|
| `shell-app` | **5000** | Shell principal — routing global, layout, authStore | `./stores/auth` |
| `auth-front` | **5001** | Auth & administration | `./LoginView`, `./RegisterView`, `./UsersView`, `./RolesView`, `./PermissionsView` |
| `task-front` | **5002** | Gestion des tâches | `./TaskList`, `./TaskForm` |
| `analytics-front` | **5003** | Tableau de bord analytique | `./Dashboard` |

## Prérequis

- Node.js >= 18
- pnpm >= 8
- Services backend démarrés (voir [docker-compose.yml](../docker-compose.yml))

## Démarrer en développement

```bash
cd frontend
pnpm install        # première fois uniquement
pnpm dev:all        # lance les 4 apps en parallèle
```

Accéder à l'application : **http://localhost:5000**

> **Note :** Les remotes (`auth-front`, `task-front`, `analytics-front`) sont buildés avant d'être servis via `vite preview`. Le premier démarrage prend ~15–30 secondes le temps que les builds se terminent.

## Scripts disponibles

```bash
pnpm dev:all       # Démarre toutes les apps (shell en dev, remotes en preview)
pnpm build:all     # Build de production de toutes les apps (remotes en premier)
```

## Backend requis

| Service | Port |
|---|---|
| auth-service | 8000 |
| task-service | 8001 |
| analytics-service | 8002 |

Démarrer le backend :

```bash
docker-compose up
```

## Comment fonctionne le partage de l'authStore

Le shell-app définit le store Pinia `'auth'` et l'expose via Module Federation (`./stores/auth`).

Les remotes partagent la même instance Pinia grâce à la config `shared: { pinia: { singleton: true } }`. Ainsi, `useAuthStore()` dans n'importe quel remote retourne la même instance que celle du shell — les tokens, permissions et email sont synchronisés automatiquement.

## Développer un remote en isolation

Chaque remote peut s'exécuter de façon autonome pour développer ses composants :

```bash
pnpm --filter auth-front dev      # http://localhost:5001
pnpm --filter task-front dev      # http://localhost:5002
pnpm --filter analytics-front dev # http://localhost:5003
```

## Structure des fichiers

```
frontend/
├── pnpm-workspace.yaml
├── package.json          ← workspace root (dev:all, build:all)
├── README.md
├── shell-app/            ← port 5000
│   └── src/
│       ├── App.vue       ← nav + <Suspense>
│       ├── main.ts
│       ├── router/       ← routes fédérées via defineAsyncComponent
│       ├── stores/       ← auth.ts (authStore partagé)
│       ├── views/        ← HomeView
│       ├── api/          ← auth, users, roles, permissions
│       └── components/   ← LoadingSpinner, RemoteError
├── auth-front/           ← port 5001
│   └── src/views/        ← LoginView, RegisterView, UsersView, RolesView, PermissionsView
├── task-front/           ← port 5002
│   └── src/
│       ├── views/        ← TasksView (exposé comme TaskList)
│       └── components/   ← TaskForm
└── analytics-front/      ← port 5003
    └── src/views/        ← AnalyticsView (exposé comme Dashboard)
```
