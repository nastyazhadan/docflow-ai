from __future__ import annotations

from core_api.app.models.sql.knowledge_space import KnowledgeSpace  # noqa: F401
from core_api.app.models.sql.source_config import SourceConfig, SourceType  # noqa: F401
# Импортируем модели, чтобы Alembic "видел" их в metadata
from core_api.app.models.sql.tenant import Tenant  # noqa: F401
from core_api.app.models.sql.user import User  # noqa: F401
