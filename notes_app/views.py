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
from .models import Note, Collection, PatronRequest, Profile, NoteFile, CollectionItem, PrivateCollectionPatron, NoteReview, CollectionAccessRequest, RequestNote
from .filters import NotesFilter, CollectionsFilter
from .forms import NoteForm, ProfileForm, CollectionForm, PatronCollectionForm, NoteReviewForm, RequestNoteForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import boto3
import urllib.request
from django.core.files.base import ContentFile
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

#PERMISSION RELATED VIEWS
def request_note(request, note_id):
    if request.method == 'POST':
        form = RequestNoteForm(request.POST)
        if form.is_valid():
            note_request = form.save(commit=False)
            note_request.requester = request.user  
            note_request.note = get_object_or_404(Note, id=note_id)
            note_request.save()
            messages.success(request, "Request successfully created!")
        else:
            messages.error(request, "Request failed, please choose a valid date!")
    form = RequestNoteForm()

    return render(request, 'notes_app/navbar_patron/request_note.html', {'form': form})

#display patrons requests for notes, provide an interface for librarians to handle requests
def manage_borrowed(request):
    if request.method == "POST":
        note_request_id = request.POST.get("request_id") #fetch based on button name field
        action = request.POST.get("action") #get the action variable, which gets set by either the approve or deny button
        note_request = get_object_or_404(RequestNote, id=note_request_id)
        if action == "approve":
            note_request.borrowed = True
            note_request.fulfilled_at = timezone.now()
        elif action == "deny":
            note_request.borrowed = False
            note_request.fulfilled_at = timezone.now()
        note_request.save()
    in_progress_requests = RequestNote.objects.filter(fulfilled_at__isnull=True, return_date__gt=timezone.now(), borrowed=False)
    active_borrows = RequestNote.objects.filter(return_date__gt=timezone.now(), borrowed=True, fulfilled_at__lt=timezone.now())
    past_requests = RequestNote.objects.filter(fulfilled_at__isnull=False, fulfilled_at__lt=timezone.now()).exclude(return_date__gt=timezone.now(), borrowed = True)
    RequestNote.objects.update(is_viewed=True)
    return render(request, "notes_app/navbar_librarian/manage_borrowed.html", {"in_progress_requests": in_progress_requests, "active_borrows": active_borrows, "past_requests":past_requests})

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


@login_required
@user_passes_test(lambda u: u.groups.filter(name="Librarians").exists())
def view_requests(request):
    requests = CollectionAccessRequest.objects.filter(status="pending")  # Only pending

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        req = get_object_or_404(CollectionAccessRequest, id=request_id)

        if action == "approve":
            req.status = "approved"
            PrivateCollectionPatron.objects.get_or_create(
                patron=req.patron,
                collection=req.collection
            )
        elif action == "deny":
            req.status = "denied"

        req.save()
        return redirect("notes_app:view_requests") 

    return render(request, "notes_app/navbar_librarian/view_requests.html", {
        "requests": requests
    })


@login_required
def borrowed_collections(request):
    patron = request.user
    borrowed = PrivateCollectionPatron.objects.filter(patron=patron).select_related('collection')
    collections = [entry.collection for entry in borrowed]

    return render(request, "notes_app/navbar_patron/borrowed_collections.html", {
        "borrowed_collections": collections
    })

def borrowed_notes(request):
    in_progress_requests = RequestNote.objects.filter(requester=request.user, fulfilled_at__isnull=True, return_date__gt=timezone.now(), borrowed=False)
    active_borrows = RequestNote.objects.filter(requester=request.user, return_date__gt=timezone.now(), borrowed=True, fulfilled_at__lt=timezone.now())
    past_requests = RequestNote.objects.filter(requester=request.user, fulfilled_at__isnull=False, fulfilled_at__lt=timezone.now()).exclude(return_date__gt=timezone.now(), borrowed = True)
    return render(request, "notes_app/navbar_patron/borrowed_notes.html", {"in_progress_requests": in_progress_requests, "active_borrows": active_borrows, "past_requests":past_requests})

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
from django.db.models import Q

from django.db.models import Q

@login_required
def patron_view_collections(request):
    collections_filter = CollectionsFilter(request.GET, queryset=Collection.objects.all())
    notes_filter = NotesFilter(request.GET, queryset=Note.objects.all())
    collections = filter_collections_and_notes(notes_filter.qs, collections_filter.qs)

    # Collections the patron created (they can edit/delete these)
    user_collections = collections.filter(created_by=request.user, visibility="public")

    # All public collections (excluding ones they created, already shown above)
    public_collections = collections.filter(visibility="public").exclude(created_by=request.user)

    # Private collections they have been granted access to (read-only view)
    private_collections_with_access = collections.filter(
        visibility="private",
        privatecollectionpatron__patron=request.user
    )

    user = request.user
    all_private = Collection.objects.filter(visibility="private")
    approved_ids = PrivateCollectionPatron.objects.filter(patron=user).values_list("collection_id", flat=True)
    all_private = all_private.exclude(id__in=approved_ids)

    existing_requests = CollectionAccessRequest.objects.filter(patron=user)
    requested_ids = existing_requests.values_list("collection_id", flat=True)
    denied_ids = existing_requests.filter(status="denied").values_list("collection_id", flat=True)
    pending_ids = existing_requests.filter(status="pending").values_list("collection_id", flat=True)

    return render(request, "notes_app/navbar_patron/view_collections.html", {
        "collections_filter": collections_filter,
        "notes_filter": notes_filter,
        "user_collections": user_collections,
        "public_collections": public_collections,
        "private_collections_with_access": private_collections_with_access,
        "private_collections_without_access": all_private,
        "pending_collection_ids": set(pending_ids),
        "denied_collection_ids": set(denied_ids),
    })


def available_notes(request):
    queryset = Note.objects.filter(visibility='public')
    notes_filter = NotesFilter(request.GET, queryset=queryset)
    notes = notes_filter.qs
    return render(request, "notes_app/navbar_patron/available_notes.html", {"notes": notes, "notes_filter": notes_filter})

@login_required
def request_collection(request, collection_id):
    collection = get_object_or_404(Collection, pk=collection_id)
    CollectionAccessRequest.objects.get_or_create(patron=request.user, collection=collection)
    messages.success(request, "Access request sent to librarians.")
    return redirect("notes_app:patron_view_collections")


#DISPLAYING AVAILABLE COLLECTIONS / NOTES VIEWS LIBRARIAN
def view_notes(request):
    notes_filter = NotesFilter(request.GET, queryset=Note.objects.all())
    notes = notes_filter.qs
    return render(request, "notes_app/navbar_librarian/view_notes.html", {"notes_filter": notes_filter, 'notes': notes})

def view_collections(request):
    collections_filter = CollectionsFilter(request.GET, queryset=Collection.objects.all())
    notes_filter = NotesFilter(request.GET, queryset=Note.objects.all())
    collections = filter_collections_and_notes(notes_filter.qs, collections_filter.qs)
    return render(request, "notes_app/navbar_librarian/view_collections.html", {"collections": collections, "collections_filter": collections_filter, "notes_filter": notes_filter})


#DISPLAYING AVAILABLE COLLECTIONS / NOTES VIEWS LIBRARIAN + PATRON
def view_note_details(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    note_collections = CollectionItem.objects.filter(note=note)
    if request.user.groups.filter(name="Librarians").exists():
        user_type = 'Librarian'
    else:
        user_type = 'Patron'
    patron_can_view_note_files = RequestNote.objects.filter(requester = request.user, return_date__gt=timezone.now(), borrowed=True, fulfilled_at__lt=timezone.now()) #template checks to see if this has length greater than 0
    return render(request, "notes_app/view_note_details.html", context={'note': note, 'files': files, 'note_collections': note_collections, 'user_type':user_type, 'patron_can_view_note_files':patron_can_view_note_files})

def anonymous_view_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    note_collections = CollectionItem.objects.filter(note=note)
    return render(request, "notes_app/anonymous_view_note.html", context={'note': note, 'files': files, 'note_collections': note_collections})

def view_clean_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    return render(request,"notes_app/view_clean_note.html",context={'note': note, 'files':files})

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
        if request.user.groups.filter(name="Librarians").exists():
            form = CollectionForm(request.POST, instance=collection)
        else:
            form = PatronCollectionForm(request.POST, instance=collection)

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
    
    if request.user.groups.filter(name="Librarians").exists():
        user_type = 'Librarian'
        form = CollectionForm(instance=collection)
    else:
        user_type = 'Patron'
        form = PatronCollectionForm(instance=collection)

    return render(request, "notes_app/edit_collection.html", context={'user_type': user_type, 'form':form, 'collection':collection, 'users': users, 'notes': notes, 'collection_notes':collection_notes, 'private_collection_patrons': private_collection_patrons})

def delete_collection(request, collection_id):
    next_url = request.GET.get('next')
    collection = get_object_or_404(Collection, pk=collection_id)
    if collection.visibility == 'private':
        notes = [object.note for object in CollectionItem.objects.filter(collection=collection)]
        for note in notes:
            note.visibility = 'public'
            note.save()  
    collection.delete()
    if request.user.groups.filter(name="Librarians").exists(): 
        return redirect(next_url)
    else:
        return redirect(next_url)

def delete_note(request, note_id):
    next_url = request.GET.get('next')
    note = get_object_or_404(Note, pk=note_id) #fetch one note object
    files = NoteFile.objects.filter(note_id=note_id) #fetch an array of notefile objects
    for file in files:
        boto3.client('s3').delete_object(Bucket='notes-sharing-app', Key=str(file.file))
    note.delete()

    collections = Collection.objects.all()
    notes = Note.objects.all()
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
    notification_count = RequestNote.objects.filter(is_viewed=False).count()
    return render(request, "notes_app/home.html", {'notification_count':notification_count})

def profile(request):
    notes = []
    if request.user.is_authenticated:
        collections = Collection.objects.filter(
         Q(created_by=request.user) | Q(privatecollectionpatron__patron=request.user)
        )
        if request.user.groups.filter(name="Patrons").exists():
            notes = Note.objects.filter(
                Q(requestnote__requester=request.user) & Q(requestnote__borrowed=True) & Q(
                    requestnote__return_date__gt=timezone.now()) & Q(requestnote__fulfilled_at__lt=timezone.now())
            )
        elif request.user.groups.filter(name="Librarians").exists():
            notes = Note.objects.filter(created_by=request.user)
    else:
        collections = []

    return render(request, "notes_app/profile/profile_collections.html",{'collections': collections,'notes':notes})

def profile_notes(request):
    notes = []
    if request.user.is_authenticated:
        collections = Collection.objects.filter(
         Q(created_by=request.user) | Q(privatecollectionpatron__patron=request.user)
        )
        if request.user.groups.filter(name="Patrons").exists():
            notes = Note.objects.filter(
                Q(requestnote__requester=request.user) & Q(requestnote__borrowed=True) & Q(requestnote__return_date__gt=timezone.now()) & Q(requestnote__fulfilled_at__lt=timezone.now())
            )
        elif request.user.groups.filter(name="Librarians").exists():
            notes = Note.objects.filter(created_by=request.user)
    else:
        collections = []

    return render(request, "notes_app/profile/profile_notes.html",{'collections': collections,'notes':notes})


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
    return render(request, "notes_app/navbar_librarian/list_patrons.html", context)


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

@login_required
@librarian_required
def list_patrons(request):
    patrons_group = Group.objects.get(name="Patrons")
    patrons = patrons_group.user_set.all()

    if request.method == "POST":
        patron_id = request.POST.get("patron_id")
        patron = get_object_or_404(User, id=patron_id)
        librarians_group, _ = Group.objects.get_or_create(name="Librarians")

        if librarians_group not in patron.groups.all():
            patron.groups.add(librarians_group)
            patron.groups.remove(patrons_group)
            messages.success(request, f"{patron.username} has been promoted to Librarian.")
        else:
            messages.info(request, f"{patron.username} is already a Librarian.")

        return redirect("notes_app:list_patrons")

    return render(request, "notes_app/navbar_librarian/list_patrons.html", {"patrons": patrons})

def anonymous_browse_notes(request):
    # Notes in public collections or not in any collection at all
    public_collections = Collection.objects.filter(visibility="public")
    notes = Note.objects.filter(
        Q(collectionitem__collection__in=public_collections) | ~Q(id__in=CollectionItem.objects.values('note'))
    ).filter(visibility="public").distinct()  # Remove duplicates if note is in multiple collections

    notes_filter = NotesFilter(request.GET, queryset=notes)
    return render(request, "notes_app/anonymous_browse_notes.html", {
        "notes": notes_filter.qs,
        "notes_filter": notes_filter,
    })

def anonymous_view_note(request, note_id):
    note = get_object_or_404(Note, pk=note_id, visibility="public")
    private_collections = Collection.objects.filter(visibility="private")
    in_private = CollectionItem.objects.filter(note=note, collection__in=private_collections).exists()
    if in_private:
        return redirect("notes_app:anonymous_browse_notes")
    files = NoteFile.objects.filter(note=note)
    return render(request, "notes_app/anonymous_view_note.html", {"note": note, "files": files})



