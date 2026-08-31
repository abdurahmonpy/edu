from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.programs.models import Program, University
from apps.resources.models import Resource

class Command(BaseCommand):
    help = 'Seeds database'
    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding...')
        korea_uni, _ = University.objects.get_or_create(name='Global Korea Scholarship', country='Janubiy Koreya')
        Program.objects.get_or_create(name='GKS - Janubiy Koreya Hukumat Granti', country='Janubiy Koreya', type='grant', defaults={'university': korea_uni, 'scope': 'international', 'source_url': 'https://www.studyinkorea.go.kr/', 'last_verified_date': timezone.now().date(), 'requirements': {'TOPIK': 'Level 3+', 'IELTS': 'Optional'}})
        wiut_uni, _ = University.objects.get_or_create(name='WIUT', country='Uzbekistan')
        Program.objects.get_or_create(name='WIUT Davlat Granti', country='Uzbekistan', type='grant', defaults={'university': wiut_uni, 'scope': 'domestic', 'source_url': 'https://wiut.uz/admissions', 'last_verified_date': timezone.now().date(), 'requirements': {'DTM': 'Required'}})
        Resource.objects.get_or_create(title='DTM strategiyasi', category='dtm_prep', defaults={'content': 'DTM format...'})
        Resource.objects.get_or_create(title='Portfolio tayyorlash', category='portfolio_prep', defaults={'content': 'Portfolio nima...'})
        self.stdout.write(self.style.SUCCESS('Done'))
        france_uni, _ = University.objects.get_or_create(name='Campus France', country='France')
        Program.objects.get_or_create(name='Parcoursup / Campus France', country='France', type='application_system', defaults={'university': france_uni, 'scope': 'international', 'source_url': 'https://www.campusfrance.org', 'last_verified_date': timezone.now().date(), 'requirements': {'Language': 'DELF B2'}})
        mext_uni, _ = University.objects.get_or_create(name='MEXT', country='Japan')
        Program.objects.get_or_create(name='MEXT - Yaponiya Hukumat Granti', country='Japan', type='grant', defaults={'university': mext_uni, 'scope': 'international', 'source_url': 'https://www.studyinjapan.go.jp/', 'last_verified_date': timezone.now().date(), 'requirements': {'JLPT': 'N2+'}})
        Resource.objects.get_or_create(title='Yevropa universitetlari (Campus France)', category='europe_admissions', defaults={'content': 'Yevropa...' })
        Resource.objects.get_or_create(title='Osiyo universitetlari (KGSP, MEXT)', category='east_asia_admissions', defaults={'content': 'Osiyo...' })
