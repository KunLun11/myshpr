"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { CheckboxField, Field, inputClass, textareaClass } from "@/components/admin/form-controls";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import type { AdminInterestArea, AdminProductCategory, ProductGuidance } from "@/types/api";

interface AreaDraft {
  slug: string;
  name: string;
  description: string;
  sort_order: string;
  is_active: boolean;
}

interface CategoryDraft extends AreaDraft {
  examples: string;
  must_have: string;
  common_mistakes: string;
  defense_tip: string;
}

const AREA_EMPTY: AreaDraft = {
  slug: "",
  name: "",
  description: "",
  sort_order: "100",
  is_active: true,
};

const CATEGORY_EMPTY: CategoryDraft = {
  ...AREA_EMPTY,
  examples: "",
  must_have: "",
  common_mistakes: "",
  defense_tip: "",
};

function toLines(values: string[] | undefined): string {
  return (values ?? []).join("\n");
}

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function areaDraft(area: AdminInterestArea): AreaDraft {
  return {
    slug: area.slug,
    name: area.name,
    description: area.description ?? "",
    sort_order: String(area.sort_order),
    is_active: area.is_active,
  };
}

function categoryDraft(category: AdminProductCategory): CategoryDraft {
  const guidance: ProductGuidance | null = category.guidance;
  return {
    slug: category.slug,
    name: category.name,
    description: category.description ?? "",
    sort_order: String(category.sort_order),
    is_active: category.is_active,
    examples: toLines(guidance?.examples),
    must_have: toLines(guidance?.must_have),
    common_mistakes: toLines(guidance?.common_mistakes),
    defense_tip: guidance?.defense_tip ?? "",
  };
}

function sortNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 100;
}

export function AdminReferences({
  areas,
  categories,
  canEdit,
}: {
  areas: AdminInterestArea[];
  categories: AdminProductCategory[];
  canEdit: boolean;
}) {
  const router = useRouter();
  const [area, setArea] = useState<AreaDraft>(AREA_EMPTY);
  const [category, setCategory] = useState<CategoryDraft>(CATEGORY_EMPTY);
  const [editingArea, setEditingArea] = useState<string | null>(null);
  const [areaEdit, setAreaEdit] = useState<AreaDraft>(AREA_EMPTY);
  const [editingCategory, setEditingCategory] = useState<string | null>(null);
  const [categoryEdit, setCategoryEdit] = useState<CategoryDraft>(CATEGORY_EMPTY);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateArea = <K extends keyof AreaDraft>(key: K, value: AreaDraft[K]) =>
    setArea((current) => ({ ...current, [key]: value }));
  // Local alias keeps the category form handlers terse.
  const setCategoryState = setCategory;

  function areaPayload(draft: AreaDraft) {
    return {
      slug: draft.slug,
      name: draft.name,
      description: draft.description || null,
      sort_order: sortNumber(draft.sort_order),
      is_active: draft.is_active,
    };
  }

  function categoryPayload(draft: CategoryDraft) {
    return {
      ...areaPayload(draft),
      guidance: {
        examples: parseLines(draft.examples),
        must_have: parseLines(draft.must_have),
        common_mistakes: parseLines(draft.common_mistakes),
        defense_tip: draft.defense_tip || null,
      },
    };
  }

  async function persist(action: () => Promise<unknown>, reset: () => void) {
    setPending(true);
    setError(null);
    try {
      await action();
      reset();
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  function createArea(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void persist(
      () => api.post("/admin/interest-areas", areaPayload(area)),
      () => setArea(AREA_EMPTY),
    );
  }

  function createCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void persist(
      () => api.post("/admin/product-categories", categoryPayload(category)),
      () => setCategory(CATEGORY_EMPTY),
    );
  }

  return (
    <div className="space-y-6">
      {error ? <Alert>{error}</Alert> : null}
      {canEdit ? null : (
        <Alert variant="info">
          Справочники платформы общие для всех школ. Их меняет суперадмин, здесь доступен
          только просмотр.
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Сферы интересов</CardTitle>
          <CardDescription>
            Выбор сферы — первый шаг мастера темы. Неактивные сферы скрываются у учеников.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {canEdit ? (
            <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={createArea}>
              <Field label="Код" htmlFor="area-slug" hint="латиница, цифры и дефис">
                <input
                  id="area-slug"
                  className={inputClass}
                  value={area.slug}
                  onChange={(event) => updateArea("slug", event.target.value)}
                  required
                  maxLength={100}
                  pattern="[a-z0-9]+(-[a-z0-9]+)*"
                />
              </Field>
              <Field label="Название" htmlFor="area-name">
                <input
                  id="area-name"
                  className={inputClass}
                  value={area.name}
                  onChange={(event) => updateArea("name", event.target.value)}
                  required
                  maxLength={200}
                />
              </Field>
              <Field label="Описание" htmlFor="area-description">
                <input
                  id="area-description"
                  className={inputClass}
                  value={area.description}
                  onChange={(event) => updateArea("description", event.target.value)}
                  maxLength={2000}
                />
              </Field>
              <Field label="Порядок" htmlFor="area-sort">
                <input
                  id="area-sort"
                  type="number"
                  className={inputClass}
                  value={area.sort_order}
                  onChange={(event) => updateArea("sort_order", event.target.value)}
                />
              </Field>
              <CheckboxField
                id="area-active"
                label="Активна"
                checked={area.is_active}
                onChange={(value) => updateArea("is_active", value)}
              />
              <div className="flex items-end">
                <Button type="submit" disabled={pending || area.name.trim().length === 0}>
                  {pending ? "Сохраняем…" : "Добавить сферу"}
                </Button>
              </div>
            </form>
          ) : null}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Код</th>
                  <th className="py-2 pr-4 font-medium">Название</th>
                  <th className="py-2 pr-4 font-medium">Порядок</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  {canEdit ? <th className="py-2 font-medium">Действия</th> : null}
                </tr>
              </thead>
              <tbody>
                {areas.map((item) =>
                  editingArea === item.id ? (
                    <tr key={item.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Код сферы"
                          className={inputClass}
                          value={areaEdit.slug}
                          onChange={(event) =>
                            setAreaEdit((current) => ({ ...current, slug: event.target.value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название сферы"
                          className={inputClass}
                          value={areaEdit.name}
                          onChange={(event) =>
                            setAreaEdit((current) => ({ ...current, name: event.target.value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Порядок"
                          type="number"
                          className={inputClass}
                          value={areaEdit.sort_order}
                          onChange={(event) =>
                            setAreaEdit((current) => ({
                              ...current,
                              sort_order: event.target.value,
                            }))
                          }
                        />
                        <CheckboxField
                          id={`area-edit-active-${item.id}`}
                          label="Активна"
                          checked={areaEdit.is_active}
                          onChange={(value) =>
                            setAreaEdit((current) => ({ ...current, is_active: value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4" />
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            disabled={pending}
                            onClick={() =>
                              void persist(
                                () =>
                                  api.patch(
                                    `/admin/interest-areas/${item.id}`,
                                    areaPayload(areaEdit),
                                  ),
                                () => setEditingArea(null),
                              )
                            }
                          >
                            Сохранить
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingArea(null)}
                          >
                            Отмена
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 font-mono text-xs">{item.slug}</td>
                      <td className="py-3 pr-4">
                        <div className="font-medium">{item.name}</div>
                        <div className="text-[var(--muted-foreground)]">
                          {item.description ?? "—"}
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">{item.sort_order}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={item.is_active ? "success" : "secondary"}>
                          {item.is_active ? "Активна" : "Скрыта"}
                        </Badge>
                      </td>
                      {canEdit ? (
                        <td className="py-3">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingArea(item.id);
                              setAreaEdit(areaDraft(item));
                              setError(null);
                            }}
                          >
                            Изменить
                          </Button>
                        </td>
                      ) : null}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Категории продукта</CardTitle>
          <CardDescription>
            Подсказки для помощника продукта: примеры, обязательные элементы и частые ошибки.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {canEdit ? (
            <form className="grid gap-4 md:grid-cols-2" onSubmit={createCategory}>
              <Field label="Код" htmlFor="category-slug" hint="латиница, цифры и дефис">
                <input
                  id="category-slug"
                  className={inputClass}
                  value={category.slug}
                  onChange={(event) => setCategoryState((current) => ({ ...current, slug: event.target.value }))}
                  required
                  maxLength={100}
                  pattern="[a-z0-9]+(-[a-z0-9]+)*"
                />
              </Field>
              <Field label="Название" htmlFor="category-name">
                <input
                  id="category-name"
                  className={inputClass}
                  value={category.name}
                  onChange={(event) => setCategoryState((current) => ({ ...current, name: event.target.value }))}
                  required
                  maxLength={200}
                />
              </Field>
              <Field label="Описание" htmlFor="category-description" className="md:col-span-2">
                <input
                  id="category-description"
                  className={inputClass}
                  value={category.description}
                  onChange={(event) =>
                    setCategoryState((current) => ({ ...current, description: event.target.value }))
                  }
                  maxLength={2000}
                />
              </Field>
              <Field label="Примеры" htmlFor="category-examples" hint="по одному на строку">
                <textarea
                  id="category-examples"
                  className={textareaClass}
                  value={category.examples}
                  onChange={(event) =>
                    setCategoryState((current) => ({ ...current, examples: event.target.value }))
                  }
                />
              </Field>
              <Field label="Обязательные элементы" htmlFor="category-must" hint="по одному на строку">
                <textarea
                  id="category-must"
                  className={textareaClass}
                  value={category.must_have}
                  onChange={(event) =>
                    setCategoryState((current) => ({ ...current, must_have: event.target.value }))
                  }
                />
              </Field>
              <Field label="Частые ошибки" htmlFor="category-mistakes" hint="по одной на строку">
                <textarea
                  id="category-mistakes"
                  className={textareaClass}
                  value={category.common_mistakes}
                  onChange={(event) =>
                    setCategoryState((current) => ({
                      ...current,
                      common_mistakes: event.target.value,
                    }))
                  }
                />
              </Field>
              <Field label="Совет к защите" htmlFor="category-defense">
                <input
                  id="category-defense"
                  className={inputClass}
                  value={category.defense_tip}
                  onChange={(event) =>
                    setCategoryState((current) => ({ ...current, defense_tip: event.target.value }))
                  }
                  maxLength={500}
                />
              </Field>
              <Field label="Порядок" htmlFor="category-sort">
                <input
                  id="category-sort"
                  type="number"
                  className={inputClass}
                  value={category.sort_order}
                  onChange={(event) =>
                    setCategoryState((current) => ({ ...current, sort_order: event.target.value }))
                  }
                />
              </Field>
              <CheckboxField
                id="category-active"
                label="Активна"
                checked={category.is_active}
                onChange={(value) =>
                  setCategoryState((current) => ({ ...current, is_active: value }))
                }
              />
              <div className="flex items-end">
                <Button type="submit" disabled={pending || category.name.trim().length === 0}>
                  {pending ? "Сохраняем…" : "Добавить категорию"}
                </Button>
              </div>
            </form>
          ) : null}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Код</th>
                  <th className="py-2 pr-4 font-medium">Название</th>
                  <th className="py-2 pr-4 font-medium">Подсказки</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  {canEdit ? <th className="py-2 font-medium">Действия</th> : null}
                </tr>
              </thead>
              <tbody>
                {categories.map((item) =>
                  editingCategory === item.id ? (
                    <tr key={item.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Код категории"
                          className={inputClass}
                          value={categoryEdit.slug}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({ ...current, slug: event.target.value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название категории"
                          className={inputClass}
                          value={categoryEdit.name}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({ ...current, name: event.target.value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <textarea
                          aria-label="Примеры"
                          className={textareaClass}
                          value={categoryEdit.examples}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({
                              ...current,
                              examples: event.target.value,
                            }))
                          }
                        />
                        <textarea
                          aria-label="Обязательные элементы"
                          className={textareaClass}
                          value={categoryEdit.must_have}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({
                              ...current,
                              must_have: event.target.value,
                            }))
                          }
                        />
                        <textarea
                          aria-label="Частые ошибки"
                          className={textareaClass}
                          value={categoryEdit.common_mistakes}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({
                              ...current,
                              common_mistakes: event.target.value,
                            }))
                          }
                        />
                        <input
                          aria-label="Совет к защите"
                          className={inputClass}
                          value={categoryEdit.defense_tip}
                          onChange={(event) =>
                            setCategoryEdit((current) => ({
                              ...current,
                              defense_tip: event.target.value,
                            }))
                          }
                        />
                        <div className="mt-1 flex items-center gap-3">
                          <CheckboxField
                            id={`category-edit-active-${item.id}`}
                            label="Активна"
                            checked={categoryEdit.is_active}
                            onChange={(value) =>
                              setCategoryEdit((current) => ({ ...current, is_active: value }))
                            }
                          />
                          <input
                            aria-label="Порядок"
                            type="number"
                            className={inputClass}
                            value={categoryEdit.sort_order}
                            onChange={(event) =>
                              setCategoryEdit((current) => ({
                                ...current,
                                sort_order: event.target.value,
                              }))
                            }
                          />
                        </div>
                      </td>
                      <td className="py-3 pr-4" />
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            disabled={pending}
                            onClick={() =>
                              void persist(
                                () =>
                                  api.patch(
                                    `/admin/product-categories/${item.id}`,
                                    categoryPayload(categoryEdit),
                                  ),
                                () => setEditingCategory(null),
                              )
                            }
                          >
                            Сохранить
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingCategory(null)}
                          >
                            Отмена
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 font-mono text-xs">{item.slug}</td>
                      <td className="py-3 pr-4">
                        <div className="font-medium">{item.name}</div>
                        <div className="text-[var(--muted-foreground)]">
                          {item.description ?? "—"}
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {item.guidance
                          ? `${item.guidance.examples.length} примеров · ${item.guidance.must_have.length} требований`
                          : "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={item.is_active ? "success" : "secondary"}>
                          {item.is_active ? "Активна" : "Скрыта"}
                        </Badge>
                      </td>
                      {canEdit ? (
                        <td className="py-3">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingCategory(item.id);
                              setCategoryEdit(categoryDraft(item));
                              setError(null);
                            }}
                          >
                            Изменить
                          </Button>
                        </td>
                      ) : null}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
