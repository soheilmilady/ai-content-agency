from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    content_html: Mapped[str] = mapped_column(Text)
    meta_description: Mapped[str] = mapped_column(String(160))
    focus_keyword: Mapped[str] = mapped_column(String)
    seo_score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="draft")
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    last_modified_by_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    wp_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    author = relationship("User", foreign_keys=[author_id], back_populates="articles")
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_id])
    assigned_editors = relationship("User", secondary="article_editors")
