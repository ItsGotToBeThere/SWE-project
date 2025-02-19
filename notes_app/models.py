from django.db import models
from django.contrib.auth.models import User

class Note(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='uploads/')  # File storage
    course_name = models.CharField(max_length=100)
    professor = models.CharField(max_length=100, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    privacy = models.CharField(
        max_length=20,
        choices=[('public', 'Public'), ('private', 'Private'), ('friends_only', 'Friends Only')],
        default='public'
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # Track who uploaded the note
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
