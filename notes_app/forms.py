from django import forms
from .models import Note, Profile, Collection

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'description', 'course_name', 'professor', 'semester']

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['title', 'description', 'visibility']



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['user']
        error_css_class = 'error'
