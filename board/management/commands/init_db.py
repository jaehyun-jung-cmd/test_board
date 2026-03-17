from django.core.management.base import BaseCommand

from board.database import init_db


class Command(BaseCommand):
    help = 'SQLAlchemy 모델 기반으로 DB 테이블 생성'

    def handle(self, *args, **options):
        self.stdout.write('DB 테이블 생성 중...')
        init_db()
        self.stdout.write(self.style.SUCCESS('DB 테이블 생성 완료!'))
