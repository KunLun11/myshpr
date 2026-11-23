"""Admin endpoints: schools, years, classes, reference data, students, audit."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ensure_class_access, ensure_school_access, get_session, require_roles
from app.core.errors import NotFoundError, ValidationError
from app.models import SchoolClass, User
from app.models.enums import UserRole
from app.repositories import classes as classes_repo
from app.schemas.admin_org import (
    AcademicYearCreateRequest,
    AcademicYearOut,
    AcademicYearUpdateRequest,
    SchoolCreateRequest,
    SchoolOut,
    SchoolUpdateRequest,
)
from app.schemas.audit import AuditEntryOut
from app.schemas.checklist import (
    AdminChecklistItemCreateRequest,
    AdminChecklistItemOut,
    AdminChecklistItemUpdateRequest,
)
from app.schemas.checkpoint import (
    CheckpointCreateRequest,
    CheckpointOut,
    CheckpointUpdateRequest,
)
from app.schemas.classes import (
    AdminStudentOut,
    ClassCreateRequest,
    ClassOut,
    InviteCreateRequest,
    InviteOut,
    StudentImportResult,
    StudentOut,
)
from app.schemas.reference import (
    AdminInterestAreaOut,
    AdminProductCategoryOut,
    InterestAreaCreateRequest,
    InterestAreaUpdateRequest,
    ProductCategoryCreateRequest,
    ProductCategoryUpdateRequest,
)
from app.services import admin_org, reference_admin, students_admin
from app.services import audit as audit_service
from app.services import checklists as checklists_service
from app.services import checkpoints as checkpoints_service
from app.services import classes as classes_service
from app.services.classes import serialize_class

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.SCHOOL_ADMIN))]
SuperAdminUser = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]
ClassStaffUser = Annotated[User, Depends(require_roles(UserRole.SCHOOL_ADMIN, UserRole.TEACHER))]

MAX_AUDIT_LIMIT = 500


async def _load_class(session: AsyncSession, class_id: uuid.UUID) -> SchoolClass:
    school_class = await classes_repo.get_by_id(session, class_id)
    if school_class is None:
        raise NotFoundError("Класс не найден", "CLASS_NOT_FOUND")
    return school_class


@router.get("/classes", response_model=list[ClassOut], summary="Классы школы")
async def list_classes(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    school_id: uuid.UUID | None = None,
) -> list[ClassOut]:
    target_school: uuid.UUID | None = school_id
    if user.role is not UserRole.SUPER_ADMIN:
        target_school = user.school_id
        ensure_school_access(user, target_school)
    rows = await classes_repo.list_school_classes(session, target_school)
    return [serialize_class(row) for row in rows]


@router.post(
    "/classes",
    response_model=ClassOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать класс",
)
async def create_class(
    payload: ClassCreateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    school_id: uuid.UUID | None = None,
) -> ClassOut:
    target_school = user.school_id
    if user.role is UserRole.SUPER_ADMIN:
        target_school = school_id
    if target_school is None:
        raise ValidationError("Не указана школа", "SCHOOL_REQUIRED")
    ensure_school_access(user, target_school)

    created = await classes_service.create_class(
        session,
        school_id=target_school,
        grade=payload.grade,
        label=payload.label,
        academic_year_id=payload.academic_year_id,
        curator_id=payload.curator_id,
    )
    await audit_service.record(
        session,
        user,
        "class.created",
        entity_type="class",
        entity_id=created.id,
        payload={"grade": created.grade, "label": created.label},
        school_id=target_school,
    )
    return created


@router.get("/classes/{class_id}", response_model=ClassOut, summary="Карточка класса")
async def get_class(
    class_id: uuid.UUID,
    user: ClassStaffUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ClassOut:
    school_class = await _load_class(session, class_id)
    await ensure_class_access(session, user, school_class)
    return await classes_service.get_class(session, class_id)


@router.get(
    "/classes/{class_id}/students",
    response_model=list[StudentOut],
    summary="Ученики класса",
)
async def list_students(
    class_id: uuid.UUID,
    user: ClassStaffUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[StudentOut]:
    school_class = await _load_class(session, class_id)
    await ensure_class_access(session, user, school_class)

    rows = await classes_repo.list_class_students(session, class_id)
    return [
        StudentOut(user_id=user_id, full_name=full_name, email=email, class_id=student_class_id)
        for user_id, full_name, email, student_class_id in rows
    ]


@router.post(
    "/classes/{class_id}/invites",
    response_model=InviteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать код приглашения в класс",
)
async def create_invite(
    class_id: uuid.UUID,
    payload: InviteCreateRequest,
    user: ClassStaffUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InviteOut:
    school_class = await _load_class(session, class_id)
    await ensure_class_access(session, user, school_class)
    invite = await classes_service.create_invite(
        session, school_class=school_class, created_by=user.id, payload=payload
    )
    await audit_service.record(
        session,
        user,
        "class.invite_created",
        entity_type="class_invite",
        entity_id=invite.id,
        payload={"class_id": class_id, "max_uses": invite.max_uses},
        school_id=school_class.school_id,
    )
    return invite


@router.post(
    "/invites/{invite_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отозвать код приглашения",
)
async def revoke_invite(
    invite_id: uuid.UUID,
    user: ClassStaffUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    invite = await classes_repo.get_invite_by_id(session, invite_id)
    if invite is None:
        raise NotFoundError("Код приглашения не найден", "INVITE_NOT_FOUND")
    school_class = await _load_class(session, invite.class_id)
    await ensure_class_access(session, user, school_class)
    await classes_service.revoke_invite(session, invite)
    await audit_service.record(
        session,
        user,
        "class.invite_revoked",
        entity_type="class_invite",
        entity_id=invite.id,
        payload={"class_id": school_class.id},
        school_id=school_class.school_id,
    )


# --- Stage 4: checklist template -------------------------------------------


@router.get(
    "/checklist-items",
    response_model=list[AdminChecklistItemOut],
    summary="Шаблон чек-листа",
)
async def list_checklist_items(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    academic_year_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
) -> list[AdminChecklistItemOut]:
    if school_id is not None and user.role is not UserRole.SUPER_ADMIN:
        ensure_school_access(user, school_id)
    return await checklists_service.list_admin_items(
        session, user, academic_year_id=academic_year_id, school_id=school_id
    )


@router.post(
    "/checklist-items",
    response_model=AdminChecklistItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить пункт чек-листа",
)
async def create_checklist_item(
    payload: AdminChecklistItemCreateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminChecklistItemOut:
    created = await checklists_service.create_admin_item(session, user, payload)
    await audit_service.record(
        session,
        user,
        "checklist_item.created",
        entity_type="checklist_item",
        entity_id=created.id,
        payload={"code": created.code, "stage": created.stage.value},
        school_id=created.school_id,
    )
    return created


@router.patch(
    "/checklist-items/{item_id}",
    response_model=AdminChecklistItemOut,
    summary="Изменить пункт чек-листа",
)
async def update_checklist_item(
    item_id: uuid.UUID,
    payload: AdminChecklistItemUpdateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminChecklistItemOut:
    updated = await checklists_service.update_admin_item(session, user, item_id, payload)
    await audit_service.record(
        session,
        user,
        "checklist_item.updated",
        entity_type="checklist_item",
        entity_id=updated.id,
        payload={"code": updated.code, "fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=updated.school_id,
    )
    return updated


@router.delete(
    "/checklist-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отключить пункт чек-листа",
)
async def delete_checklist_item(
    item_id: uuid.UUID,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    await checklists_service.deactivate_admin_item(session, user, item_id)
    await audit_service.record(
        session,
        user,
        "checklist_item.deactivated",
        entity_type="checklist_item",
        entity_id=item_id,
    )


# --- Stage 5: control points -----------------------------------------------


@router.get(
    "/checkpoints",
    response_model=list[CheckpointOut],
    summary="Контрольные точки",
)
async def list_checkpoints(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    academic_year_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
) -> list[CheckpointOut]:
    if school_id is not None and user.role is not UserRole.SUPER_ADMIN:
        ensure_school_access(user, school_id)
    return await checkpoints_service.list_admin(
        session,
        user,
        academic_year_id=academic_year_id,
        school_id=school_id,
    )


@router.post(
    "/checkpoints",
    response_model=CheckpointOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать контрольную точку",
)
async def create_checkpoint(
    payload: CheckpointCreateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CheckpointOut:
    created = await checkpoints_service.create(session, user, payload)
    await audit_service.record(
        session,
        user,
        "checkpoint.created",
        entity_type="checkpoint",
        entity_id=created.id,
        payload={"code": created.code, "due_at": created.due_at.isoformat()},
        school_id=created.school_id,
    )
    return created


@router.patch(
    "/checkpoints/{checkpoint_id}",
    response_model=CheckpointOut,
    summary="Изменить контрольную точку",
)
async def update_checkpoint(
    checkpoint_id: uuid.UUID,
    payload: CheckpointUpdateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CheckpointOut:
    updated = await checkpoints_service.update(session, user, checkpoint_id, payload)
    await audit_service.record(
        session,
        user,
        "checkpoint.updated",
        entity_type="checkpoint",
        entity_id=updated.id,
        payload={"code": updated.code, "fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=updated.school_id,
    )
    return updated


# --- Stage 6: schools and academic years -----------------------------------


@router.get("/schools", response_model=list[SchoolOut], summary="Школы")
async def list_schools(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[SchoolOut]:
    return await admin_org.list_schools(session, user)


@router.post(
    "/schools",
    response_model=SchoolOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать школу",
)
async def create_school(
    payload: SchoolCreateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SchoolOut:
    created = await admin_org.create_school(session, user, payload)
    await audit_service.record(
        session,
        user,
        "school.created",
        entity_type="school",
        entity_id=created.id,
        payload={"name": created.name},
        school_id=created.id,
    )
    return created


@router.patch("/schools/{school_id}", response_model=SchoolOut, summary="Изменить школу")
async def update_school(
    school_id: uuid.UUID,
    payload: SchoolUpdateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SchoolOut:
    updated = await admin_org.update_school(session, user, school_id, payload)
    await audit_service.record(
        session,
        user,
        "school.updated",
        entity_type="school",
        entity_id=updated.id,
        payload={"fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=updated.id,
    )
    return updated


@router.get(
    "/academic-years",
    response_model=list[AcademicYearOut],
    summary="Учебные годы",
)
async def list_academic_years(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    school_id: uuid.UUID | None = None,
) -> list[AcademicYearOut]:
    return await admin_org.list_years(session, user, school_id=school_id)


@router.post(
    "/academic-years",
    response_model=AcademicYearOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать учебный год",
)
async def create_academic_year(
    payload: AcademicYearCreateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicYearOut:
    created = await admin_org.create_year(session, user, payload)
    await audit_service.record(
        session,
        user,
        "academic_year.created",
        entity_type="academic_year",
        entity_id=created.id,
        payload={"name": created.name, "is_current": created.is_current},
        school_id=created.school_id,
    )
    return created


@router.patch(
    "/academic-years/{year_id}",
    response_model=AcademicYearOut,
    summary="Изменить учебный год",
)
async def update_academic_year(
    year_id: uuid.UUID,
    payload: AcademicYearUpdateRequest,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicYearOut:
    updated = await admin_org.update_year(session, user, year_id, payload)
    await audit_service.record(
        session,
        user,
        "academic_year.updated",
        entity_type="academic_year",
        entity_id=updated.id,
        payload={"fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=updated.school_id,
    )
    return updated


# --- Stage 6: reference data ------------------------------------------------


@router.get(
    "/interest-areas",
    response_model=list[AdminInterestAreaOut],
    summary="Сферы интересов (админка)",
)
async def list_admin_interest_areas(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AdminInterestAreaOut]:
    return await reference_admin.list_interest_areas(session)


@router.post(
    "/interest-areas",
    response_model=AdminInterestAreaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить сферу интересов",
)
async def create_interest_area(
    payload: InterestAreaCreateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminInterestAreaOut:
    created = await reference_admin.create_interest_area(session, user, payload)
    await audit_service.record(
        session,
        user,
        "interest_area.created",
        entity_type="interest_area",
        entity_id=created.id,
        payload={"slug": created.slug},
        school_id=None,
    )
    return created


@router.patch(
    "/interest-areas/{area_id}",
    response_model=AdminInterestAreaOut,
    summary="Изменить сферу интересов",
)
async def update_interest_area(
    area_id: uuid.UUID,
    payload: InterestAreaUpdateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminInterestAreaOut:
    updated = await reference_admin.update_interest_area(session, user, area_id, payload)
    await audit_service.record(
        session,
        user,
        "interest_area.updated",
        entity_type="interest_area",
        entity_id=updated.id,
        payload={"slug": updated.slug, "fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=None,
    )
    return updated


@router.get(
    "/product-categories",
    response_model=list[AdminProductCategoryOut],
    summary="Категории продукта (админка)",
)
async def list_admin_product_categories(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[AdminProductCategoryOut]:
    return await reference_admin.list_product_categories(session)


@router.post(
    "/product-categories",
    response_model=AdminProductCategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить категорию продукта",
)
async def create_product_category(
    payload: ProductCategoryCreateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminProductCategoryOut:
    created = await reference_admin.create_product_category(session, user, payload)
    await audit_service.record(
        session,
        user,
        "product_category.created",
        entity_type="product_category",
        entity_id=created.id,
        payload={"slug": created.slug},
        school_id=None,
    )
    return created


@router.patch(
    "/product-categories/{category_id}",
    response_model=AdminProductCategoryOut,
    summary="Изменить категорию продукта",
)
async def update_product_category(
    category_id: uuid.UUID,
    payload: ProductCategoryUpdateRequest,
    user: SuperAdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminProductCategoryOut:
    updated = await reference_admin.update_product_category(session, user, category_id, payload)
    await audit_service.record(
        session,
        user,
        "product_category.updated",
        entity_type="product_category",
        entity_id=updated.id,
        payload={"slug": updated.slug, "fields": sorted(payload.model_dump(exclude_unset=True))},
        school_id=None,
    )
    return updated


# --- Stage 6: students and CSV import ---------------------------------------


@router.get("/students", response_model=list[AdminStudentOut], summary="Ученики школы")
async def list_admin_students(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    class_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[AdminStudentOut]:
    if school_id is not None and user.role is not UserRole.SUPER_ADMIN:
        ensure_school_access(user, school_id)
    return await students_admin.list_students(
        session,
        user,
        class_id=class_id,
        school_id=school_id,
        query=q,
        limit=min(max(limit, 1), 1000),
        offset=max(offset, 0),
    )


@router.post(
    "/students/import",
    response_model=StudentImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Импортировать учеников из CSV",
)
async def import_admin_students(
    class_id: uuid.UUID,
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    file: Annotated[UploadFile, File(description="CSV с колонками full_name, email")],
) -> StudentImportResult:
    content = await file.read(students_admin.MAX_IMPORT_BYTES + 1)
    result = await students_admin.import_students(session, user, class_id=class_id, content=content)
    school_class = await classes_repo.get_by_id(session, class_id)
    await audit_service.record(
        session,
        user,
        "students.imported",
        entity_type="class",
        entity_id=class_id,
        payload={"created": result.created_count, "skipped": result.skipped_count},
        school_id=school_class.school_id if school_class else None,
    )
    return result


# --- Stage 6: audit log -----------------------------------------------------


@router.get(
    "/audit-log",
    response_model=list[AuditEntryOut],
    summary="Журнал действий администраторов",
)
async def list_audit_log(
    user: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    action: str | None = None,
    school_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEntryOut]:
    if school_id is not None and user.role is not UserRole.SUPER_ADMIN:
        ensure_school_access(user, school_id)
    return await audit_service.list_entries(
        session,
        user,
        school_id=school_id,
        action=action,
        limit=min(max(limit, 1), MAX_AUDIT_LIMIT),
        offset=max(offset, 0),
    )
