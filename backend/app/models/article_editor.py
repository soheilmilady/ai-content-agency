from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.session import Base

article_editors = Table(
    "article_editors",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)
