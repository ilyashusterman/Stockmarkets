from unittest import TestCase

from firebase import firebase
import firebase as fb

URL = 'https://stocks-c6f94.appspot.com/'


class FirebaseStorage(object):
    def __init__(self):
        self.firebase = firebase.FirebaseApplication(URL, authentication=None)


class TestFirebaseStorage(TestCase):
    def setUp(self):
        self.storage = FirebaseStorage()

    def test_upload_file(self):
        filename = 'model.pkl'
        with open(filename,  'r+') as file:
            self.storage.firebase.post('/models', file)