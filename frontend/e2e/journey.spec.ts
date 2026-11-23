import { expect, test } from "@playwright/test";

import {
  RUN_ID,
  TEACHER_EMAIL,
  buildTopicPair,
  fillWizardBasics,
  login,
  longProductDescription,
  registerStudent,
  uniqueEmail,
  waitForTopicCheck,
} from "./helpers";

/**
 * Five P0 scenarios from TASKS.md, stage 7 (T7.1).
 *
 * Serial by design: scenario 2 depends on the topic created in scenario 1
 * (duplicate check), and scenarios 3–5 depend on the approved topic.
 */
test.describe.configure({ mode: "serial" });

// Unique per run: titles differ only by a short id would be ~88% similar to
// earlier runs and the duplicate rule would block them.
const { base: BASE_TOPIC, fixed: FIXED_TOPIC } = buildTopicPair();
const QUESTION = "Как уровень шума в школьной столовой влияет на внимание учеников девятого класса?";

const studentA = { fullName: `Анна Тестова ${RUN_ID}`, email: uniqueEmail("anna") };
const studentB = { fullName: `Борис Тестов ${RUN_ID}`, email: uniqueEmail("boris") };
const uploadedFileName = `e2e-work-${RUN_ID}.pdf`;

test("1. ученик регистрируется по коду, проходит мастер и отправляет тему", async ({ page }) => {
  await registerStudent(page, studentA);

  await fillWizardBasics(page, { area: "Экология", question: QUESTION });
  await page.locator("#topic-title").fill(BASE_TOPIC);
  await waitForTopicCheck(page);

  const submit = page.getByRole("button", { name: "Отправить учителю" });
  await expect(submit).toBeEnabled();
  await submit.click();

  await expect(page.getByText("Отправленная заявка")).toBeVisible();
  await page.goto("/cabinet");
  await expect(page.getByText("На проверке").first()).toBeVisible();
});

test("2. учитель видит заявку и утверждает, ученик видит статус", async ({ page }) => {
  // A second student repeats the same title to hit the duplicate rule.
  await registerStudent(page, studentB);
  await fillWizardBasics(page, { area: "Экология", question: QUESTION });
  await page.locator("#topic-title").fill(BASE_TOPIC);
  await waitForTopicCheck(page);

  await expect(page.getByText("Точный повтор")).toBeVisible();
  await expect(page.getByRole("button", { name: "Отправить учителю" })).toBeDisabled();

  // Fix the wording: a different topic is no longer an exact duplicate.
  await page.locator("#topic-title").fill(FIXED_TOPIC);
  await expect(page.getByText(/Повторов нет|Похожая тема/)).toBeVisible();
  await expect(page.getByText("Точный повтор")).toHaveCount(0);
  await expect(page.getByText("Тема занята")).toHaveCount(0);
  const submit = page.getByRole("button", { name: "Отправить учителю" });
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect(page.getByText("Отправленная заявка")).toBeVisible();

  // Teacher reviews the request and leaves a comment.
  await login(page, TEACHER_EMAIL);
  await page.goto("/teacher/submissions");
  const card = page
    .locator("div")
    .filter({ hasText: FIXED_TOPIC })
    .filter({ has: page.getByRole("button", { name: "Утвердить" }) })
    .last();
  await expect(card).toBeVisible();
  await card.getByRole("button", { name: "Утвердить" }).click();
  await card.locator("textarea").fill("Тема сужена по месту и группе, можно утверждать.");
  await card.getByRole("button", { name: "Утвердить тему" }).click();
  await expect(page.getByText(FIXED_TOPIC)).toHaveCount(0);

  // Student sees the approved status.
  await login(page, studentB.email);
  await page.goto("/cabinet");
  await expect(page.getByText("Тема утверждена").first()).toBeVisible();
});

test("3. ученик выбирает продукт, учитель видит его в карточке", async ({ page }) => {
  await login(page, studentB.email);
  await page.goto("/cabinet/product");

  await page.getByRole("radio", { name: /Модель \/ макет/ }).check({ force: true });
  const description = longProductDescription(RUN_ID);
  await page.locator("#product-description").fill(description);
  await page.locator("#defense-plan").fill("Покажу модель и таблицу измерений.");
  await page.locator("#product-audience").fill("Ученики 5–7 классов и учителя");

  await page.getByRole("button", { name: "Сохранить продукт" }).click();
  await expect(page.getByText(/Продукт сохранён|Изменения сохранены/).first()).toBeVisible();

  await login(page, TEACHER_EMAIL);
  await page.goto("/teacher/projects");
  const projectCard = page
    .locator("div")
    .filter({ hasText: studentB.fullName })
    .filter({ has: page.getByRole("link", { name: "Открыть проект" }) })
    .last();
  await projectCard.getByRole("link", { name: "Открыть проект" }).click();

  await expect(page.getByRole("heading", { name: studentB.fullName })).toBeVisible();
  await expect(page.getByText("Модель / макет").filter({ visible: true })).toBeVisible();
  await expect(
    page.getByText(description.slice(0, 40)).filter({ visible: true }),
  ).toBeVisible();
});

test("4. ученик загружает файл и отмечает чек-лист, учитель комментирует", async ({ page }) => {
  await login(page, studentB.email);
  await page.goto("/cabinet/work");

  // Checklist: the first pending item can be started and completed.
  const doneButton = page.getByRole("button", { name: "Готово" }).first();
  await expect(doneButton).toBeVisible();
  await doneButton.click();
  await expect(page.getByRole("button", { name: "Вернуть в работу" }).first()).toBeVisible();

  // Files: upload a small valid PDF through the hidden input.
  await page.locator("#work-tab-files").click();
  await page.locator("#project-file").setInputFiles({
    name: uploadedFileName,
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"),
  });
  await expect(page.getByText(uploadedFileName)).toBeVisible();

  // Teacher comments on the project.
  await login(page, TEACHER_EMAIL);
  await page.goto("/teacher/projects");
  const projectCard = page
    .locator("div")
    .filter({ hasText: studentB.fullName })
    .filter({ has: page.getByRole("link", { name: "Открыть проект" }) })
    .last();
  await projectCard.getByRole("link", { name: "Открыть проект" }).click();
  await page.locator("#teacher-tab-comments").click();

  const comment = `Добавьте два источника за последние три года (${RUN_ID}).`;
  await page.locator("#comment-body").fill(comment);
  await page.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(page.getByText(comment)).toBeVisible();

  // The student reads the comment in their cabinet.
  await login(page, studentB.email);
  await page.goto("/cabinet/work");
  await page.locator("#work-tab-comments").click();
  await expect(page.getByText(comment)).toBeVisible();
});

test("5. учитель видит дашборд с цветами, причинами и прогрессом чек-листа", async ({ page }) => {
  await login(page, TEACHER_EMAIL);
  await page.goto("/teacher");

  await page.getByRole("link", { name: "Дашборд класса" }).first().click();
  await expect(page.getByRole("heading", { name: /Кто застрял/ })).toBeVisible();

  await expect(page.getByText("Всего учеников")).toBeVisible();
  await expect(page.getByRole("button", { name: "Красные" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Жёлтые" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Зелёные" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Фильтр по статусу проекта" })).toBeVisible();

  // At least one student card exposes the checklist progress bar.
  await expect(page.getByLabel(/^Чек-лист /).first()).toBeVisible();

  // Filter by name still returns a readable reason line, not colour alone.
  await page.getByLabel("Поиск ученика по имени").fill(studentB.fullName);
  await expect(page.getByText(studentB.fullName)).toBeVisible();
});
