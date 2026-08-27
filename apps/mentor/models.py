"""
Models for AI mentor persistent chat and conversation history.
"""
from django.db import models

class MentorMessage(models.Model):
    """
    Stores conversational turns between student and AI Mentor.
    """
    ROLE_CHOICES = [
        ('student', "O'quvchi"),
        ('ai', 'AI Mentor'),
    ]

    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='mentor_messages',
        verbose_name="O'quvchi"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name="Rol"
    )
    content = models.TextField(
        verbose_name="Xabar matni"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yuborilgan vaqt"
    )

    class Meta:
        verbose_name = "Mentor xabari"
        verbose_name_plural = "Mentor xabarlari"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.get_role_display()}] {self.student.user.first_name}: {self.content[:40]}"
