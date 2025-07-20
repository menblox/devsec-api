from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String, index=True)
    age: Mapped[int] = Column(Integer)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    title: Mapped[str] = Column(String, index=True)
    body: Mapped[str] = Column(String)
    author_id: Mapped[int] = Column(Integer, ForeignKey("users.id"))

    author: Mapped["User"] = relationship("User")
