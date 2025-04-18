from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from django.utils import timezone
from storages.backends.s3boto3 import S3Boto3Storage
from django.db.models import Avg
import urllib
from django.core.files.base import ContentFile

class Collection(models.Model):
    title = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    VISIBILITY_CHOICES = [
        ("public", "Public"), #public = database value, Public = human-readable value
        ("private", "Private"),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="public") 
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # User refers to the auth_user table
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Note(models.Model):
    title = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    course_name = models.CharField(max_length=100)
    professor = models.CharField(max_length=100, blank=True)
    semester = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)  # User refers to the auth_user table
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    VISIBILITY_CHOICES = [
        ("public", "Public"), #public = database value, Public = human-readable value
        ("private", "Private"),
    ]
    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default="public") #private = in private collection

    def get_reviews(self):
        return NoteReview.objects.filter(note=self)
    
    def is_borrowed(self):
        if RequestNote.objects.filter(note=self, return_date__gt=timezone.now(), borrowed=True, fulfilled_at__lt=timezone.now()):
            return True
        else:
            return False
    
    def get_display_image(self):
        files = NoteFile.objects.filter(note_id=self.id) #fetch an array of notefile objects
        
        #get default display icon and use it to make a notefile object
        response = urllib.request.urlopen('https://notes-sharing-app.s3.us-east-1.amazonaws.com/notes/default_image.png')
        file_obj = ContentFile(response.read(), name='notes/default_image.png')
        display_image = NoteFile(note=self,file=file_obj)
        
        #if any files associated with the note are images, use that instead of the defualt icon
        for file in files:
            if '.jpg' in str(file.file) or '.jpeg' in str(file.file) or '.png' in str(file.file):
                display_image = file
                break
        return display_image

    def get_average_rating(self):
        return NoteReview.objects.filter(note=self).aggregate(Avg("rating"))["rating__avg"] or None


    def __str__(self):
        return self.title

class RequestNote(models.Model):
    requester = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    return_date = models.DateTimeField(validators=[MinValueValidator(timezone.now)])
    additional_notes = models.TextField(blank=True)
    borrowed = models.BooleanField(default=False)
    fulfilled_at = models.DateTimeField(null=True, blank=True) #stored as None (null) when not set
    is_viewed = models.BooleanField(default = False)

class NoteFile(models.Model): #allows multiple file instances to be associated with one note
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    file = models.FileField(storage=S3Boto3Storage(), upload_to='notes/')

class CollectionItem(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

class PrivateCollectionPatron(models.Model):
    patron = models.ForeignKey(User, on_delete=models.CASCADE) 
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

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
    fulfilled_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f"{self.patron.username} - {self.note.title} - {self.status}"  

class NoteReview(models.Model):
    patron = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    rating = models.FloatField(null=False,default=5,validators=[MinValueValidator(0), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

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
    date_joined = models.DateTimeField(blank=True, auto_now_add=True)

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
        if self.user.groups.all().exists():
            return str(self.user.groups.all()[0])[:-1]
        else:
            return "Patron"

    def get_preferred_name(self):
        if self.preferred_named:
            return self.preferred_named
        else:
            return self.user.username

class CollectionAccessRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("denied", "Denied"),
    ]
    patron = models.ForeignKey(User, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patron.username} → {self.collection.title} ({self.status})"
