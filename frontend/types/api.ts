/** Shared API types mirroring the FastAPI schemas. */

export type UserRole = "student" | "teacher" | "school_admin" | "super_admin";

export interface SchoolBrief {
  id: string;
  name: string;
}

export interface ClassBrief {
  id: string;
  grade: number;
  label: string;
  academic_year_name: string | null;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  school: SchoolBrief | null;
  class: ClassBrief | null;
  must_change_password: boolean;
}

export interface ClassSummary {
  id: string;
  grade: number;
  label: string;
  academic_year_id: string;
  academic_year_name: string | null;
  curator_id: string | null;
  students_count: number;
}

export interface StudentSummary {
  user_id: string;
  full_name: string;
  email: string;
  class_id: string;
}

export interface Invite {
  id: string;
  code: string;
  expires_at: string;
  max_uses: number | null;
  uses_count: number;
  register_url: string;
}

/* --- Stage 3: topic wizard ------------------------------------------------ */

export type CheckLevel = "ok" | "warn" | "block";

export interface InterestArea {
  id: string;
  slug: string;
  name: string;
  description: string | null;
}

export interface CheckMessage {
  field: string;
  message: string;
}

export interface DuplicateMatch {
  source: "registry" | "pending";
  id: string;
  title: string;
  score: number;
}

export interface DuplicateCheck {
  level: CheckLevel;
  exact: boolean;
  best_score: number;
  matches: DuplicateMatch[];
}

export interface BroadnessCheck {
  score: number;
  level: CheckLevel;
  reasons: string[];
  suggestions: string[];
}

export interface TopicCheck {
  title: string;
  normalized_title: string;
  errors: CheckMessage[];
  warnings: CheckMessage[];
  duplicate: DuplicateCheck;
  broadness: BroadnessCheck;
  can_submit: boolean;
}

export interface TopicDraft {
  id: string;
  status: string;
  title: string;
  normalized_title: string;
  research_question: string;
  duplicate_score: number | null;
  broadness_score: number | null;
  broadness_reasons: string[];
  review_comment: string | null;
  reviewed_at: string | null;
  updated_at: string;
}

export type ProjectStatus =
  | "idea"
  | "topic_draft"
  | "topic_submitted"
  | "topic_approved"
  | "product_draft"
  | "product_defined"
  | "in_progress"
  | "ready_for_defense"
  | "defended"
  | "archived";

export interface Project {
  id: string;
  status: ProjectStatus;
  class_id: string;
  class_label: string;
  class_grade: number;
  academic_year_id: string;
  academic_year_name: string | null;
  interest_area: InterestArea | null;
  research_question: string | null;
  topic_approved_at: string | null;
  product_defined_at: string | null;
  created_at: string;
  updated_at: string;
  topic: TopicDraft | null;
  next_checkpoint: NextCheckpoint | null;
}

export interface ProjectPatchResponse {
  project: Project;
  warnings: CheckMessage[];
}

export interface Submission {
  id: string;
  project_id: string;
  status: string;
  title: string;
  research_question: string;
  student_full_name: string;
  class_label: string;
  interest_area_name: string | null;
  submitted_at: string;
  duplicate_score: number | null;
  duplicate_level: CheckLevel;
  duplicate_of_title: string | null;
  broadness_score: number | null;
  broadness_level: CheckLevel;
  broadness_reasons: string[];
  review_comment: string | null;
  reviewed_at: string | null;
}

export interface RegistryTopic {
  id: string;
  title: string;
  research_question: string | null;
  author_full_name: string | null;
  interest_area_name: string | null;
  academic_year_name: string | null;
  approved_at: string;
}

/* --- Stage 4: product, work, comments ------------------------------------- */

export interface ProductGuidance {
  examples: string[];
  must_have: string[];
  common_mistakes: string[];
  defense_tip: string | null;
}

export interface ProductCategory {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  guidance: ProductGuidance | null;
}

export interface ProductBrief {
  defense_plan: string | null;
  audience: string | null;
}

export interface ProductState {
  project_id: string;
  status: ProjectStatus;
  category: ProductCategory | null;
  description: string | null;
  brief: ProductBrief | null;
  guidance: ProductGuidance | null;
  requirements: { description_min: number; description_max: number };
  product_defined_at: string | null;
}

export type FileKind =
  | "research_draft"
  | "final_work"
  | "presentation"
  | "product_media"
  | "other";

export type FileStatus = "uploaded" | "available" | "quarantined" | "deleted";

export interface ProjectFile {
  id: string;
  project_id: string;
  kind: FileKind;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  status: FileStatus;
  created_at: string;
  download_url: string;
}

export type ChecklistState =
  | "pending"
  | "in_progress"
  | "done"
  | "verified"
  | "skipped";

export interface ChecklistItemState {
  id: string;
  checklist_item_id: string;
  code: string;
  title: string;
  description: string | null;
  stage: ProjectStatus;
  is_required: boolean;
  due_at: string | null;
  status: ChecklistState;
  overdue: boolean;
  marked_at: string | null;
  verified_at: string | null;
  comment: string | null;
}

export interface ChecklistStage {
  stage: ProjectStatus;
  title: string;
  items: ChecklistItemState[];
  done_count: number;
  total_count: number;
  required_done: number;
  required_total: number;
}

export interface ChecklistProgress {
  done: number;
  required: number;
  percent: number;
}

export interface ProjectChecklist {
  project_id: string;
  stages: ChecklistStage[];
  progress: ChecklistProgress;
  overdue_count: number;
}

export type CommentVisibility = "student_visible" | "teachers_only";

export interface TeacherComment {
  id: string;
  project_id: string;
  body: string;
  visibility: CommentVisibility;
  stage: ProjectStatus | null;
  author_full_name: string | null;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
}

export interface TeacherProject {
  id: string;
  status: ProjectStatus;
  student_full_name: string;
  class_label: string;
  class_grade: number;
  academic_year_name: string | null;
  topic_title: string | null;
  research_question: string | null;
  topic_status: string | null;
  product_category_id: string | null;
  product_category_name: string | null;
  product_description: string | null;
  product_brief: Record<string, string> | null;
  product_defined_at: string | null;
  last_activity_at: string;
  files_count: number;
  comments_count: number;
}

/* --- Stage 5: dashboard, checkpoints, notifications ---------------------- */

export type TrafficLight = "green" | "yellow" | "red";

export interface StatusReason {
  code: string;
  label: string;
  severity: TrafficLight;
}

export interface NextCheckpoint {
  id: string;
  code: string;
  title: string;
  due_at: string;
  days_left: number;
  required_status: ProjectStatus;
  overdue: boolean;
}

export interface DashboardStudent {
  student_id: string;
  student_full_name: string;
  project_id: string | null;
  status: ProjectStatus | "no_project";
  color: TrafficLight;
  reasons: StatusReason[];
  last_activity_at: string | null;
  inactive_days: number | null;
  next_checkpoint: NextCheckpoint | null;
  checklist_done: number;
  checklist_total: number;
  checklist_overdue: number;
  has_final_file: boolean;
  files_count: number;
  last_comment_at: string | null;
  last_comment_excerpt: string | null;
  topic_title: string | null;
}

export interface DashboardSummary {
  total: number;
  green: number;
  yellow: number;
  red: number;
}

export interface ClassDashboard {
  class_id: string;
  class_label: string;
  class_grade: number;
  academic_year_name: string | null;
  generated_at: string;
  summary: DashboardSummary;
  students: DashboardStudent[];
}

export type NotificationType =
  | "topic_decision"
  | "topic_review"
  | "checkpoint_due"
  | "inactivity"
  | "teacher_digest"
  | "new_comment"
  | "checklist_due";

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  project_id: string | null;
  checkpoint_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
  is_read: boolean;
}

export interface NotificationList {
  items: NotificationItem[];
  unread_count: number;
  total: number;
}

/* --- Stage 6: admin ------------------------------------------------------ */

export interface School {
  id: string;
  name: string;
  region: string | null;
  city: string | null;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface AcademicYear {
  id: string;
  school_id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  is_current: boolean;
}

export interface AdminInterestArea extends InterestArea {
  is_active: boolean;
  sort_order: number;
}

export interface AdminProductCategory extends ProductCategory {
  is_active: boolean;
  sort_order: number;
}

export interface AdminStudent {
  user_id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  class_id: string;
  class_label: string;
  class_grade: number;
  academic_year_name: string | null;
}

export interface ImportedStudent {
  user_id: string;
  full_name: string;
  email: string;
  temp_password: string;
}

export interface ImportSkip {
  row: number;
  email: string | null;
  reason: string;
}

export interface StudentImportResult {
  created: ImportedStudent[];
  skipped: ImportSkip[];
  created_count: number;
  skipped_count: number;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  actor_id: string | null;
  actor_name: string | null;
  school_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  payload: Record<string, unknown> | null;
}

export interface AdminChecklistItem {
  id: string;
  school_id: string | null;
  academic_year_id: string;
  stage: ProjectStatus;
  code: string;
  title: string;
  description: string | null;
  sort_order: number;
  is_required: boolean;
  due_at: string | null;
  is_active: boolean;
}

export interface AdminCheckpoint {
  id: string;
  school_id: string | null;
  academic_year_id: string;
  code: string;
  title: string;
  description: string | null;
  due_at: string;
  required_status: ProjectStatus;
  audience: "student" | "teacher" | "both";
  is_active: boolean;
  sort_order: number;
}
