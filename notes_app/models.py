from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
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


PRONOUN_CHOICES = (('he/him',"He/Him"), ('she/her',"She/Her"), ('they/them',"They/Them"), ('other',"Other"))

class Profile(models.Model):
    """
    User class + other information (Bio, Profile pic, etc.)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    banner = models.ImageField(storage=S3Boto3Storage(), null = True, blank = True, upload_to='banners/', default = None)
    profile_picture = models.ImageField(storage=S3Boto3Storage(), null = True, blank = True, upload_to='profile-pictures/', default=None)
    preferred_named = models.CharField(max_length = 40,blank=True)
    preferred_pronouns = models.CharField(max_length = 17,choices = PRONOUN_CHOICES, blank=True)
    bio = models.TextField(blank=True)


    def get_banner_url(self):
        if self.banner:
            return self.banner.url
        else:
            return static('notes_app/images/default_banner.png')

    def get_profile_pic_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        else:
            return static('notes_app/images/default_profile.png')

    def get_role(self):
        return str(self.user.groups.all()[0])[:-1]

    def get_preferred_name(self):
        if self.preferred_named:
            return self.preferred_named
        else:
            return self.user.username