"""
Management command to create default superuser admin if none exists.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Creates default superuser for Django Admin if none exists."

    def handle(self, *args, **options):
        admin_phone = os.getenv('ADMIN_PHONE', '+998900000000')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        admin_name = os.getenv('ADMIN_NAME', 'Admin')

        if not User.objects.filter(is_superuser=True).exists():
            try:
                admin_user = User.objects.create_superuser(
                    phone_number=admin_phone,
                    password=admin_password,
                    first_name=admin_name
                )
                self.stdout.write(self.style.SUCCESS(f"Superuser admin yaratildi: {admin_phone} (Parol: {admin_password})"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Superuser yaratishda ogohlantirish: {e}"))
        else:
            self.stdout.write(self.style.SUCCESS("Superuser admin allaqachon mavjud."))
