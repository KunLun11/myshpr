# Frontend

Next.js 16 (App Router, Cache Components) + React 19 + Tailwind 4. Дизайн —
сплав Apple HIG и Mailchimp Pattern Library, см. `docs/design.md` и
`.github/instructions/frontend-design.instructions.md`.

## Запуск

```bash
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

Откройте <http://localhost:3000>. Браузер ходит на `/api/backend/*`, Next
проксирует это в FastAPI (`next.config.ts`), поэтому cookies остаются
first-party.

> Перед новыми паттернами прочитайте `AGENTS.md` и локальную документацию
> Next 16 в `node_modules/next/dist/docs/`. В этом проекте используются
> `cacheComponents`, `partialPrefetching` и `proxy.ts` (не `middleware.ts`).

## Структура

```text
app/(auth)      вход и регистрация
app/(student)   кабинет, мастер темы, продукт, работа
app/(teacher)   классы, дашборд, проверка тем, проекты
app/(admin)     админка школы и платформы
components/     UI и панели; components/ui — примитивы
lib/            API-клиент, auth, env, форматирование
types/api.ts    типы ответов backend
e2e/            Playwright-сценарии
```

## Проверки

```bash
npx tsc --noEmit
npm run lint
npm run build
```

## E2E (Playwright)

Сценарии в `e2e/journey.spec.ts` покрывают пять P0-потоков этапа 7. Нужен
запущенный и засеянный стек.

```bash
npm ci
npm run test:e2e:install        # один раз: браузер Chromium
npm run test:e2e                # E2E_BASE_URL=http://localhost:3000
npm run test:e2e:ui             # интерактивный режим
```

При падении сохраняются trace, скриншот и видео (`e2e-results/`), отчёт —
`playwright-report/`. В CI эти артефакты прикладываются к запуску workflow
`E2E`.

## Дизайн-правила (кратко)

- Токены в `app/globals.css`, не хардкодить цвета/радиусы/тайминги.
- Один акцент — Kale; Cavendish только для брендового highlight.
- Статус — всегда иконка + текст + цвет.
- Кликабельная зона ≥ 44px, видимый фокус-ring, skeleton вместо спиннеров.
- Поддерживать `prefers-reduced-motion` и `prefers-reduced-transparency`.
