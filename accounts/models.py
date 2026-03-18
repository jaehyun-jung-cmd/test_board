from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from board.database import Base


class User(Base):
    """회원 모델"""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)                          # 회원번호
    email = Column(String(255), unique=True, nullable=False, index=True)        # 로그인 ID (이메일)
    password = Column(String(256), nullable=False)                              # Argon2 해시 비밀번호
    nickname = Column(String(50), unique=True, nullable=False)                  # 별명
    name = Column(String(100), nullable=False)                                  # 이름
    phone = Column(String(20), nullable=True)                                   # 전화번호 (선택)
    is_active = Column(Boolean, default=True)                                   # 계정 활성화 여부
    last_login_at = Column(DateTime, nullable=True)                             # 마지막 로그인 일시
    created_at = Column(DateTime, default=datetime.utcnow)                      # 가입일
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 수정일

    # 비밀번호 재설정 토큰과의 관계
    reset_tokens = relationship('PasswordResetToken', back_populates='user', cascade='all, delete-orphan')
    # 작성 게시글과의 관계
    posts = relationship('Post', back_populates='user')
    # 작성 댓글과의 관계
    comments = relationship('Comment', back_populates='user')


class PasswordResetToken(Base):
    """비밀번호 재설정 토큰 모델 - 원본 토큰은 이메일로 발송, DB에는 SHA-256 해시만 저장"""

    __tablename__ = 'password_reset_tokens'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)           # 토큰 발급 회원
    token_hash = Column(String(64), unique=True, nullable=False, index=True)    # SHA-256 해시값
    created_at = Column(DateTime, default=datetime.utcnow)                      # 발급 일시
    used = Column(Boolean, default=False)                                       # 사용 여부

    user = relationship('User', back_populates='reset_tokens')
