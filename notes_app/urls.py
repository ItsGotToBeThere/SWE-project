from django.urls import path
from . import views

app_name = "notes_app"

urlpatterns = [
    path("", views.dashboard, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("accounts/logout/", views.logout_view, name="account_logout"),
    path("logout/", views.logout_view, name="logout_view"),
    
    path("patron-dashboard/", views.patron_dashboard, name='patron_dashboard'),
    path("librarian-dashboard/", views.librarian_dashboard, name='librarian_dashboard'),
]
