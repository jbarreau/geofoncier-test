# Module Federation — Documentation technique

## Sommaire

1. [Qu'est-ce que le Module Federation ?](#quest-ce-que-le-module-federation)
2. [Problèmes résolus](#problèmes-résolus)
3. [Alternatives](#alternatives)
4. [Points forts](#points-forts)
5. [Limitations et pièges](#limitations-et-pièges)
6. [Implémentation dans ce projet](#implémentation-dans-ce-projet)
7. [Décisions d'architecture](#décisions-darchitecture)

---

## Qu'est-ce que le Module Federation ?

Le Module Federation est un mécanisme qui permet à plusieurs applications JavaScript indépendantes de partager du code à l'exécution (runtime), sans passer par un bundle commun ni par un npm publish.

L'idée centrale : une application expose des modules (`exposes`), une autre les consomme à la demande (`remotes`), et les deux peuvent partager des dépendances communes comme une seule instance (`shared`).

Introduit par Webpack 5 en 2020, le concept a ensuite été porté vers d'autres bundlers. Dans ce projet on utilise `@originjs/vite-plugin-federation`, le portage officiel pour Vite.

### Vocabulaire

| Terme | Définition |
|---|---|
| **Host / Shell** | L'app qui orchestre et consomme les remotes |
| **Remote** | Une app qui expose des composants/modules |
| **remoteEntry.js** | Le manifeste généré par le remote, chargé par le shell au runtime |
| **Shared** | Dépendances partagées en singleton entre toutes les apps |
| **Expose** | Déclaration des modules qu'un remote rend disponibles |

---

## Problèmes résolus

### 1. Couplage fort dans un monolithe frontend

Dans une SPA classique, toute modification d'un composant oblige à rebuilder et redéployer l'intégralité de l'application. Le Module Federation permet de déployer un seul remote sans toucher aux autres.

**Avant** :
```
Une modification dans AnalyticsView.vue
  → rebuild complet du bundle (~30s)
  → redéploiement de tout le frontend
  → rollback impossible par domaine
```

**Après** :
```
Une modification dans analytics-front
  → rebuild de analytics-front seulement (~5s)
  → redéploiement de analytics-front
  → les autres apps continuent sans interruption
```

### 2. Ownership fragmenté

Quand plusieurs équipes travaillent sur le même repo frontend, les conflits de merge, les blocages de release et les régressions inter-équipes sont fréquents.

Avec Module Federation, chaque équipe possède son app avec son propre cycle de release. La seule interface contractuelle est la liste des composants exposés.

### 3. Duplication des dépendances

Sans stratégie de partage, plusieurs micro-frontends embarquent chacun leur propre copie de Vue, Pinia, etc. → bundle final lourd, risques d'instances multiples (deux Pinia = deux états distincts → bugs subtils).

La configuration `shared: { vue: { singleton: true } }` garantit qu'une seule instance de Vue tourne dans le navigateur, peu importe combien de remotes sont chargés.

### 4. Time-to-interactive initial trop long

Un bundle monolithique qui inclut tous les écrans est chargé en entier au premier accès, même si l'utilisateur ne va jamais sur `/analytics`.

Le Module Federation charge chaque remote uniquement quand sa route est activée pour la première fois (`defineAsyncComponent` + lazy routing).

### 5. Tests et CI trop lents

Un seul pipeline qui teste tout → feedback lent, contention sur les runners CI.

Chaque app ayant son propre `package.json`, il devient possible d'avoir des pipelines CI parallèles et indépendants par domaine.

---

## Alternatives

### iframes

La solution la plus ancienne et la plus isolée.

| | |
|---|---|
| **Avantages** | Isolation totale (CSS, JS, DOM), déploiement trivial, tech-agnostique |
| **Inconvénients** | Communication inter-frame complexe (postMessage), performance médiocre, UX dégradée (scroll, focus, accessibilité), impossibilité de partager état nativement |

**Quand choisir** : intégration d'apps tierces avec des contraintes de sécurité strictes (ex. : widget bancaire dans un portail).

---

### npm packages privés

Publier les composants partagés dans un registre npm privé (Verdaccio, GitHub Packages, etc.).

| | |
|---|---|
| **Avantages** | Versioning explicite, contrat d'API clair, compatible avec tous les outils |
| **Inconvénients** | Nécessite un publish/tag à chaque changement, le consommateur doit update sa dépendance et rebuilder, pas de partage de state à l'exécution |

**Quand choisir** : composants UI purement présentationnels (design system, boutons, icônes) qui n'ont pas besoin d'état partagé et dont les changements sont peu fréquents.

---

### Monorepo avec build partagé (Turborepo, Nx)

Toutes les apps dans un seul repo, le bundler construit à partir des sources partagées.

| | |
|---|---|
| **Avantages** | Refactoring cross-app facilité, typage partagé, cache de build incrémental |
| **Inconvénients** | Le déploiement reste couplé (un changement dans un package partagé rebuild tout), pas d'indépendance runtime |

**Quand choisir** : équipe unique, pas besoin de déploiements indépendants, priorité au DX plutôt qu'à l'autonomie des équipes.

---

### Web Components (Custom Elements)

Encapsuler les composants en Custom Elements standard du DOM.

| | |
|---|---|
| **Avantages** | Standard W3C, framework-agnostique, encapsulation CSS via Shadow DOM |
| **Inconvénients** | Compatibilité limitée avec Vue/React (props, events, slots), overhead de sérialisation, pas de partage de state, DX inférieur |

**Quand choisir** : composants exposés à des consommateurs qui utilisent des frameworks différents.

---

### Single-SPA

Framework dédié à l'orchestration de micro-frontends.

| | |
|---|---|
| **Avantages** | Mature (2018), support multi-framework (React + Vue + Angular dans la même page), lifecycle complet |
| **Inconvénients** | Configuration verbeuse, courbe d'apprentissage élevée, pas de solution native au partage de dépendances (souvent combiné avec Module Federation), API propriétaire |

**Quand choisir** : migration d'une app legacy multi-framework, besoin d'une orchestration fine du routing et des lifecycles.

---

### Tableau comparatif

| Critère | Module Federation | iframes | npm privé | Monorepo build | Web Components | Single-SPA |
|---|---|---|---|---|---|---|
| Partage d'état runtime | ✅ natif | ❌ postMessage | ❌ | ❌ | ❌ | ⚠️ manuel |
| Déploiement indépendant | ✅ | ✅ | ⚠️ rebuild consommateur | ❌ | ✅ | ✅ |
| Isolation CSS | ⚠️ scope manuel | ✅ | ⚠️ | ⚠️ | ✅ Shadow DOM | ⚠️ |
| Multi-framework | ⚠️ possible mais complexe | ✅ | ❌ | ❌ | ✅ | ✅ |
| Complexité de setup | Moyenne | Faible | Faible | Faible | Faible | Élevée |
| Performance réseau | Bonne (lazy) | Mauvaise | Bonne | Très bonne | Bonne | Bonne |
| Maturité | Bonne | Très mature | Très mature | Mature | Mature | Mature |
| DX avec Vue | ✅ | ❌ | ✅ | ✅ | ⚠️ | ⚠️ |

---

## Points forts

### Déploiement indépendant sans recompilation des consommateurs

C'est l'avantage principal. Le shell ne contient que l'URL du `remoteEntry.js`. Quand un remote est redéployé, le shell charge automatiquement la nouvelle version au prochain chargement de la route, sans rebuild.

```
shell-app vite.config.ts :
remotes: {
  'analytics-front': 'http://localhost:5003/assets/remoteEntry.js'
  // ↑ pointeur stable — le contenu change sans toucher au shell
}
```

### Partage de singletons garanti

Sans `shared`, deux apps qui importent Vue se retrouvent avec deux instances distinctes → `provide/inject` cassé, `useRoute()` qui retourne `undefined` dans le remote, etc.

```typescript
shared: {
  vue: { singleton: true, requiredVersion: '^3.4.0' },
  pinia: { singleton: true, requiredVersion: '^2.1.0' },
}
```

Avec `singleton: true`, la federation runtime refuse de charger une deuxième copie : si `vue@3.4.x` est déjà dans le scope, tous les remotes utilisent cette instance. Cela permet de partager l'authStore (défini dans le shell) avec tous les remotes via la déduplication Pinia par store ID.

### Lazy loading natif par domaine

Les `defineAsyncComponent` dans le router du shell n'initialisent le réseau vers un remote qu'au premier accès à la route correspondante. Résultat : le TTI (Time To Interactive) de la page initiale n'est pas pénalisé par le code de `analytics-front` si l'utilisateur ne visite jamais `/analytics`.

### Frontière de déploiement = frontière de domaine métier

La découpe `auth-front / task-front / analytics-front / shell` suit les domaines métier. C'est une frontière naturelle pour les équipes, les tests, les releases et le monitoring.

---

## Limitations et pièges

### `remoteEntry.js` n'existe qu'après `vite build`

C'est le piège le plus courant avec `@originjs/vite-plugin-federation`. En mode `vite dev`, aucun `remoteEntry.js` n'est généré — le plugin ne fonctionne qu'avec le pipeline de build.

**Conséquence pratique** : en développement, les remotes doivent tourner en mode `vite preview` (build préalable), pas `vite dev`. Le premier démarrage est donc plus lent (~15–30s pour builder les remotes).

```json
// package.json de chaque remote
"dev:preview": "vite build && vite preview"
```

Il existe un mode `devMode: true` dans certaines versions du plugin (expérimental), mais son comportement est instable.

**Alternative en cours** : `@module-federation/vite` (la lib officielle Webpack MF portée sur Vite) supporte mieux le dev live. À évaluer si le pain point dev devient bloquant.

### `build.modulePreload: false` est obligatoire

Vite injecte par défaut des `<link rel="modulepreload">` pour précharger les chunks. Ces instructions cassent le mécanisme de résolution de modules fédérés (le runtime MF intercepte les imports dynamiques avant que le navigateur ne précharge).

Sans ce flag, les remotes échouent silencieusement en production.

### Les composants globaux ne se propagent pas

Si `analytics-front` enregistre `VueApexCharts` globalement dans son propre `main.ts`, ce composant n'est **pas** disponible quand `AnalyticsView` est chargé dans le contexte du shell. La raison : le `main.ts` du remote n'est pas exécuté — seul le composant exposé est chargé.

**Solution** : enregistrer les composants globaux dans le shell, ou passer à des imports locaux dans les composants.

```typescript
// shell-app/src/main.ts — nécessaire pour <apexchart> dans analytics-front
app.use(VueApexCharts)
```

### TypeScript : pas de types auto-générés

Le plugin ne génère pas de types pour les imports fédérés. `import('auth-front/LoginView')` donne une erreur TypeScript sans déclaration manuelle.

**Solution** : fichier `remotes.d.ts` à maintenir à la main :

```typescript
declare module 'auth-front/LoginView' {
  import { DefineComponent } from 'vue'
  const component: DefineComponent
  export default component
}
```

C'est du boilerplate, mais il reste limité : une déclaration par composant exposé.

### Versioning et compatibilité des interfaces

Le Module Federation ne fournit aucun mécanisme de vérification de contrat entre shell et remotes. Si `task-front` renomme `./TaskList` en `./Tasks`, le shell continue de tenter de charger `task-front/TaskList` et échoue silencieusement à l'exécution (seul `RemoteError.vue` s'affiche).

**Bonnes pratiques** :
- Traiter les noms exposés comme une API publique (semver)
- Maintenir une liste des contrats dans une doc partagée
- Envisager des tests d'intégration qui chargent effectivement les remotes

### Overhead de configuration

Chaque app nécessite : un `vite.config.ts`, un `package.json`, un `tsconfig.json`, un `index.html`, un `main.ts` standalone, etc. Pour 4 apps, c'est ~20 fichiers de config à maintenir.

C'est acceptable pour ce projet, mais le ratio config/code devient problématique si les remotes sont très petits (1–2 composants chacun).

### CSS global et isolation

Il n'y a pas d'isolation CSS native. Si `auth-front` et `analytics-front` définissent chacun un `.container { padding: 2rem }`, les styles se superposent dans le contexte du shell.

**Solution adoptée ici** : PicoCSS est importé uniquement dans `shell-app/main.ts`. Les remotes ne l'importent pas (ils l'utilisent via l'instance partagée). Dans un projet plus complexe, il faudrait envisager CSS Modules ou scoped styles stricts.

### Débogage cross-apps

La stack trace dans le shell peut pointer vers le bundle du remote sans que le sourcemap du remote soit disponible. Il faut configurer les sourcemaps de build sur chaque remote et s'assurer qu'ils sont accessibles (CORS).

---

## Implémentation dans ce projet

### Topologie

```
Browser
  └── shell-app (:5000)
        ├── charge auth-front/LoginView       ← auth-front (:5001/assets/remoteEntry.js)
        ├── charge auth-front/RegisterView
        ├── charge auth-front/UsersView
        ├── charge auth-front/RolesView
        ├── charge auth-front/PermissionsView
        ├── charge task-front/TaskList        ← task-front (:5002/assets/remoteEntry.js)
        ├── charge task-front/TaskForm
        └── charge analytics-front/Dashboard  ← analytics-front (:5003/assets/remoteEntry.js)
```

### Flux de chargement d'un remote

```
1. Utilisateur navigue vers /tasks
2. Vue Router active RemoteTaskList (defineAsyncComponent)
3. Le loader exécute : import('task-front/TaskList')
4. La federation runtime fetch http://localhost:5002/assets/remoteEntry.js
5. remoteEntry.js expose le manifeste des modules disponibles
6. Le runtime négocie les shared deps (vue, pinia, vue-router)
   → si déjà chargées dans le shell : réutilise les instances existantes
   → sinon : charge les versions du remote
7. Le chunk __federation_expose_TaskList-xxx.js est chargé
8. Le composant est rendu dans <RouterView> du shell
9. useAuthStore() dans TasksView retourne l'instance du shell
   (même store ID 'auth' + même instance Pinia)
```

### Gestion des erreurs

```vue
<!-- shell-app/src/App.vue -->
<Suspense>
  <template #default>
    <RouterView />          ← composant remote (peut échouer)
  </template>
  <template #fallback>
    <LoadingSpinner />      ← affiché pendant le chargement
  </template>
</Suspense>
```

`defineAsyncComponent` avec `errorComponent: RemoteError` capture :
- Timeout de chargement (remote éteint)
- Erreur réseau
- Module introuvable (contrat cassé)

### Partage de l'authStore

```
shell-app crée Pinia → useAuthStore() enregistre le store avec l'ID 'auth'
                                    ↓
task-front charge TasksView → appelle useAuthStore()
                                    ↓
Pinia vérifie : store 'auth' déjà enregistré dans cette instance Pinia ?
  → OUI (pinia est singleton) → retourne l'instance du shell
  → accès aux tokens, permissions, email du shell
```

La copie locale de `auth.ts` dans chaque remote sert uniquement au mode dev standalone (quand le remote tourne sans le shell). En production, la déduplication par store ID fait le travail.

---

## Décisions d'architecture

### Pourquoi `@originjs/vite-plugin-federation` plutôt que `@module-federation/vite` ?

`@module-federation/vite` (lib officielle MF portée par Zack Jackson) est plus proche de la spec Webpack 5, mais son support Vite est plus récent et son API est plus verbeuse. `@originjs/vite-plugin-federation` est plus mature sur le stack Vite + Vue 3 et sa configuration est plus simple pour les cas d'usage courants.

À réévaluer si le besoin de dev live (`vite dev` pour les remotes) devient prioritaire.

### Pourquoi les admin views (Users, Roles, Permissions) dans `auth-front` ?

Ces vues partagent la logique métier liée aux utilisateurs et aux permissions, qui appartient naturellement au domaine Auth. Elles utilisent les mêmes API (`/api/users`, `/api/roles`, `/api/permissions`) que le service `auth-service`. Regrouper par domaine métier plutôt que par route UI.

### Pourquoi ne pas extraire un package `shared` pour `client.ts` ?

`client.ts` est un thin wrapper autour de `fetch`. Le copier dans chaque app évite de créer une dépendance de workspace (`shared/`) qui complexifie le build et le versioning. Le fichier est si petit que la duplication est un moindre mal.

Si `client.ts` évolue (ajout de retry, interceptors, etc.), la bonne décision sera d'en faire un package workspace.

### Pourquoi `cssCodeSplit: false` ?

Avec `cssCodeSplit: true` (défaut Vite), les styles sont découpés en chunks correspondant aux composants. Quand un remote est chargé par le shell, ces chunks CSS peuvent être demandés dans un ordre non déterministe → flash de contenu non stylé (FOUC).

`cssCodeSplit: false` bundle tous les styles dans un seul fichier CSS par app → chargement atomique, pas de FOUC.

Coût : le premier chargement d'un remote charge ses styles en entier même si seul un composant est utilisé. Acceptable pour la taille des apps actuelles.
