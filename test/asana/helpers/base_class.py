from unittest import TestCase
from test.asana.helpers.dynamodb_client import DynamoDbClient


class BaseClass(TestCase):
    def setUp(self):
        DynamoDbClient.initialize()
