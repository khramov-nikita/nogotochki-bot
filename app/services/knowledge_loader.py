"""Загрузка файла базы знаний."""

from __future__ import annotations

from pathlib import Path

# Корень проекта: app/services/ -> parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_PATH = (
    PROJECT_ROOT / "База знаний для бота бьюти-студии «Ноготочки».md"
)


class KnowledgeLoadError(Exception):
    """Не удалось прочитать базу знаний."""


def load_knowledge_base(path: Path | None = None) -> str:
    knowledge_path = path or DEFAULT_KNOWLEDGE_PATH
    try:
        return knowledge_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise KnowledgeLoadError(
            f"Не удалось прочитать базу знаний: {knowledge_path}"
        ) from exc
