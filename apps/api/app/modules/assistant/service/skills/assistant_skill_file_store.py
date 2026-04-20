from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import shutil
import uuid

from app.shared.runtime.errors import NotFoundError

from .assistant_skill_dto import AssistantSkillCreateDTO, AssistantSkillDetailDTO, AssistantSkillUpdateDTO
from .assistant_skill_support import (
    SKILL_FILE_NAME,
    build_runtime_skill,
    build_skill_detail,
    build_skill_summary,
    build_project_skill_path,
    build_user_skill_path,
    create_project_skill_detail,
    create_user_skill_detail,
    detail_to_record,
    format_skill_markdown,
    parse_skill_markdown,
    update_skill_detail,
)


class AssistantSkillFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list_user_skills(self, user_id: uuid.UUID):
        return self._list_skills(self._user_skills_root(user_id))

    def list_project_skills(self, project_id: uuid.UUID):
        return self._list_skills(self._project_skills_root(project_id))

    def load_user_skill(self, user_id: uuid.UUID, skill_id: str) -> AssistantSkillDetailDTO:
        return build_skill_detail(self._find_user_skill(user_id, skill_id))

    def load_project_skill(self, project_id: uuid.UUID, skill_id: str) -> AssistantSkillDetailDTO:
        return build_skill_detail(self._find_project_skill(project_id, skill_id))

    def find_user_skill(self, user_id: uuid.UUID, skill_id: str):
        try:
            return self._find_user_skill(user_id, skill_id)
        except NotFoundError:
            return None

    def find_project_skill(self, project_id: uuid.UUID, skill_id: str):
        try:
            return self._find_project_skill(project_id, skill_id)
        except NotFoundError:
            return None

    def create_user_skill(
        self,
        user_id: uuid.UUID,
        payload: AssistantSkillCreateDTO,
        *,
        reserved_ids: set[str],
    ) -> AssistantSkillDetailDTO:
        existing_ids = self._list_existing_ids(self._user_skills_root(user_id))
        detail = create_user_skill_detail(
            payload,
            reserved_ids=reserved_ids,
            existing_ids=existing_ids,
        )
        self._write_skill(build_user_skill_path(self.root, user_id, detail.id), detail)
        return self.load_user_skill(user_id, detail.id)

    def create_project_skill(
        self,
        project_id: uuid.UUID,
        payload: AssistantSkillCreateDTO,
        *,
        reserved_ids: set[str],
    ) -> AssistantSkillDetailDTO:
        existing_ids = self._list_existing_ids(self._project_skills_root(project_id))
        detail = create_project_skill_detail(
            payload,
            reserved_ids=reserved_ids,
            existing_ids=existing_ids,
        )
        self._write_skill(build_project_skill_path(self.root, project_id, detail.id), detail)
        return self.load_project_skill(project_id, detail.id)

    def update_user_skill(
        self,
        user_id: uuid.UUID,
        skill_id: str,
        payload: AssistantSkillUpdateDTO,
    ) -> AssistantSkillDetailDTO:
        current = self.load_user_skill(user_id, skill_id)
        detail = update_skill_detail(skill_id, payload, updated_at=current.updated_at)
        self._write_skill(build_user_skill_path(self.root, user_id, detail.id), detail)
        return self.load_user_skill(user_id, skill_id)

    def update_project_skill(
        self,
        project_id: uuid.UUID,
        skill_id: str,
        payload: AssistantSkillUpdateDTO,
    ) -> AssistantSkillDetailDTO:
        current = self.load_project_skill(project_id, skill_id)
        detail = update_skill_detail(skill_id, payload, updated_at=current.updated_at)
        self._write_skill(build_project_skill_path(self.root, project_id, detail.id), detail)
        return self.load_project_skill(project_id, skill_id)

    def delete_user_skill(self, user_id: uuid.UUID, skill_id: str) -> None:
        self._delete_skill(build_user_skill_path(self.root, user_id, skill_id), skill_id)

    def delete_project_skill(self, project_id: uuid.UUID, skill_id: str) -> None:
        self._delete_skill(build_project_skill_path(self.root, project_id, skill_id), skill_id)

    def _list_skills(self, skills_root: Path):
        records = [parse_skill_markdown(path, path.read_text(encoding="utf-8")) for path in self._iter_skill_files(skills_root)]
        sorted_records = sorted(
            records,
            key=lambda item: item.updated_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return [build_skill_summary(record) for record in sorted_records]

    def _write_skill(self, path: Path, detail: AssistantSkillDetailDTO) -> None:
        build_runtime_skill(detail_to_record(detail, path=path, updated_at=detail.updated_at))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(format_skill_markdown(detail), encoding="utf-8")

    def _find_user_skill(self, user_id: uuid.UUID, skill_id: str):
        return self._find_skill(self._user_skills_root(user_id), skill_id)

    def _find_project_skill(self, project_id: uuid.UUID, skill_id: str):
        return self._find_skill(self._project_skills_root(project_id), skill_id)

    def _find_skill(self, skills_root: Path, skill_id: str):
        for path in self._iter_skill_files(skills_root):
            record = parse_skill_markdown(path, path.read_text(encoding="utf-8"))
            if record.id == skill_id:
                return record
        raise NotFoundError(f"Assistant skill not found: {skill_id}")

    def _delete_skill(self, path: Path, skill_id: str) -> None:
        if not path.exists():
            raise NotFoundError(f"Assistant skill not found: {skill_id}")
        skill_dir = path.parent
        path.unlink()
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

    def _list_existing_ids(self, skills_root: Path) -> set[str]:
        return {parse_skill_markdown(path, path.read_text(encoding="utf-8")).id for path in self._iter_skill_files(skills_root)}

    def _iter_skill_files(self, skills_root: Path):
        if not skills_root.exists():
            return []
        return sorted(skills_root.rglob(SKILL_FILE_NAME))

    def _project_skills_root(self, project_id: uuid.UUID) -> Path:
        return self.root / "projects" / str(project_id) / "skills"

    def _user_skills_root(self, user_id: uuid.UUID) -> Path:
        return self.root / "users" / str(user_id) / "skills"
