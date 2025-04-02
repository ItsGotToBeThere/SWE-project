from django import forms
from .models import Note, Profile, Collection, NoteReview, RequestNote

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'description', 'course_name', 'professor', 'semester']

class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['title', 'description', 'visibility']

class NoteReviewForm(forms.ModelForm):
    class Meta:
        model = NoteReview
        fields = ['rating','comment']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['user']


class PatronCollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ['title', 'description']  

class RequestNoteForm(forms.ModelForm):
    class Meta:
        model = RequestNote
        fields = ['return_date', 'additional_notes']
        widgets = {
            'return_date': forms.TextInput(attrs={'type': 'date'}),
        }