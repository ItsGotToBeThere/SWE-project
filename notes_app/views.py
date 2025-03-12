from django.forms import ValidationError
from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views import generic

from .decorators import librarian_required, patron_required
from django.views import View
from django.utils.decorators import method_decorator
from django.core.files.storage import FileSystemStorage
from .models import Note, Collection, PatronRequest, Profile, NoteFile
from django.conf import settings
from .forms import NoteForm, ProfileForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import boto3
import urllib.request
from django.core.files.base import ContentFile

@login_required
def view_requests(request):
    """View to list patron requests for approval."""
    requests = PatronRequest.objects.filter(status="pending") 

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        patron_request = get_object_or_404(PatronRequest, id=request_id)

        if action == "approve":
            patron_request.status = "approved"
            patron_request.note.is_requested = False  
        elif action == "deny":
            patron_request.status = "denied"

        patron_request.save()
        return redirect("notes_app:view_requests") 

    return render(request, "notes_app/view_requests.html", {"requests": requests})

@login_required
def request_notes(request):
    """View to display private notes available for request."""
    notes = Note.objects.filter(is_requested=False, visibility="private") # only private notes
    title_query = request.GET.get('title', '')
    subject_query = request.GET.get('subject', '')
    semester_query = request.GET.get('semester', '')
    date_query = request.GET.get('date', '')
    collection_query = request.GET.get('collection', '')

    if title_query:
        notes = notes.filter(title__icontains=title_query)
    if subject_query:
        notes = notes.filter(subject__icontains=subject_query)
    if semester_query:
        notes = notes.filter(semester__icontains=semester_query)
    if date_query:
        notes = notes.filter(date=date_query)
    if collection_query:
        notes = notes.filter(collections__id=collection_query)

    if request.method == "POST":
        note_id = request.POST.get("note_id")
        note = get_object_or_404(Note, id=note_id)
        note.is_requested = True 
        note.save()
        return redirect("notes_app:request_notes")  

    return render(request, "notes_app/request_notes.html", {
        "notes": notes,
        "collections": collections
    })


def borrowed_notes(request):
    user = request.user
    notes = Note.objects.filter(borrowed_by=user) 
    collections = Collection.objects.all()
    title = request.GET.get("title")
    subject = request.GET.get("subject")
    semester = request.GET.get("semester")
    date = request.GET.get("date")
    visibility = request.GET.get("visibility")
    collection_id = request.GET.get("collection")

    if title:
        notes = notes.filter(title__icontains=title)
    if subject:
        notes = notes.filter(subject__icontains=subject)
    if semester:
        notes = notes.filter(semester__icontains=semester)
    if date:
        notes = notes.filter(date=date)
    if visibility:
        notes = notes.filter(visibility=visibility)
    if collection_id:
        notes = notes.filter(collections__id=collection_id)

    return render(request, "notes_app/borrowed_notes.html", {"notes": notes, "collections": collections})

def available_notes(request):
    notes = Note.objects.filter(visibility="public") 
    collections = Collection.objects.all()
    title = request.GET.get("title")
    subject = request.GET.get("subject")
    semester = request.GET.get("semester")
    date = request.GET.get("date")
    visibility = request.GET.get("visibility")
    collection_id = request.GET.get("collection")

    if title:
        notes = notes.filter(title__icontains=title)
    if subject:
        notes = notes.filter(subject__icontains=subject)
    if semester:
        notes = notes.filter(semester__icontains=semester)
    if date:
        notes = notes.filter(date=date)
    if visibility:
        notes = notes.filter(visibility=visibility)
    if collection_id:
        notes = notes.filter(collections__id=collection_id)

    return render(request, "notes_app/available_notes.html", {"notes": notes, "collections": collections})

#to do: iterate through all the files (check if one is an image -> if so, display, else display default image)

def view_notes(request):
    collections = Collection.objects.all()
    notes = Note.objects.all()
    notes_and_file = [] #creates a list of tuples (Note, NoteFile)
    for note in notes:
        files = NoteFile.objects.filter(note_id=note.id) #fetch an array of notefile objects
        
        #get default display icon and use it to make a notefile object
        response = urllib.request.urlopen('https://notes-sharing-app.s3.us-east-1.amazonaws.com/notes/default_image.png')
        file_obj = ContentFile(response.read(), name='notes/default_image.png')
        file_display_image = NoteFile(note=note,file=file_obj)
        
        #if any files associated with the note are images, use that instead of the defualt icon
        for file in files:
            if '.jpg' in str(file.file) or '.jpeg' in str(file.file) or '.png' in str(file.file):
                print('reached')
                file_display_image = file
                break
        notes_and_file.append((note, file_display_image))
    # title = request.GET.get("title")
    # subject = request.GET.get("subject")
    # semester = request.GET.get("semester")
    # date = request.GET.get("date")
    # visibility = request.GET.get("visibility")
    # collection_id = request.GET.get("collection")

    # if title:
    #     notes = notes.filter(title__icontains=title)
    # if subject:
    #     notes = notes.filter(subject__icontains=subject)
    # if semester:
    #     notes = notes.filter(semester__icontains=semester)
    # if date:
    #     notes = notes.filter(date=date)
    # if visibility:
    #     notes = notes.filter(visibility=visibility)
    # if collection_id:
    #     notes = notes.filter(collections__id=collection_id)

    return render(request, "notes_app/navbar_librarian/view_notes.html", {"notes": notes, "collections": collections, "notes_and_file": notes_and_file})

def edit_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    if request.method == 'POST':
        #update core note attributes 
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            note.save()
        else:
            messages.error(request, "Unable to modify note, note name already exists.")
            return render(request, "notes_app/edit_note.html", context={'form': form, 'files': files})
        
        #delete files from existing files that were not selected
        existing_files_to_keep = request.POST.getlist('select_files')
        for file in files:
            if file.file.url not in existing_files_to_keep:
                file.delete()    

        #add new files that were uploaded
        new_files = request.FILES.getlist('files') 
        for file in new_files:
            notefile = NoteFile()
            notefile.note = note
            notefile.file = file
            notefile.save()
        
        files = NoteFile.objects.filter(note_id=note_id) #refresh file information for new render
        messages.success(request, 'Note edited successfully!')
    else: #GET request
        form = NoteForm(instance=note)

    return render(request, "notes_app/edit_note.html", context={'form': form, 'files': files})

def view_full_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    return render(request, "notes_app/view_full_note.html", context={'note': note, 'files': files})

def delete_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    for file in files:
        boto3.client('s3').delete_object(Bucket='notes-sharing-app', Key=str(file.file))
    note.delete()

    collections = Collection.objects.all()
    notes = Note.objects.all()
    messages.success(request, "Successfully deleted note!")
    return render(request, "notes_app/navbar_librarian/view_notes.html", {"notes": notes, "collections": collections})

def add_notes(request):
    if request.method == 'POST':
        try:
            form = NoteForm(request.POST)
            if form.is_valid():
                note = form.save(commit=False)
                note.created_by = request.user
                note.save()

                files = request.FILES.getlist('files') #fetches from dictionary based on input html tag name in add_notes.html
                for file in files:
                    notefile = NoteFile()
                    notefile.note = note
                    notefile.file = file
                    notefile.save()
        except ValidationError as e:
            # Handle the validation error
            print("error was" + str(e.message_dict))  # This will show which field failed validation
            
            messages.success(request, 'Note created successfully!')
    return render(request, 'notes_app/navbar_librarian/add_notes.html', {'form': NoteForm()})

def index(request):
    return render(request, "notes_app/home.html")

def profile(request):
    return render(request, "notes_app/profile/profile.html")

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("/")  #go back to home page

def anonymous_view(request):
    return render(request, "notes_app/anonymous_view.html")


# Librarian Views
# def add_notes(request):
#     return render(request, "notes_app/navbar_librarian/add_notes.html")

def manage_borrowed(request):
    return render(request, "notes_app/navbar_librarian/manage_borrowed.html")

def view_requests(request):
    return render(request, "notes_app/navbar_librarian/view_requests.html")

# Patron Views
def available_notes(request):
    return render(request, "notes_app/navbar_patron/available_notes.html")

def request_notes(request):
    return render(request, "notes_app/navbar_patron/request_notes.html")

def borrowed_notes(request):
    return render(request, "notes_app/navbar_patron/borrowed_notes.html")

# assign new users to patrons group by default
@receiver(user_signed_up)
def assign_user_group(user, **kwargs):
    patron_group, created = Group.objects.get_or_create(name="Patrons")
    
    if not user.groups.filter(name="Patrons").exists():
        user.groups.add(patron_group)
        user.save()

@patron_required
def patron_dashboard(request):
    return render(request, "notes_app/patron_dashboard.html")

@librarian_required
def librarian_dashboard(request):
    patron_group = Group.objects.get(name="Patrons")
    patrons = patron_group.user_set.all()
    
    context = {
        'patrons': patrons,
    }
    return render(request, "notes_app/librarian_dashboard.html")


@method_decorator(librarian_required, name='dispatch')
class PromotePatronView(View):
    def get(self, request, patron_id, *args, **kwargs):
        # Retrieve patron using provided ID
        patron = get_object_or_404(User, id=patron_id)
        
        # Get the groups for patrons and librarians
        patrons_group = Group.objects.get(name="Patrons")
        librarians_group, created = Group.objects.get_or_create(name="Librarians")
        
        # If user is in Patrons group, promote them
        if patrons_group in patron.groups.all():
            patron.groups.remove(patrons_group)
            patron.groups.add(librarians_group)
            patron.save()
        
        # Redirect back to librarian dashboard after promotion
        return redirect("notes_app:librarian_dashboard")


def set_theme(request):
    theme = request.GET.get("theme","dark") #default dark
    response = redirect(request.META.get("HTTP_REFERER","/")) #Go back to page prev page
    response.set_cookie("theme", theme, max_age=10512000) #Third of a year
    return response


class EditProfileView(generic.UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "notes_app/profile/edit_profile.html"

    def get_object(self, queryset=None):
        return get_object_or_404(Profile, user=self.request.user)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("notes_app:profile")


