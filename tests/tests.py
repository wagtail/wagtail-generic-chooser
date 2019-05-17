import json
from urllib.parse import urlencode, urlparse
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from wagtail.core.models import Page, Site


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

    def test_pagination(self):
        page = Page.objects.first()
        for i in range(0, 25):
            Site.objects.create(hostname='%d.example.com' % i, root_page=page)

        # fetch page 1
        response = self.client.get('/admin/site-chooser/chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<p>Page 1 of 3.</p>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="2" class="icon icon-arrow-right-after">Next</a>',
            response_json['html']
        )

        # fetch page 2
        response = self.client.get('/admin/site-chooser/chooser/?p=2')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<p>Page 2 of 3.</p>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="1" class="icon icon-arrow-left">Previous</a>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="3" class="icon icon-arrow-right-after">Next</a>',
            response_json['html']
        )

    def test_search(self):
        homepage = Page.objects.get(depth=2)
        red_page = homepage.add_child(title='A red page')
        another_red_page = homepage.add_child(title='Another red page')
        green_page = homepage.add_child(title='A green page')

        response = self.client.get('/admin/page-chooser/chooser/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include a search box
        self.assertInHTML(
            '<input type="text" name="q" placeholder="Search" required id="id_q">',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">A green page</a>' % green_page.id,
            response_json['html']
        )

        response = self.client.get('/admin/page-chooser/chooser/?q=red')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include red_page and another_red_page but not green_page
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/chooser/%d/">A green page</a>' % green_page.id,
            response_json['html'],
            count=0
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


class FakeResponse:
    """
    Partial mockup of the return value of requests.get
    """
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeRequestsTestCase(TestCase):
    """
    a TestCase class that patches requests.get to forward HTTP requests to the Django test client
    """

    def setUp(self):
        def fake_requests_get(url_string, params=None):
            url = urlparse(url_string)
            assert(url.scheme == 'http')
            assert(url.netloc == 'testserver')

            path = url.path
            if params:
                path += '?' + urlencode(params)

            response = self.client.get(path)
            return FakeResponse(response.content)

        self.requests_get_patcher = patch('requests.get', new=fake_requests_get)
        self.requests_get_patcher.start()

    def tearDown(self):
        self.requests_get_patcher.stop()


class TestAPIChooseView(FakeRequestsTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        homepage = Page.objects.get(depth=2)
        red_page = homepage.add_child(title='A red page')

        response = self.client.get('/admin/api-page-chooser/chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<h1 class="icon icon-page">Choose a page</h1>',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )

    def test_pagination(self):
        homepage = Page.objects.get(depth=2)
        for i in range(0, 25):
            homepage.add_child(title='Page %d' % i)

        # fetch page 1
        response = self.client.get('/admin/api-page-chooser/chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<p>Page 1 of 3.</p>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="2" class="icon icon-arrow-right-after">Next</a>',
            response_json['html']
        )

        # fetch page 2
        response = self.client.get('/admin/api-page-chooser/chooser/?p=2')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<p>Page 2 of 3.</p>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="1" class="icon icon-arrow-left">Previous</a>',
            response_json['html']
        )
        self.assertInHTML(
            '<a href="#" data-page="3" class="icon icon-arrow-right-after">Next</a>',
            response_json['html']
        )

    def test_search(self):
        homepage = Page.objects.get(depth=2)
        red_page = homepage.add_child(title='A red page')
        another_red_page = homepage.add_child(title='Another red page')
        green_page = homepage.add_child(title='A green page')

        response = self.client.get('/admin/api-page-chooser/chooser/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include a search box
        self.assertInHTML(
            '<input type="text" name="q" placeholder="Search" required id="id_q">',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">A green page</a>' % green_page.id,
            response_json['html']
        )

        response = self.client.get('/admin/api-page-chooser/chooser/?q=red')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include red_page and another_red_page but not green_page
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/chooser/%d/">A green page</a>' % green_page.id,
            response_json['html'],
            count=0
        )


class TestAPIChosenView(FakeRequestsTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        response = self.client.get('/admin/api-page-chooser/chooser/2/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'chosen')
        self.assertEqual(
            response_json['result'],
            {"id": "2", "string": "Welcome to your new Wagtail site!", "edit_link": "/admin/pages/2/edit/"}
        )
