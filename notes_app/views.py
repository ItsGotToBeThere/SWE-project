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

def index(request):
    return render(request, "notes_app/home.html")

def dashboard(request):
    return render(request, "notes_app/dashboard.html")

@login_required
def logout_view(request):
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