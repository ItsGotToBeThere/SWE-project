import django_filters
from notes_app.models import Collection, Note


class NotesFilter(django_filters.FilterSet):
    class Meta:
        model = Note
        fields = {
            'title': ['icontains'], #icontains does a case-insensitive contains check
            'course_name': ['icontains'],
            'professor': ['icontains']
        }

    #used to change the display text
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['title__icontains'].label = 'Note Title'
        self.filters['course_name__icontains'].label = 'Course Name'
        self.filters['professor__icontains'].label = 'Professor Name'

class CollectionsFilter(django_filters.FilterSet):
    class Meta:
        model = Collection
        fields = {
            'title': ['icontains'], #icontains does a case-insensitive contains check
        }
    
    VISIBILITY_CHOICES = (
        ('private', 'Private'),
        ('public', 'Public'),
    )
    
    visibility = django_filters.ChoiceFilter(choices=VISIBILITY_CHOICES)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['title__icontains'].label = 'Collection Title'
