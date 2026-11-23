import { expect, type BrowserContext, type Page } from "@playwright/test";

export const TEACHER_EMAIL = process.env.E2E_TEACHER_EMAIL ?? "teacher@example.com";
export const PASSWORD = process.env.E2E_PASSWORD ?? "student123";
export const INVITE_CODE = process.env.E2E_INVITE_CODE ?? "DEMO2026";

// One id per run keeps titles and emails unique against a persistent database.
export const RUN_ID = process.env.E2E_RUN_ID ?? Date.now().toString(36);

export function uniqueEmail(prefix: string): string {
  return `${prefix}.${RUN_ID}@example.com`;
}

/**
 * Build a topic that is structurally distinct from previous runs.
 *
 * A title that only differs in a short run id is ~88% similar to the title
 * approved by an earlier run (pg_trgm), so the duplicate rule blocks it. Pick
 * different content words per run instead.
 */
export function buildDistinctTopic(tag = "topic"): string {
  // Every option carries a narrowing signal (place / group / method) so the
  // broadness score stays well above the "too broad" threshold.
  const verbs = ["Сравнение", "Измерение", "Тестирование", "Наблюдение", "Моделирование"];
  const subjects = [
    "шума",
    "освещённости",
    "влажности воздуха",
    "температуры",
    "качества воды",
    "скорости чтения",
  ];
  const places = [
    "в школьной столовой",
    "в школьной библиотеке",
    "в школьном спортзале",
    "в школьной теплице",
    "в районной библиотеке",
    "в школе на уроках физики",
  ];
  const groups = [
    "у девятиклассников",
    "у пятиклассников",
    "у младших школьников",
    "у учителей",
    "у учеников девятых классов",
  ];
  let hash = 0;
  for (const char of `${RUN_ID}${tag}`) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  const verb = verbs[hash % verbs.length];
  const subject = subjects[(hash >>> 3) % subjects.length];
  const place = places[(hash >>> 6) % places.length];
  const group = groups[(hash >>> 9) % groups.length];
  return `${verb} ${subject} ${place} ${group}`;
}

/** Two different, run-unique topics: one to submit, one to fix a duplicate. */
export function buildTopicPair(): { base: string; fixed: string } {
  const base = buildDistinctTopic("base");
  let fixed = buildDistinctTopic("fixed");
  let salt = 0;
  while (fixed === base) {
    salt += 1;
    fixed = buildDistinctTopic(`fixed-${salt}`);
  }
  return { base, fixed };
}

export async function registerStudent(
  page: Page,
  options: { fullName: string; email: string },
): Promise<void> {
  await page.goto(`/register?code=${INVITE_CODE}`);
  await page.locator("#invite-code").fill(INVITE_CODE);
  await page.locator("#full-name").fill(options.fullName);
  await page.locator("#email").fill(options.email);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Зарегистрироваться" }).click();
  await expect(page).toHaveURL(/\/cabinet$/);
}

type StorageState = Awaited<ReturnType<BrowserContext["storageState"]>>;

// Reuse a session per user within one run: logging in through the UI for every
// test would trip the login rate limit (10/min) on back-to-back runs.
const authCache = new Map<string, StorageState>();

export async function login(
  page: Page,
  email: string,
  password: string = PASSWORD,
): Promise<void> {
  const cached = authCache.get(email);
  if (cached) {
    await page.context().addCookies(cached.cookies);
    await page.goto("/");
    return;
  }

  await page.goto("/login");
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(password);
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  authCache.set(email, await page.context().storageState());
}

/** Fill steps 1 and 2 of the topic wizard (area + research question). */
export async function fillWizardBasics(
  page: Page,
  options: { area?: string; question: string },
): Promise<void> {
  await page.goto("/cabinet/topic");
  await page.getByRole("radio", { name: new RegExp(options.area ?? "Экология") }).check({
    force: true,
  });
  await page.getByRole("button", { name: "Далее" }).click();
  await page.locator("#research-question").fill(options.question);
  await page.getByRole("button", { name: "Далее" }).click();
}

/** Wait until the debounced server-side check has rendered a verdict. */
export async function waitForTopicCheck(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { name: "Повтор темы" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ширина темы" })).toBeVisible();
}

export function longProductDescription(seed: string): string {
  return (
    `Соберу действующую модель устройства для проекта «${seed}», измерю результат ` +
    "на двух режимах работы и подготовлю короткий отчёт с таблицей измерений. " +
    "Модель покажу на защите и объясню, как она отвечает на исследовательский вопрос, " +
    "какие ограничения есть у решения и что можно улучшить в следующей версии."
  );
}
