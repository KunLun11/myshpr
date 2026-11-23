"use client";

import { ClipboardCheck, MessageSquare, Paperclip } from "lucide-react";
import { useState } from "react";

import { ChecklistPanel } from "@/components/checklist-panel";
import { CommentsPanel } from "@/components/comments-panel";
import { FilesPanel } from "@/components/files-panel";
import { cn } from "@/lib/utils";
import type { ProjectChecklist, ProjectFile, TeacherComment } from "@/types/api";

type TabKey = "checklist" | "files" | "comments";

const TABS: { key: TabKey; label: string; Icon: typeof ClipboardCheck }[] = [
  { key: "checklist", label: "Чек-лист", Icon: ClipboardCheck },
  { key: "files", label: "Файлы", Icon: Paperclip },
  { key: "comments", label: "Комментарии", Icon: MessageSquare },
];

export function WorkTabs({
  checklist,
  files,
  comments,
}: {
  checklist: ProjectChecklist;
  files: ProjectFile[];
  comments: TeacherComment[];
}) {
  const [active, setActive] = useState<TabKey>("checklist");

  const counts: Record<TabKey, string> = {
    checklist: `${checklist.progress.percent}%`,
    files: String(files.length),
    comments: String(comments.length),
  };

  return (
    <div className="space-y-4">
      <div
        role="tablist"
        aria-label="Разделы работы над проектом"
        className="flex flex-wrap gap-1 rounded-full bg-[var(--muted)] p-1"
      >
        {TABS.map((tab) => {
          const selected = active === tab.key;
          const Icon = tab.Icon;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              id={`work-tab-${tab.key}`}
              aria-selected={selected}
              aria-controls={`work-panel-${tab.key}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(tab.key)}
              onKeyDown={(event) => {
                if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") {
                  return;
                }
                event.preventDefault();
                const index = TABS.findIndex((item) => item.key === active);
                const nextIndex =
                  event.key === "ArrowRight"
                    ? (index + 1) % TABS.length
                    : (index - 1 + TABS.length) % TABS.length;
                const next = TABS[nextIndex];
                setActive(next.key);
                document.getElementById(`work-tab-${next.key}`)?.focus();
              }}
              className={cn(
                "inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-full px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                selected
                  ? "bg-[var(--card)] text-[var(--foreground)] shadow-[var(--shadow-soft)]"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {tab.label}
              <span className="rounded-full bg-[var(--background)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
                {counts[tab.key]}
              </span>
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`work-panel-${active}`}
        aria-labelledby={`work-tab-${active}`}
        tabIndex={0}
        className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
      >
        {active === "checklist" ? (
          <ChecklistPanel initialChecklist={checklist} mode="student" />
        ) : active === "files" ? (
          <FilesPanel initialFiles={files} mode="student" />
        ) : (
          <CommentsPanel initialComments={comments} mode="student" />
        )}
      </div>
    </div>
  );
}
