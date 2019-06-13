import json
from urllib.parse import urlencode, urlparse
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.test import TestCase

from wagtail.core.models import Page, Site

from .models import Person


class TestChooseView(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        editor = User.objects.create_user(username='editor', email='editor@example.com', password='password')
        editor.groups.add(Group.objects.get(name='Editors'))

    def test_get(self):
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        response = self.client.get('/admin/site-chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<h1 class="icon icon-site">Choose a site</h1>',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/site-chooser/1/">localhost [default]</a>',
            response_json['html']
        )

    def test_pagination(self):
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        page = Page.objects.first()
        for i in range(0, 25):
            Site.objects.create(hostname='%d.example.com' % i, root_page=page)

        # fetch page 1
        response = self.client.get('/admin/site-chooser/')
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
        response = self.client.get('/admin/site-chooser/?p=2')
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
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        homepage = Page.objects.get(depth=2)
        red_page = homepage.add_child(title='A red page')
        another_red_page = homepage.add_child(title='Another red page')
        green_page = homepage.add_child(title='A green page')

        response = self.client.get('/admin/page-chooser/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include a search box
        self.assertInHTML(
            '<input type="text" name="q" placeholder="Search" required id="id_q">',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">A green page</a>' % green_page.id,
            response_json['html']
        )

        response = self.client.get('/admin/page-chooser/?q=red')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include red_page and another_red_page but not green_page
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/page-chooser/%d/">A green page</a>' % green_page.id,
            response_json['html'],
            count=0
        )

    def test_creation_form(self):
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        response = self.client.get('/admin/site-chooser/')
        self.assertEqual(response.status_code, 200)

        # Admin has create permission for sites, so should get the create form
        response_json = json.loads(response.content)
        self.assertInHTML(
            '<a href="#site-chooser-create">Create</a>',
            response_json['html']
        )
        self.assertInHTML(
            '<input type="text" name="site-chooser-create-form-hostname" maxlength="255" required id="id_site-chooser-create-form-hostname">',
            response_json['html']
        )

    def test_creation_form_requires_create_permission(self):
        self.assertTrue(
            self.client.login(username='editor', password='password')
        )

        response = self.client.get('/admin/site-chooser/')
        self.assertEqual(response.status_code, 200)

        # Editor should NOT get the create form
        response_json = json.loads(response.content)
        self.assertInHTML(
            '<a href="#site-chooser-create">Create</a>',
            response_json['html'],
            count=0
        )
        self.assertInHTML(
            '<input type="text" name="site-chooser-create-form-hostname" maxlength="255" required id="id_site-chooser-create-form-hostname">',
            response_json['html'],
            count=0
        )

        # POST should be rejected outright
        response = self.client.post('/admin/site-chooser/', {
            'site-chooser-create-form-hostname': 'foo',
            'site-chooser-create-form-port': '123',
            'site-chooser-create-form-site_name': 'foo',
            'site-chooser-create-form-root_page': Page.objects.filter(depth=2).first().pk,
        })
        self.assertEqual(response.status_code, 403)

    def test_post_invalid_creation_form(self):
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        response = self.client.post('/admin/site-chooser/', {
            'site-chooser-create-form-hostname': '',
            'site-chooser-create-form-port': '123',
            'site-chooser-create-form-site_name': 'foo',
            'site-chooser-create-form-root_page': Page.objects.filter(depth=2).first().pk,
        })
        self.assertEqual(response.status_code, 200)
        # should be returned to the chooser view (step=choose) with a validation error
        # and the Create tab active
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        self.assertInHTML(
            '<li class="active"><a href="#site-chooser-create">Create</a></li>',
            response_json['html']
        )
        self.assertInHTML(
            '<span>This field is required.</span>',
            response_json['html']
        )

    def test_post_valid_creation_form(self):
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

        response = self.client.post('/admin/site-chooser/', {
            'site-chooser-create-form-hostname': 'foo',
            'site-chooser-create-form-port': '123',
            'site-chooser-create-form-site_name': 'foo',
            'site-chooser-create-form-root_page': Page.objects.filter(depth=2).first().pk,
        })
        self.assertEqual(response.status_code, 200)

        # Site should be created
        site = Site.objects.get(hostname='foo')

        # should receive a step=chosen response
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'chosen')
        self.assertEqual(
            response_json['result'],
            {"id": str(site.id), "string": "foo", "edit_link": "/admin/sites/%d/" % site.id}
        )


class TestChosenView(TestCase):
    def setUp(self):
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        response = self.client.get('/admin/site-chooser/1/')
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
    a TestCase class that patches requests.get and requests.post to forward HTTP requests to the
    Django test client
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

        def fake_requests_post(url_string, **kwargs):
            url = urlparse(url_string)
            assert(url.scheme == 'http')
            assert(url.netloc == 'testserver')

            if 'json' not in kwargs:
                raise Exception("non-JSON posts not supported")

            response = self.client.post(
                url.path, data=json.dumps(kwargs['json']), content_type='application/json'
            )
            return FakeResponse(response.content)

        self.requests_get_patcher = patch('requests.get', new=fake_requests_get)
        self.requests_get_patcher.start()
        self.requests_post_patcher = patch('requests.post', new=fake_requests_post)
        self.requests_post_patcher.start()

    def tearDown(self):
        self.requests_get_patcher.stop()
        self.requests_post_patcher.stop()


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

        response = self.client.get('/admin/api-page-chooser/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')
        self.assertInHTML(
            '<h1 class="icon icon-page">Choose a page</h1>',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )

    def test_pagination(self):
        homepage = Page.objects.get(depth=2)
        for i in range(0, 25):
            homepage.add_child(title='Page %d' % i)

        # fetch page 1
        response = self.client.get('/admin/api-page-chooser/')
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
        response = self.client.get('/admin/api-page-chooser/?p=2')
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

        response = self.client.get('/admin/api-page-chooser/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include a search box
        self.assertInHTML(
            '<input type="text" name="q" placeholder="Search" required id="id_q">',
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">A green page</a>' % green_page.id,
            response_json['html']
        )

        response = self.client.get('/admin/api-page-chooser/?q=red')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # response should include red_page and another_red_page but not green_page
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">A red page</a>' % red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">Another red page</a>' % another_red_page.id,
            response_json['html']
        )
        self.assertInHTML(
            '<a class="item-choice" href="/admin/api-page-chooser/%d/">A green page</a>' % green_page.id,
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
        response = self.client.get('/admin/api-page-chooser/2/')
        self.assertEqual(response.status_code, 200)

        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'chosen')
        self.assertEqual(
            response_json['result'],
            {"id": "2", "string": "Welcome to your new Wagtail site!", "edit_link": "/admin/pages/2/edit/"}
        )


class TestAPICreateForm(FakeRequestsTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_superuser(username='admin', email='admin@example.com', password='password')
        self.assertTrue(
            self.client.login(username='admin', password='password')
        )

    def test_get(self):
        response = self.client.get('/admin/person-chooser/')
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        # Create form should be displayed
        response_json = json.loads(response.content)
        self.assertInHTML(
            '<a href="#person-chooser-create">Create</a>',
            response_json['html']
        )
        self.assertInHTML(
            '<input type="text" name="person-chooser-create-form-first_name" required id="id_person-chooser-create-form-first_name">',
            response_json['html']
        )

    def test_post_invalid(self):
        response = self.client.post('/admin/person-chooser/', {
            'person-chooser-create-form-first_name': 'Bob',
            'person-chooser-create-form-last_name': '',
            'person-chooser-create-form-job_title': 'Builder',
        })
        self.assertEqual(response.status_code, 200)

        # should be returned to the chooser view (step=choose) with a validation error
        # and the Create tab active
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'choose')

        self.assertInHTML(
            '<li class="active"><a href="#person-chooser-create">Create</a></li>',
            response_json['html']
        )
        self.assertInHTML(
            '<span>This field is required.</span>',
            response_json['html']
        )

    def test_post_valid(self):
        response = self.client.post('/admin/person-chooser/', {
            'person-chooser-create-form-first_name': 'Gordon',
            'person-chooser-create-form-last_name': 'Ramsay',
            'person-chooser-create-form-job_title': 'Chef',
        })
        self.assertEqual(response.status_code, 200)

        # Person should be created
        person = Person.objects.get(first_name='Gordon')

        # should receive a step=chosen response
        response_json = json.loads(response.content)
        self.assertEqual(response_json['step'], 'chosen')
        self.assertEqual(
            response_json['result'],
            {"id": str(person.id), "string": "Gordon Ramsay", "edit_link": None}
        )
