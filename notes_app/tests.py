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

    def test_collection_creation(self):
        collection = Collection.objects.get(title='Test Collection')
        self.assertEqual(collection.title, 'Test Collection')
        self.assertEqual(collection.description, 'This is a test collection.')
        self.assertEqual(collection.created_by, self.user)

    def test_note_creation(self):
        note = Note.objects.get(title='Test Note')
        self.assertEqual(note.title, 'Test Note')
        self.assertEqual(note.description, 'This is a test note.')
        self.assertEqual(note.course_name, 'Test Course')
        self.assertEqual(note.created_by, self.user)

    def test_note_file_creation(self):
        file = SimpleUploadedFile("test_file.txt", b"Hello World")
        note_file = NoteFile.objects.create(note=self.note, file=file)
        self.assertIsNotNone(note_file.file)

    def test_collection_item_creation(self):
        collection_item = CollectionItem.objects.create(note=self.note, collection=self.collection)
        self.assertEqual(collection_item.note, self.note)
        self.assertEqual(collection_item.collection, self.collection)

    def test_private_collection_patron_creation(self):
        patron = PrivateCollectionPatron.objects.create(patron=self.user, collection=self.collection)
        self.assertEqual(patron.patron, self.user)
        self.assertEqual(patron.collection, self.collection)

