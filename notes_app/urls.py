from django.urls import path
from . import views
from .views import available_notes, request_notes, borrowed_notes

app_name = "notes_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("set-theme/", views.set_theme, name="set_theme"),
    path("profile/", views.profile, name="profile"),
    path("accounts/logout/", views.logout_view, name="account_logout"),
    path("logout/", views.logout_view, name="logout_view"),
    
    path("patron-dashboard/", views.patron_dashboard, name='patron_dashboard'),
    path("librarian-dashboard/", views.librarian_dashboard, name='librarian_dashboard'),
    path("promote/<int:patron_id>/", views.PromotePatronView.as_view(), name='promote_patron_view'),
    
    path("available-notes/", views.available_notes, name="available_notes"),
    path("request-notes/", views.request_notes, name="request_notes"),
    path("borrowed-notes/", views.borrowed_notes, name="borrowed_notes"),

    path("add-notes/", views.add_notes, name="add_notes"),
    path("manage-borrowed/", views.manage_borrowed, name="manage_borrowed"),
    path("view-requests/", views.view_requests, name="view_requests"),
]
