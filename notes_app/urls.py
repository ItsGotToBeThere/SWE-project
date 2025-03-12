from django.urls import path
from . import views
from .views import available_notes, request_notes, borrowed_notes

app_name = "notes_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("set-theme/", views.set_theme, name="set_theme"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.EditProfileView.as_view(), name="edit_profile"),
    path("accounts/logout/", views.logout_view, name="account_logout"),
    path("logout/", views.logout_view, name="logout_view"),
    
    path("patron-dashboard/", views.patron_dashboard, name='patron_dashboard'),
    path("librarian-dashboard/", views.librarian_dashboard, name='librarian_dashboard'),
    path("promote/<int:patron_id>/", views.PromotePatronView.as_view(), name='promote_patron_view'),
    
    #patron specific urls
    path("available-notes/", views.available_notes, name="available_notes"),
    path("request-notes/", views.request_notes, name="request_notes"),
    path("borrowed-notes/", views.borrowed_notes, name="borrowed_notes"),

    #librarian specific urls
    path("add-notes/", views.add_notes, name="add_notes"),
    path("view-notes/", views.view_notes, name="view_notes"),
    path("manage-borrowed/", views.manage_borrowed, name="manage_borrowed"),
    path("view_full_note/<int:note_id>/", views.view_full_note, name="view_full_note"),
    path("edit_note/<int:note_id>/", views.edit_note, name="edit_note"),
    path("delete_note/<int:note_id>/", views.delete_note, name="delete_note"),
    path("view-requests/", views.view_requests, name="view_requests"),
]
