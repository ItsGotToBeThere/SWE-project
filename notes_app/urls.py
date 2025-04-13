from django.urls import path
from . import views
app_name = "notes_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("set-theme/", views.set_theme, name="set_theme"),
    path("profile/", views.profile, name="profile"),
    path("profile/notes", views.profile_notes, name="profile_notes"),
    path("profile/edit/", views.EditProfileView.as_view(), name="edit_profile"),
    path("accounts/logout/", views.logout_view, name="account_logout"),
    path("logout/", views.logout_view, name="logout_view"),
    
    path("patron-dashboard/", views.patron_dashboard, name='patron_dashboard'),
    path("librarian-dashboard/", views.librarian_dashboard, name='librarian_dashboard'),
    path("promote/<int:patron_id>/", views.PromotePatronView.as_view(), name='promote_patron_view'),
    # path("elevate-patron/<int:patron_id>/", views.elevate_patron, name="elevate_patron"),

    #patron specific urls
    path("available-notes/", views.available_notes, name="available_notes"),
    path("request-collections/", views.request_collections, name="request_collections"),
    path("request-collection/<int:collection_id>/", views.request_collection, name="request_collection"),

    path("patron-view-collections/", views.patron_view_collections, name="patron_view_collections"),
    path("borrowed-collections/", views.borrowed_collections, name="borrowed_collections"),
    path("borrowed-notes/", views.borrowed_notes, name="borrowed_notes"),
    path("create-patron-collection/", views.create_patron_collection, name="create_patron_collection"),
    path("review-note/<int:note_id>", views.review_note, name="review_note"),
    path("request-note/<int:note_id>", views.request_note, name="request_note"),

    #librarian specific urls

    #note related
    path("add-notes/", views.add_notes, name="add_notes"),
    path("view-notes/", views.view_notes, name="view_notes"),
    path("view_note_details/<int:note_id>/", views.view_note_details, name="view_note_details"),
    path("note/<int:note_id>", views.view_clean_note, name="view_clean_note"),
    path("edit_note/<int:note_id>/", views.edit_note, name="edit_note"),
    path("delete_note/<int:note_id>/", views.delete_note, name="delete_note"),
    
    #collection related
    path("create-collection/", views.create_collection, name="create_collection"),
    path("view-collections/", views.view_collections, name="view_collections"),
    path("view_full_collection/<int:collection_id>/", views.view_full_collection, name="view_full_collection"),
    path("edit_collection/<int:collection_id>/", views.edit_collection, name="edit_collection"),
    path("delete_collection/<int:collection_id>/", views.delete_collection, name="delete_collection"),
    path("manage-borrowed/", views.manage_borrowed, name="manage_borrowed"),

    #permissions related
    path("view-requests/", views.view_requests, name="view_requests"),

    #anonymous user
    path("browse-notes/", views.browse_notes, name="browse_notes"),
    path("anonymous_view_note/<int:note_id>/", views.anonymous_view_note, name="anonymous_view_note"),
]
