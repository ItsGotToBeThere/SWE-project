from django.test import TestCase
from django.contrib.auth.models import User
from notes_app.models import Collection, Note, NoteFile, CollectionItem, PrivateCollectionPatron
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
# NOTE: this is a temp testing file and needs additional tests
# TODO: add tests for google auth (logging in) for librarian + patron views -> may need to force google login

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.collection = Collection.objects.create(title='Test Collection', description='This is a test collection.', created_by=self.user)
        self.note = Note.objects.create(title='Test Note', description='This is a test note.', course_name='Test Course', created_by=self.user)

        # creating patron user
        self.patron = User.objects.create_user(username='patron_user', email='patron@example.com', password='password123')
        self.patron_group, _ = Group.objects.get_or_create(name="Patrons")
        self.patron.groups.add(self.patron_group)

        # creating other patron user
        self.other_patron = User.objects.create_user(username='other_patron', email='other_patron@example.com', password='password123')
        self.other_patron.groups.add(self.patron_group)

        # creating librian
        self.librarian = User.objects.create_user(username='librarian_user', email='librarian@example.com', password='password123')
        self.librarian_group, _ = Group.objects.get_or_create(name="Librarians")
        self.librarian.groups.add(self.librarian_group)

        # Create Public Notes
        self.note1 = Note.objects.create(title="Public Note 1", visibility="public", created_by=self.patron)
        self.note2 = Note.objects.create(title="Public Note 2", visibility="public", created_by=self.patron)

        # Patron Creates a Collection
        self.patron_collection = Collection.objects.create(
            title="Patron Collection", 
            description="Collection created by a Patron", 
            created_by=self.patron, 
            visibility="public"
        )
        CollectionItem.objects.create(collection=self.patron_collection, note=self.note1)

    # def test_collection_creation(self):
    #     collection = Collection.objects.get(title='Test Collection')
    #     self.assertEqual(collection.title, 'Test Collection')
    #     self.assertEqual(collection.description, 'This is a test collection.')
    #     self.assertEqual(collection.created_by, self.user)

    # def test_note_creation(self):
    #     note = Note.objects.get(title='Test Note')
    #     self.assertEqual(note.title, 'Test Note')
    #     self.assertEqual(note.description, 'This is a test note.')
    #     self.assertEqual(note.course_name, 'Test Course')
    #     self.assertEqual(note.created_by, self.user)

    # def test_note_file_creation(self):
    #     file = SimpleUploadedFile("test_file.txt", b"Hello World")
    #     note_file = NoteFile.objects.create(note=self.note, file=file)
    #     self.assertIsNotNone(note_file.file)

    # def test_collection_item_creation(self):
    #     collection_item = CollectionItem.objects.create(note=self.note, collection=self.collection)
    #     self.assertEqual(collection_item.note, self.note)
    #     self.assertEqual(collection_item.collection, self.collection)

    # def test_private_collection_patron_creation(self):
    #     patron = PrivateCollectionPatron.objects.create(patron=self.user, collection=self.collection)
    #     self.assertEqual(patron.patron, self.user)
    #     self.assertEqual(patron.collection, self.collection)
    
    # patron collection creation tests

    def test_patron_can_create_public_collection(self):
        """Test if a Patron can successfully create a public collection."""
        self.client.login(username='patron_user', password='password123')
        response = self.client.post(reverse('notes_app:create_patron_collection'), {
            'title': 'New Patron Collection',
            'description': 'Test collection',
            'collection_notes': [self.note1.id, self.note2.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirect means success
        self.assertTrue(Collection.objects.filter(title="New Patron Collection").exists())

    def test_patron_can_edit_own_collection(self):
        """Test that a Patron can edit their own collection."""
        self.client.login(username='patron_user', password='password123')
        response = self.client.post(reverse('notes_app:edit_collection', args=[self.patron_collection.id]), {
            'title': 'Updated Patron Collection',
            'description': 'Updated description',
        })
        self.assertEqual(response.status_code, 302)
        self.patron_collection.refresh_from_db()
        self.assertEqual(self.patron_collection.title, "Updated Patron Collection")

    def test_patron_cannot_edit_other_patrons_collection(self):
        """Test that a Patron cannot edit another Patron's collection."""
        self.client.login(username='other_patron', password='password123')
        response = self.client.post(reverse('notes_app:edit_collection', args=[self.patron_collection.id]), {
            'title': 'Hacked Collection',
            'description': 'Trying to edit someone else’s collection',
        })
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_patron_can_delete_own_collection(self):
        """Test that a Patron can delete their own collection."""
        self.client.login(username='patron_user', password='password123')
        response = self.client.post(reverse('notes_app:delete_collection', args=[self.patron_collection.id]))
        self.assertEqual(response.status_code, 302)  # Redirect means success
        self.assertFalse(Collection.objects.filter(id=self.patron_collection.id).exists())

    def test_patron_cannot_delete_other_patrons_collection(self):
        """Test that a Patron cannot delete another Patron's collection."""
        self.client.login(username='other_patron', password='password123')
        response = self.client.post(reverse('notes_app:delete_collection', args=[self.patron_collection.id]))
        self.assertEqual(response.status_code, 403)  # Forbidden
        self.assertTrue(Collection.objects.filter(id=self.patron_collection.id).exists())

    def test_librarian_can_edit_any_patrons_collection(self):
        """Test that a Librarian can edit any Patron's collection."""
        self.client.login(username='librarian_user', password='password123')
        response = self.client.post(reverse('notes_app:edit_collection', args=[self.patron_collection.id]), {
            'title': 'Librarian Updated Collection',
            'description': 'Librarian edited this',
        })
        self.assertEqual(response.status_code, 302)
        self.patron_collection.refresh_from_db()
        self.assertEqual(self.patron_collection.title, "Librarian Updated Collection")

    def test_librarian_can_delete_any_patrons_collection(self):
        """Test that a Librarian can delete any Patron's collection."""
        self.client.login(username='librarian_user', password='password123')
        response = self.client.post(reverse('notes_app:delete_collection', args=[self.patron_collection.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Collection.objects.filter(id=self.patron_collection.id).exists())

