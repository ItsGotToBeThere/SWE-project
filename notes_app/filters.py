import django_filters
from notes_app.models import Collection, Note


class NotesFilter(django_filters.FilterSet):
    class Meta:
        model = Note
        fields = {
            'title': ['icontains'], #icontains does a case-insensitive contains check
            'course_name': ['icontains'],
        }

    #used to change the display text
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['title__icontains'].label = 'Note Title'
        self.filters['course_name__icontains'].label = 'Course Name'

class CollectionsFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains', label='Collection Title')
    
    VISIBILITY_CHOICES = (
        ('private', 'Private'),
        ('public', 'Public'),
    )
    
    visibility = django_filters.ChoiceFilter(choices=VISIBILITY_CHOICES)
