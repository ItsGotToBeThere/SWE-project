from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth.decorators import login_required
from .decorators import librarian_required, patron_required
from django.views import View
from django.utils.decorators import method_decorator

from django.core.files.storage import FileSystemStorage
from .models import Note, Collection

def add_notes(request):
    if request.method == "POST":
        title = request.POST["title"]
        subject = request.POST["subject"]
        semester = request.POST["semester"]
        date = request.POST["date"]
        visibility = request.POST["visibility"]
        description = request.POST["description"]
        file = request.FILES["file"]

        # Process collections
        selected_collections = request.POST.getlist("collections")  # Multi-select returns list
        new_collection_name = request.POST.get("new_collection")  # Check for new collection input

        # Save file to media directory
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)

        # Create the note
        note = Note.objects.create(
            title=title,
            subject=subject,
            semester=semester,
            date=date,
            visibility=visibility,
            description=description,
            file=file
        )

        # Add selected collections
        for collection_id in selected_collections:
            collection = Collection.objects.get(id=collection_id)
            note.collections.add(collection)

        # Create and add new collection if provided
        if new_collection_name:
            new_collection, created = Collection.objects.get_or_create(name=new_collection_name)
            note.collections.add(new_collection)

        return redirect("notes_app:librarian_dashboard")  # Redirect after successful upload

    # Pass existing collections to the template
    collections = Collection.objects.all()
    return render(request, "notes_app/navbar_librarian/add_notes.html", {"collections": collections})

def index(request):
    return render(request, "notes_app/home.html")

def profile(request):
    return render(request, "notes_app/profile.html")

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("/")  #go back to home page

def anonymous_view(request):
    return render(request, "notes_app/anonymous_view.html")


# Librarian Views
def add_notes(request):
    return render(request, "notes_app/navbar_librarian/add_notes.html")

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

# Dashboards
def librarian_dashboard(request):
    return render(request, "notes_app/librarian_dashboard.html")

def patron_dashboard(request):
    return render(request, "notes_app/patron_dashboard.html")

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

