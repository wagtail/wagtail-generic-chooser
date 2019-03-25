# wagtail-generic-chooser

`wagtail-generic-chooser` provides base classes for building chooser popups and form widgets for the Wagtail admin, matching the look and feel of Wagtail's built-in choosers for pages, documents, snippets and images.

It differs from existing model chooser add-ons ([Naeka/wagtailmodelchooser](https://github.com/Naeka/wagtailmodelchooser/), [neon-jungle/wagtailmodelchooser](https://github.com/neon-jungle/wagtailmodelchooser), [springload/wagtailmodelchoosers](https://github.com/springload/wagtailmodelchoosers)) in that it is designed to be fully configurable through subclassing - in particular, it can be used on data sources other than Django models, such as REST API endpoints.

It is intended that `wagtail-generic-chooser` will be expanded to cover all the functionality of Wagtail's built-in choosers, such as inline object creation forms, and will then be incorporated into Wagtail as the new base implementation of those built-in choosers - this will reduce code duplication and greatly simplify the process of building new admin apps.

## Requirements

Wagtail 2.4 or higher

## Installation

(no PyPI package available just yet)

Check out this repository and run `pip install -e .` from the root, or copy the `generic_chooser` app into your project. Then add `generic_chooser` to your project's `INSTALLED_APPS`.

## Usage

`wagtail-generic-chooser`'s functionality is split into two distinct components: chooser views (the URL endpoints that implement the modal interface for choosing an item) and chooser widgets (form elements that display the currently selected item, with a button that opens up the modal interface to choose a new one). Chooser views can be used independently of chooser widgets; they are used by rich text editors, for example.

### Chooser views (model-based)

The `generic_chooser.views` module provides abstract class-based views `ModelChooseView` and `ModelChosenView`, corresponding to the two stages of the chooser modal: displaying the listing of items, and returning the chosen item to the calling page as JSON data. These can be subclassed to provide a chooser for a given model - for example, to implement a chooser for [bakerydemo](https://github.com/wagtail/bakerydemo)'s `People` model:

    from django.contrib.admin.utils import quote
    from django.urls import reverse
    from django.utils.translation import ugettext_lazy as _

    from generic_chooser.views import ModelChooseView, ModelChosenView

    from bakerydemo.base.models import People


    class ChoosePersonView(ModelChooseView):
        model = People

        # the URL names registered in the URLconf for the 'choose' and 'chosen' views
        choose_url_name = 'person_chooser:choose_person'
        chosen_url_name = 'person_chooser:chosen_person'

        icon = 'user'  # see the Wagtail styleguide app for available icons
        page_title = _("Choose a person")
        per_page = 25  # None (the default) gives an unpaginated listing


    class ChosenPersonView(ModelChosenView):
        model = People

        def get_edit_item_url(self, item):
            # Returns a URL where the chosen item can be edited.
            # This needs to be a method because the wagtailsnippets:edit URL route requires
            # additional args alongside the item ID; if there were a route that accepted
            # just the ID, this could be set as the attribute edit_item_url_name instead.

            return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item.pk)))

These views can be defined in a URL configuration and registered through Wagtail's `register_admin_urls` hook:

    # myapp/admin_urls.py

    from django.conf.urls import url

    from myapp import views


    app_name = 'person_chooser'
    urlpatterns = [
        url(r'^chooser/$', views.ChoosePersonView.as_view(), name='choose_person'),
        url(r'^chooser/(\d+)/$', views.ChosenPersonView.as_view(), name='chosen_person'),
    ]


    # myapp/wagtail_hooks.py

    from django.conf.urls import include, url
    from wagtail.core import hooks

    from myapp import admin_urls


    @hooks.register('register_admin_urls')
    def register_admin_urls():
        return [
            url(r'^people/', include(admin_urls, namespace='person_chooser')),
        ]


### Chooser views (Django Rest Framework-based)

The `generic_chooser.views` module also provides abstract class-based views `DRFChooseView` and `DRFChosenView` for building choosers based on Django Rest Framework API endpoints. For example, an API-based chooser for Wagtail's Page model can be implemented as follows:

    from django.utils.translation import ugettext_lazy as _
    from wagtail.core.models import Page

    from generic_chooser.views import DRFChooseView, DRFChosenView


    class ChoosePageAPIView(DRFChooseView):
        icon = 'page'
        page_title = _("Choose a page")
        choose_url_name = 'page_chooser:choose_page'
        chosen_url_name = 'page_chooser:chosen_page'

        api_base_url = 'http://localhost:8000/api/v2/pages/'

        # enables the search box and passes search terms to the API as the 'search' query parameter
        is_searchable = True

        per_page = 25

        def get_object_string(self, item):
            # Given an object dictionary from the API response, return the text to use as the label
            return item['title']


    class ChosenPageAPIView(DRFChosenView):
        edit_item_url_name = 'wagtailadmin_pages:edit'
        api_base_url = 'http://localhost:8000/api/v2/pages/'

        def get_object_string(self, item):
            return item['title']

These views can be defined in a URL configuration and registered through Wagtail's `register_admin_urls` hook as above.


### Chooser views (other data sources)

See the base class implementations in `generic_chooser/views.py` - these provide numerous overrideable methods to allow adapting the chooser UI to other data sources, such as non-Django APIs.


### Chooser widgets (model-based)

The `generic_chooser.widgets` module provides an `AdminChooser` widget to be subclassed. For example, a widget for the `People` model, using the chooser views defined above, can be implemented as follows:

    from django.contrib.admin.utils import quote
    from django.urls import reverse
    from django.utils.translation import ugettext_lazy as _

    from generic_chooser.widgets import AdminChooser

    from bakerydemo.base.models import People


    class PersonChooser(AdminChooser):
        choose_one_text = _('Choose a person')
        choose_another_text = _('Choose another person')
        link_to_chosen_text = _('Edit this person')
        model = People
        choose_modal_url_name = 'person_chooser:choose_person'

        def get_edit_item_url(self, item):
            return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item.pk)))

This widget can now be used in a form:

    from myapp.widgets import PersonChooser

    class BlogPage(Page):
        author = models.ForeignKey(
            'base.People', related_name='blog_posts',
            null=True, blank=True, on_delete=models.SET_NULL
        )

        content_panels = [
            FieldPanel('author', widget=PersonChooser),
        ]


### Chooser widgets (Django Rest Framework-based)

`generic_chooser.widgets` also provides a `DRFChooser` base class for chooser widgets backed by Django Rest Framework API endpoints:

    from generic_chooser.widgets import DRFChooser

    class PageAPIChooser(DRFChooser):
        choose_one_text = _('Choose a page')
        choose_another_text = _('Choose another page')
        link_to_chosen_text = _('Edit this page')
        choose_modal_url_name = 'page_chooser:choose_page'
        edit_item_url_name = 'wagtailadmin_pages:edit'
        api_base_url = 'http://localhost:8000/api/v2/pages/'

        def get_title(self, instance):
            return instance['title']


### Chooser views (other data sources)

See the base class implementations in `generic_chooser/widgets.py`.
