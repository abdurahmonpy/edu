"""
Management command to decay the Ready Score for students who missed tasks yesterday.
Usage:
    python manage.py decay_scores
    python manage.py decay_scores --date=2026-08-25 --points=2
"""
from datetime import datetime, date
from django.core.management.base import BaseCommand
from apps.services.score_service import decay_student_scores


class Command(BaseCommand):
    help = "Miss qilingan kunlar uchun o'quvchilarning Ready Score ko'rsatkichini pasaytiradi (Score Decay)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help="Tekshirish sanasi (YYYY-MM-DD formatida). Standart: kechagi kun."
        )
        parser.add_argument(
            '--points',
            type=int,
            default=2,
            help="Pasaytiriladigan ball miqdori (standart: 2)."
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        points = options.get('points', 2)

        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Yaroqsiz sana formati: {date_str}. YYYY-MM-DD formatida kiriting."))
                return

        self.stdout.write(self.style.NOTICE(f"Score decay boshlanmoqda... (Sana: {target_date or 'kecha'})"))

        result = decay_student_scores(target_date=target_date, decay_points=points)

        self.stdout.write(
            self.style.SUCCESS(
                f"Muvaffaqiyatli yakunlandi: {result['students_processed']} ta o'quvchi tekshirildi, "
                f"{result['students_decayed']} ta o'quvchining ballari pasaytirildi (-{points} ball)."
            )
        )
