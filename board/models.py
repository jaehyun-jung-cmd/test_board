from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Post(Base):
    """게시글 모델"""

    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)                              # 게시글 고유 ID
    title = Column(String(200), nullable=False)                                     # 제목 (최대 200자)
    content = Column(Text, nullable=False)                                          # 본문 (Summernote HTML)
    author = Column(String(50), nullable=False)                                     # 작성자 닉네임 (비정규화)
    view_count = Column(Integer, default=0)                                         # 조회수
    created_at = Column(DateTime, default=datetime.utcnow)                          # 작성일시
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정일시
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)               # 작성자 FK

    # 댓글과 1:N 관계 - 게시글 삭제 시 댓글도 함께 삭제
    comments = relationship('Comment', back_populates='post', cascade='all, delete-orphan')
    # 작성자와의 관계
    user = relationship('User', back_populates='posts')


class Comment(Base):
    """댓글 모델"""

    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, index=True)                              # 댓글 고유 ID
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)  # 게시글 FK
    content = Column(Text, nullable=False)                                          # 댓글 내용
    author = Column(String(50), nullable=False)                                     # 작성자 닉네임 (비정규화)
    created_at = Column(DateTime, default=datetime.utcnow)                          # 작성일시
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정일시
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)               # 작성자 FK

    # 게시글과의 관계 참조
    post = relationship('Post', back_populates='comments')
    # 작성자와의 관계
    user = relationship('User', back_populates='comments')
