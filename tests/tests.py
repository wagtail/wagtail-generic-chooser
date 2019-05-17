import json

from django.contrib.auth.models import User
from django.test import TestCase


class TestChooseView(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        response = self.client.get('/admin/site-chooser/chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<h1 class="icon icon-site">Choose a site</h1>',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/site-chooser/chooser/1/">localhost [default]</a>',
            response_json['html']
        )


class TestChosenView(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        response = self.client.get('/admin/site-chooser/chooser/1/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'chosen')
        self.assertEqual(
            response_json['result'],
            {"id": "1", "string": "localhost [default]", "edit_link": "/admin/sites/1/"}
        )
