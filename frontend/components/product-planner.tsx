"use client";

import {
  ArrowRight,
  BookOpen,
  Box,
  CalendarDays,
  CheckCircle2,
  Code2,
  Cpu,
  FlaskConical,
  Lightbulb,
  LoaderCircle,
  LockKeyhole,
  PackageCheck,
  Save,
  Shapes,
  Video,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  ProductCategory,
  ProductState,
  Project,
  ProjectStatus,
} from "@/types/api";

const TOPIC_APPROVED = new Set<ProjectStatus>([
  "topic_approved",
  "product_draft",
  "product_defined",
  "in_progress",
  "ready_for_defense",
  "defended",
]);

const CATEGORY_ICONS: Record<string, typeof Box> = {
  model: Box,
  software: Code2,
  research: FlaskConical,
  media: Video,
  event: CalendarDays,
  handbook: BookOpen,
  device: Cpu,
  other: Shapes,
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.";
}

export function ProductPlanner({
  project,
  categories,
  initialProduct,
}: {
  project: Project | null;
  categories: ProductCategory[];
  initialProduct: ProductState | null;
}) {
  const router = useRouter();
  const [categoryId, setCategoryId] = useState(initialProduct?.category?.id ?? "");
  const [description, setDescription] = useState(initialProduct?.description ?? "");
  const [defensePlan, setDefensePlan] = useState(initialProduct?.brief?.defense_plan ?? "");
  const [audience, setAudience] = useState(initialProduct?.brief?.audience ?? "");
  const [product, setProduct] = useState<ProductState | null>(initialProduct);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = (product?.status ?? project?.status ?? "idea") as ProjectStatus;
  const topicApproved = Boolean(project && TOPIC_APPROVED.has(project.status));
  const selected = categories.find((category) => category.id === categoryId) ?? null;
  const guidance = selected?.guidance ?? product?.guidance ?? null;
  const min = product?.requirements.description_min ?? 120;
  const max = product?.requirements.description_max ?? 1500;
  const length = description.trim().length;
  const lengthValid = length >= min && length <= max;
  const canSave = topicApproved && Boolean(categoryId) && lengthValid && !saving;

  if (!topicApproved) {
    return (
      <div className="space-y-6">
        <header className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-3xl font-semibold tracking-tight">Продукт проекта</h1>
            <ProjectStatusBadge status={status} />
          </div>
          <p className="max-w-[70ch] text-[var(--muted-foreground)]">
            Продукт — это то, что вы покажете на защите. Он выбирается после того,
            как учитель утвердит тему.
          </p>
        </header>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <LockKeyhole className="size-5 text-[var(--warning)]" aria-hidden="true" />
              Сначала утвердите тему
            </CardTitle>
            <CardDescription>
              Пока тема не утверждена, продукт выбрать нельзя. Вернитесь в мастер темы,
              если черновик ещё не отправлен.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Link href="/cabinet/topic" className={buttonVariants()}>
              Открыть мастер темы
              <ArrowRight aria-hidden="true" />
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const result = await api.patch<ProductState>("/me/project/product", {
        product_category_id: categoryId,
        product_description: description,
        defense_plan: defensePlan.trim() || null,
        audience: audience.trim() || null,
      });
      setProduct(result);
      setSaved(true);
      router.refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Продукт проекта</h1>
          <ProjectStatusBadge status={status} />
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Выберите категорию, опишите результат и решите, что покажете на защите.
          Черновик можно менять в любое время.
        </p>
      </header>

      {product?.product_defined_at ? (
        <Alert variant="success" className="flex flex-wrap items-center justify-between gap-3">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="size-4" aria-hidden="true" />
            Продукт сохранён. Теперь можно переходить к работе над проектом.
          </span>
          <Link href="/cabinet/work" className={buttonVariants({ size: "sm" })}>
            Открыть работу
            <ArrowRight aria-hidden="true" />
          </Link>
        </Alert>
      ) : null}

      {saved ? (
        <Alert variant="success" className="flex items-center gap-2">
          <CheckCircle2 className="size-4" aria-hidden="true" />
          Изменения сохранены.
        </Alert>
      ) : null}
      {error ? <Alert>{error}</Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <PackageCheck className="size-5 text-[var(--primary)]" aria-hidden="true" />
            1. Категория продукта
          </CardTitle>
          <CardDescription>
            Категория задаёт формат результата: модель, исследование, приложение, видео и т.д.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <fieldset>
            <legend className="sr-only">Категория продукта</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {categories.map((category) => {
                const Icon = CATEGORY_ICONS[category.slug] ?? Shapes;
                const active = category.id === categoryId;
                return (
                  <label
                    key={category.id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-[var(--radius-md)] border p-4 transition-colors focus-within:ring-2 focus-within:ring-[var(--ring)]",
                      active
                        ? "border-[var(--primary)] bg-[var(--info-soft)]"
                        : "border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]",
                    )}
                  >
                    <input
                      type="radio"
                      name="product-category"
                      value={category.id}
                      checked={active}
                      onChange={() => {
                        setCategoryId(category.id);
                        setSaved(false);
                      }}
                      className="sr-only"
                    />
                    <span
                      className={cn(
                        "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full",
                        active
                          ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                          : "bg-[var(--muted)] text-[var(--muted-foreground)]",
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <span className="space-y-1">
                      <span className="flex items-center gap-2 font-medium">
                        {category.name}
                        {active ? (
                          <CheckCircle2 className="size-4 text-[var(--primary)]" aria-hidden="true" />
                        ) : null}
                      </span>
                      {category.description ? (
                        <span className="block text-sm text-[var(--muted-foreground)]">
                          {category.description}
                        </span>
                      ) : null}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
          {categories.length === 0 ? (
            <Alert variant="info">
              Справочник категорий пуст. Попросите администратора школы заполнить его.
            </Alert>
          ) : null}

          {guidance ? (
            <div className="rounded-[var(--radius-md)] bg-[var(--muted)] p-4 text-sm">
              <p className="flex items-center gap-2 font-medium">
                <Lightbulb className="size-4 text-[var(--primary)]" aria-hidden="true" />
                Подсказки для категории «{selected?.name ?? product?.category?.name ?? ""}»
              </p>
              {guidance.examples.length > 0 ? (
                <p className="mt-2 text-[var(--muted-foreground)]">
                  Примеры: {guidance.examples.join("; ")}
                </p>
              ) : null}
              {guidance.must_have.length > 0 ? (
                <p className="mt-1 text-[var(--muted-foreground)]">
                  Обязательно: {guidance.must_have.join("; ")}
                </p>
              ) : null}
              {guidance.common_mistakes.length > 0 ? (
                <p className="mt-1 text-[var(--muted-foreground)]">
                  Частая ошибка: {guidance.common_mistakes.join("; ")}
                </p>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">2. Описание продукта</CardTitle>
          <CardDescription>
            Что именно вы создадите? Опишите результат так, чтобы его можно было представить
            на защите.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <label htmlFor="product-description" className="sr-only">
            Описание продукта
          </label>
          <textarea
            id="product-description"
            value={description}
            onChange={(event) => {
              setDescription(event.target.value);
              setSaved(false);
            }}
            rows={6}
            maxLength={max}
            aria-describedby="product-description-help"
            className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            placeholder="Например: соберу действующую модель фильтра для воды и измерю, насколько она снижает мутность."
          />
          <div
            id="product-description-help"
            className="flex flex-wrap items-center justify-between gap-2 text-xs"
          >
            <span className={lengthValid ? "text-[var(--muted-foreground)]" : "text-[var(--warning)]"}>
              От {min} до {max} символов. Сейчас {length}.
            </span>
            <span className="text-[var(--muted-foreground)]">
              {length}/{max}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">3. Что покажете на защите?</CardTitle>
          <CardDescription>
            Опишите демонстрацию и аудиторию. Это необязательно, но помогает подготовиться.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="defense-plan" className="text-sm font-medium">
              План показа
            </label>
            <textarea
              id="defense-plan"
              value={defensePlan}
              onChange={(event) => {
                setDefensePlan(event.target.value);
                setSaved(false);
              }}
              rows={3}
              maxLength={1000}
              className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              placeholder="Например: покажу модель, результаты измерений и сравню их с гипотезой."
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="product-audience" className="text-sm font-medium">
              Для кого продукт
            </label>
            <input
              id="product-audience"
              value={audience}
              onChange={(event) => {
                setAudience(event.target.value);
                setSaved(false);
              }}
              maxLength={500}
              className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              placeholder="Например: ученики 5–7 классов и учителя"
            />
          </div>

          {guidance?.defense_tip ? (
            <div className="rounded-[var(--radius-md)] bg-[var(--brand)] px-4 py-3 text-sm text-[var(--brand-foreground)]">
              <p className="flex items-start gap-2">
                <Lightbulb className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                {guidance.defense_tip}
              </p>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleSave} disabled={!canSave}>
          {saving ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <Save aria-hidden="true" />
          )}
          {product?.product_defined_at ? "Сохранить изменения" : "Сохранить продукт"}
        </Button>
        {!lengthValid && description.length > 0 ? (
          <Badge variant="warning">Описание ещё не готово</Badge>
        ) : null}
        {!categoryId ? <Badge variant="secondary">Выберите категорию</Badge> : null}
      </div>
    </div>
  );
}
