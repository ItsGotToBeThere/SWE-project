from django.db import models
from django.contrib.auth.models import User
from storages.backends.s3boto3 import S3Boto3Storage
class Collection(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Note(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course_name = models.CharField(max_length=100)
    professor = models.CharField(max_length=100, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # User refers to the auth_user table
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    s3_url = models.URLField(blank=True, null=True)  
    is_requested = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class NoteFile(models.Model): #allows multiple file instances to be associated with one note
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    file = models.FileField(storage=S3Boto3Storage(), upload_to='notes/')

class PatronRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("denied", "Denied"),
    ]
    patron = models.ForeignKey(User, on_delete=models.CASCADE) 
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patron.username} - {self.note.title} - {self.status}"  
