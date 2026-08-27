from django.contrib import admin
from .models import MockExam, MockExamSection

class MockExamSectionInline(admin.StackedInline):
    model = MockExamSection
    extra = 0
    fields = ('section_type', 'order', 'time_limit_seconds', 'section_score', 'status', 'ai_feedback')
    readonly_fields = ('started_at', 'ended_at')

@admin.register(MockExam)
class MockExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'exam_type', 'overall_band_score', 'status', 'started_at', 'completed_at')
    list_filter = ('exam_type', 'status', 'started_at')
    search_fields = ('student__user__first_name', 'student__user__phone_number')
    inlines = [MockExamSectionInline]

@admin.register(MockExamSection)
class MockExamSectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'mock_exam', 'section_type', 'order', 'section_score', 'status')
    list_filter = ('section_type', 'status')
    search_fields = ('mock_exam__student__user__phone_number', 'ai_feedback')
