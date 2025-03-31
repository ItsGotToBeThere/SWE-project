from django.contrib.auth import logout
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.views import generic
from django.contrib.auth.models import User
from .decorators import librarian_required, patron_required
from django.views import View
from django.utils.decorators import method_decorator
from .models import Note, Collection, PatronRequest, Profile, NoteFile, CollectionItem, PrivateCollectionPatron, NoteReview
from .filters import NotesFilter, CollectionsFilter
from .forms import NoteForm, ProfileForm, CollectionForm, PatronCollectionForm, NoteReviewForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import boto3
import urllib.request
from django.core.files.base import ContentFile
from django.http import HttpResponseForbidden

#PERMISSION RELATED VIEWS
@method_decorator(librarian_required, name='dispatch')
class PromotePatronView(View):
    pass
#     def get(self, request, patron_id, *args, **kwargs):
#         # Retrieve patron using provided ID
#         patron = get_object_or_404(User, id=patron_id)
        
#         # Get the groups for patrons and librarians
#         patrons_group = Group.objects.get(name="Patrons")
#         librarians_group, created = Group.objects.get_or_create(name="Librarians")
        
#         # If user is in Patrons group, promote them
#         if patrons_group in patron.groups.all():
#             patron.groups.remove(patrons_group)
#             patron.groups.add(librarians_group)
#             patron.save()
        
#         # Redirect back to librarian dashboard after promotion
#         return redirect("notes_app:librarian_dashboard")

#     def is_librarian(user):
#         return user.profile.role == "librarian"

    # @login_required
    # @user_passes_test(is_librarian)
    # def elevate_patron(request, patron_id):
    #     patron_profile = get_object_or_404(Profile, user_id=patron_id)

    #     if patron_profile.role == "patron":  # Only elevate if they're a regular patron
    #         patron_profile.role = "elevated_patron"
    #         patron_profile.save()

    #         # Send email notification
    #         send_mail(
    #             subject="Your Patron Permissions Have Been Elevated!",
    #             message=f"Hello {patron_profile.get_preferred_name()},\n\nYour account has been upgraded to Elevated Patron status. You now have access to additional note-sharing features.",
    #             from_email="admin@classnotes.com",
    #             recipient_list=[patron_profile.user.email],
    #             fail_silently=False,
    #         )

    #         messages.success(request, f"{patron_profile.user.username} has been elevated to Elevated Patron.")

    #     return redirect("notes_app:librarian_dashboard")  # Redirect back to librarian dashboard
def manage_borrowed(request):
    return render(request, "notes_app/navbar_librarian/manage_borrowed.html")

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
    collections = Collection.objects.filter(is_requested=False, visibility="private")
    title_query = request.GET.get('title', '')
    semester_query = request.GET.get('semester', '')
    professor_query = request.GET.get('professor', '')
    collection_id = request.GET.get('collection', '')

    if title_query:
        notes = notes.filter(title__icontains=title_query)
        collections = collections.filter(title__icontains=title_query)
    if semester_query:
        notes = notes.filter(semester__icontains=semester_query)
    if professor_query:
        notes = notes.filter(professor__icontains=professor_query)
    if collection_id:
        notes = notes.filter(collectionitem__collection_id__exact=collection_id)

    if request.method == "POST":
        user = request.user
        note_id = request.POST.get("note_id")
        note = get_object_or_404(Note, id=note_id)
        note.is_requested = True
        patron_request = PatronRequest.objects.create(patron=user, note=note)
        patron_request.save()
        note.save()

        return redirect("notes_app:request_notes")  

    return render(request, "notes_app/navbar_patron/request_notes.html", {
        "notes": notes,
        "collections": collections
    })


def borrowed_notes(request):
    user = request.user
    notes = Note.objects.filter(
        Q(patronrequest__patron=user,patronrequest__status="approved") | Q(visibility="public")
    )
    collections = Collection.objects.filter(
        Q(privatecollectionpatron__patron=user) | Q(visibility="public")
    )
    title = request.GET.get("title")
    semester = request.GET.get("semester")
    professor = request.GET.get("professor")
    visibility = request.GET.get("visibility")
    collection_id = request.GET.get("collection")

    if title:
        notes = notes.filter(title__icontains=title)
    if semester:
        notes = notes.filter(semester__icontains=semester)
    if visibility:
        notes = notes.filter(visibility=visibility)
    if professor:
        notes = notes.filter(professor__icontains=professor)
    if collection_id:
        notes = notes.filter(collectionitem__collection_id__exact=collection_id)

    return render(request, "notes_app/navbar_patron/borrowed_notes.html", {"notes": notes, "collections": collections})

def view_requests(request):
    return render(request, "notes_app/navbar_librarian/view_requests.html")


#DISPLAYING AVAILABLE COLLECTIONS / NOTES VIEWS PATRON 
def filter_collections_and_notes(filtered_notes, filtered_collections):
    filtered_notes_associated_collections = set()

    # compare collection ids since it's easier to work with
    filtered_collections_ids = set(filtered_collections.values_list('id', flat=True))

    for note in filtered_notes:
        collections = Collection.objects.filter(collectionitem__note_id=note.id)
        for collection in collections:
            filtered_notes_associated_collections.add(collection.id)

    common_collection_ids = filtered_collections_ids & filtered_notes_associated_collections
    return Collection.objects.filter(id__in=common_collection_ids)

def patron_view_collections(request):
    collections_filter = CollectionsFilter(request.GET, queryset=Collection.objects.all())
    notes_filter = NotesFilter(request.GET, queryset=Note.objects.all())
    collections = filter_collections_and_notes(notes_filter.qs, collections_filter.qs)

    user_collections = collections.filter(created_by=request.user)
    private_collections = collections.filter(visibility="private")
    public_collections = collections.exclude(created_by=request.user)
    public_collections = public_collections.exclude(visibility="private")
    return render(request, "notes_app/navbar_patron/view_collections.html", {"public_collections": public_collections, "user_collections": user_collections, "private_collections": private_collections, "collections_filter": collections_filter, "notes_filter": notes_filter})

def available_notes(request):
    queryset = Note.objects.filter(visibility='public')
    notes = NotesFilter(request.GET, queryset=queryset)
    notes_and_file = get_notes_and_associated_file(notes.qs)
    return render(request, "notes_app/navbar_patron/available_notes.html", {"notes_and_file": notes_and_file, "notes_filter": notes})


#DISPLAYING AVAILABLE COLLECTIONS / NOTES VIEWS LIBRARIAN
def view_notes(request):
    notes = NotesFilter(request.GET, queryset=Note.objects.all())
    notes_and_file = get_notes_and_associated_file(notes.qs)
    return render(request, "notes_app/navbar_librarian/view_notes.html", {"notes_and_file": notes_and_file, "notes_filter": notes})

def view_collections(request):
    collections_filter = CollectionsFilter(request.GET, queryset=Collection.objects.all())
    notes_filter = NotesFilter(request.GET, queryset=Note.objects.all())
    collections = filter_collections_and_notes(notes_filter.qs, collections_filter.qs)
    return render(request, "notes_app/navbar_librarian/view_collections.html", {"collections": collections, "collections_filter": collections_filter, "notes_filter": notes_filter})


#DISPLAYING AVAILABLE COLLECTIONS / NOTES VIEWS LIBRARIAN + PATRON
def view_full_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    note_collections = CollectionItem.objects.filter(note=note)
    if request.user.groups.filter(name="Librarians").exists():
        user_type = 'Librarian'
    else:
        user_type = 'Patron'
    return render(request, "notes_app/view_full_note.html", context={'note': note, 'files': files, 'note_collections': note_collections, 'user_type':user_type})

def view_full_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id) 
    
    private_collection_patrons = []
    objects = PrivateCollectionPatron.objects.filter(collection_id=collection_id)
    for object in objects:
        private_collection_patrons.append(object.patron)
    
    #all librarians have access to all private collections
    librarians = []
    for user in User.objects.all():
        if Group.objects.get(name="Librarians") in user.groups.all():
            librarians.append(user)

    collection_notes = []
    collection_items = CollectionItem.objects.filter(collection_id=collection_id)
    for item in collection_items:
        collection_notes.append(item.note)
    return render(request, "notes_app/view_full_collection.html", context={'collection': collection, 'private_collection_patrons': private_collection_patrons, 'librarians': librarians, 'collection_notes': collection_notes})


#Helper function
def get_notes_and_associated_file(notes):
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
    return notes_and_file

#EDITING / MODIFICATION RELATED VIEWS LIBRARIAN + PATRON
@login_required
def create_patron_collection(request):
    # Fetch only public notes
    notes = Note.objects.filter(visibility="public")

    if request.method == 'POST':
        form = PatronCollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.created_by = request.user  # FIX: Assign the creator correctly
            collection.is_public = True  # Ensure the collection is public
            collection.save()

            # Save selected notes to the collection
            note_ids = request.POST.getlist('collection_notes')
            selected_notes = Note.objects.filter(id__in=note_ids)
            for note in selected_notes:
                CollectionItem.objects.create(note=note, collection=collection)

            messages.success(request, "Collection created successfully!")
    else:
        form = PatronCollectionForm()

    return render(request, 'notes_app/navbar_patron/create_patron_collection.html', {'form': form, 'notes': notes})

def review_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id)
    review, created = NoteReview.objects.get_or_create(note=note, patron=request.user)

    if request.method == 'POST':
        form = NoteReviewForm(request.POST, instance = review)
        if form.is_valid():
            if created:
                noteReview=form.save(commit=False)
                noteReview.note = note
                noteReview.patron = request.user
                noteReview.save()
            else:
                review.rating = form.cleaned_data['rating']
                review.comment = form.cleaned_data['comment']
                review.save()

            messages.success(request, "Note reviewed successfully!")
            return redirect("notes_app:available_notes")
    else:
        form = NoteReviewForm(instance = review)
    return render(request, 'notes_app/navbar_patron/review_notes.html',{'form':form,'note': note})


def edit_collection(request, collection_id):
    #need to pass notes (all notes + notes in collection), collection information, and then also private users if they exist
    collection = get_object_or_404(Collection, pk=collection_id) #fetch one note object
    collection_notes = [obj.note for obj in CollectionItem.objects.filter(collection_id=collection_id)]
    private_collection_patrons = [obj.patron for obj in PrivateCollectionPatron.objects.filter(collection_id=collection_id)]
    users = [user for user in User.objects.all() if Group.objects.get(name="Patrons") in user.groups.all()]
    notes = [note for note in Note.objects.all() if note.visibility == 'public']

    #add private notes that are part of the collection
    for note in collection_notes:
        if note not in notes: 
            notes.append(note)

    if request.method == 'POST':
        #update core note attributes 
        form = CollectionForm(request.POST, instance=collection)
        if form.is_valid():
            form.save() 
        else:
            messages.error(request, "Unable to modify collection, collection name already exists.")
            return render(request, "notes_app/edit_collection.html", context={'users': users, 'notes': notes, 'collection_notes':collection_notes, 'private_collection_patrons': private_collection_patrons})
        
        #remove notes from collection if they were part of the collection but were not selected to be in the modified collection
        new_collection_notes_list = request.POST.getlist('collection_notes')
        new_collection_notes = Note.objects.filter(title__in=new_collection_notes_list)
        for note in collection_notes:
            if note not in new_collection_notes:
                if note.visibility == 'private':
                    note.visibility = 'public'
                    note.save()
                collection_item = CollectionItem.objects.get(note=note, collection=collection)
                collection_item.delete()
            else: #ensure that the visibility is correct for notes still in the collection
                if note.visibility != collection.visibility:
                    note.visibility = collection.visibility
                    note.save()


        #add new notes that used to not be in the collection
        for note in new_collection_notes:
            if note not in collection_notes: #check to see if it wasn't part of the collection originally
                if collection.visibility == 'private':
                    note.visibility = 'private'
                    note.save()
                collection_item = CollectionItem(note=note, collection=collection)
                collection_item.save()

        if collection.visibility == 'private':
            #remove patrons from collection if they were part of the collection but were not selected to be in the modified collection
            new_patron_list_emails = request.POST.getlist('access_users')
            new_patron_list = User.objects.filter(email__in=new_patron_list_emails)
            for patron in private_collection_patrons:
                if patron not in new_patron_list:
                    collection_patron = PrivateCollectionPatron.objects.get(patron=patron, collection=collection)
                    collection_patron.delete()

            #add new patrons that used to not be in the collection
            for patron in new_patron_list:
                if patron not in private_collection_patrons: #check to see if it wasn't part of the collection originally
                    print("reached")
                    collection_patron = PrivateCollectionPatron(patron=patron, collection=collection)
                    collection_patron.save()
        
        #refresh information
        collection_notes = [obj.note for obj in CollectionItem.objects.filter(collection_id=collection_id)]
        private_collection_patrons = [obj.patron for obj in PrivateCollectionPatron.objects.filter(collection_id=collection_id)]
        collection = get_object_or_404(Collection, pk=collection_id)

        messages.success(request, 'Collection edited successfully!')
    else: #GET request
        form = CollectionForm(instance=collection)

    return render(request, "notes_app/edit_collection.html", context={'form':form, 'collection':collection, 'users': users, 'notes': notes, 'collection_notes':collection_notes, 'private_collection_patrons': private_collection_patrons})

def delete_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id) 
    if collection.visibility == 'private':
        notes = [object.note for object in CollectionItem.objects.filter(collection=collection)]
        for note in notes:
            note.visibility = 'public'
            note.save()  
    collection.delete()
    if request.user.groups.filter(name="Librarians").exists(): 
        return redirect("notes_app:view_collections") 
    else:
        return redirect("notes_app:patron_view_collections") 

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

def add_notes(request):
    if request.method == 'POST':
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
            messages.success(request, 'Note created successfully!')
        else:
            messages.error(request, 'Note with that title already exists, please try again.')
    return render(request, 'notes_app/navbar_librarian/add_notes.html', {'form': NoteForm()})

def create_collection(request):
    users = []
    for user in User.objects.all():
        if Group.objects.get(name="Patrons") in user.groups.all():
            users.append(user)
    
    notes = []
    for note in Note.objects.all():
        if note.visibility == 'public':
            notes.append(note)

    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.created_by = request.user
            collection.save()
        
            #create a list of note objects from note names
            note_names_in_collection = request.POST.getlist('collection_notes')
            notes_in_collection = []
            for note in Note.objects.all():
                if note.title in note_names_in_collection:
                    notes_in_collection.append(note)

            for note in notes_in_collection:
                if collection.visibility == 'private':
                    CollectionItem.objects.filter(note=note).delete() #remove from all public collections
                    note.visibility = 'private'
                    note.save() 
                collection_item = CollectionItem(note=note, collection=collection)
                collection_item.save()
            if collection.visibility == 'private':
                private_collection_patrons_with_access = request.POST.getlist('access_users')
                for access_patron in private_collection_patrons_with_access:
                    for patron in users:
                        if patron.email == access_patron:
                            patron = PrivateCollectionPatron(patron = patron, collection = collection)
                            patron.save()

            messages.success(request, 'Collection created successfully!')
        else:
            messages.error(request, 'Collection with that title already exists, please try again.')
    return render(request, 'notes_app/navbar_librarian/create_collection.html', {'form': CollectionForm(), 'notes': notes, 'users': users })


#OTHER VIEWS
def index(request):
    return render(request, "notes_app/home.html")

def profile(request):
    if request.user.is_authenticated:
        collections = Collection.objects.filter(
         Q(created_by=request.user) | Q(privatecollectionpatron__patron=request.user)
        )
    else:
        collections = []

    return render(request, "notes_app/profile/profile_collections.html",{'content': collections,})

def profile_notes(request):
    notes = []
    if request.user.is_authenticated:
        if request.user.groups.filter(name="Patrons").exists():
            notes = Note.objects.filter(patronrequest__patron=request.user)
        elif request.user.groups.filter(name="Librarians").exists():
            notes = Note.objects.filter(created_by=request.user)
    return render(request, "notes_app/profile/profile_notes.html",{'content': notes,})


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("/")  #go back to home page

def anonymous_view(request):
    return render(request, "notes_app/anonymous_view.html")

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


