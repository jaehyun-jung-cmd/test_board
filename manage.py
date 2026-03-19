#!/usr/bin/env python
"""Django 커맨드라인 관리 유틸리티"""
import os
import sys


def main():
    """관리 명령 실행"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django를 불러올 수 없습니다. Django가 설치되어 있고 "
            "PYTHONPATH 환경변수에 포함되어 있는지 확인하세요. "
            "가상 환경을 활성화하는 것을 잊으셨나요?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
