import django_filters
from notes_app.models import Collection, Note, NoteFile, CollectionItem, PrivateCollectionPatron


class NotesFilter(django_filters.FilterSet):
    class Meta:
        model = Note
        fields = {
            'title': ['icontains'], #icontains does a case-insensitive contains check
            'course_name': ['icontains'],
            'professor': ['icontains']
        }