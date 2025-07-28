from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String, nullable=False, index=True, unique=True)

class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    source_id = Column(Integer, ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False, index=True)
    weight = Column(Integer, nullable=False, default=1)
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", name="uq_source_target"),
    )

    def __repr__(self):
        return f"<Edge(source_id={self.source_id}, target_id={self.target_id})>"