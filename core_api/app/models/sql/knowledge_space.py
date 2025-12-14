from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_api.db.base import Base


class KnowledgeSpace(Base):
    __tablename__ = "knowledge_spaces"
    __table_args__ = (
        UniqueConstraint("tenant_id", "space_key", name="uq_spaces_tenant_space_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
                                                 nullable=False)

    # Это то, что у вас сейчас везде называется space_id (demo-space)
    space_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="spaces")
    source_configs = relationship("SourceConfig", back_populates="space", cascade="all, delete-orphan")
