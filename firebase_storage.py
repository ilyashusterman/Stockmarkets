import os
from unittest import TestCase
from google.cloud import storage
from firebase import firebase

os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', './project.json')
URL = 'stocks-c6f94.appspot.com'



def get_storage():
    return storage.Client()


def initiate_firebase():
    fb = firebase.FirebaseApplication('https://{}'.format(URL),
                                      authentication=None)
    fb.storage = get_storage()
    fb.bucket = fb.storage.get_bucket(URL)
    return fb


class FirebaseStorage(object):
    def __init__(self):
        self.firebase = initiate_firebase()


class TestFirebaseStorage(TestCase):
    def setUp(self):
        self.storage = FirebaseStorage()

    def test_upload_file(self):
        filename = 'model.pkl'
        test_blob = self.storage.firebase.bucket.blob('/')
        # with open(filename, 'r+') as file:
        test_blob.upload_from_filename(filename)
