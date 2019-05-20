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

The `generic_chooser.views` module provides a viewset class `ModelChooserViewSet`, which wraps two class-based views `ModelChooseView` and `ModelChosenView` along with their URL configuration. These views correspond to the two stages of the chooser modal: displaying the listing of items, and returning the chosen item to the calling page as JSON data.

In a simple case, a chooser for a given model can be implemented by subclassing `ModelChooserViewSet` and specifying the model and other configuration options as attributes on that class. More complex customisations can be made by subclassing `ModelChooseView` and `ModelChosenView` and overriding methods on them; the viewset class can then be configured to use those custom views by setting the attributes `chooser_view_class` and `chosen_view_class`. For example, to implement a chooser for [bakerydemo](https://github.com/wagtail/bakerydemo)'s `People` model:

```python
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from generic_chooser.views import ModelChooserViewSet, ModelChosenView

from bakerydemo.base.models import People


class ChosenPersonView(ModelChosenView):
    def get_edit_item_url(self, item):
        # Returns a URL where the chosen item can be edited.
        # This needs to be a method because the wagtailsnippets:edit URL route requires
        # additional args alongside the item ID; if there were a route that accepted
        # just the ID, this could be set as the attribute edit_item_url_name instead.

        return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item.pk)))


class PersonChooserViewSet(ModelChooserViewSet):
    icon = 'user'
    model = People
    page_title = _("Choose a person")
    per_page = 2

    chosen_view_class = ChosenPersonView
```

The viewset can then be registered through Wagtail's `register_admin_viewset` hook:

```python
# myapp/wagtail_hooks.py

from wagtail.core import hooks

from myapp.views import PersonChooserViewSet


@hooks.register('register_admin_viewset')
def register_person_chooser_viewset():
    return PersonChooserViewSet('person_chooser', url_prefix='person-chooser')
```

### Chooser views (Django Rest Framework-based)

The `generic_chooser.views` module also provides a viewset class `DRFChooserViewSet`, along with class-based views `DRFChooseView` and `DRFChosenView`, for building choosers based on Django Rest Framework API endpoints. For example, an API-based chooser for Wagtail's Page model can be implemented as follows:

```python
from django.utils.translation import ugettext_lazy as _

from generic_chooser.views import DRFChooserViewSet

class APIPageChooserViewSet(DRFChooserViewSet):
    icon = 'page'
    page_title = _("Choose a page")
    api_base_url = 'http://localhost:8000/api/v2/pages/'
    edit_item_url_name = 'wagtailadmin_pages:edit'
    is_searchable = True
    per_page = 5
    title_field_name = 'title'
```

This viewset can be registered through Wagtail's `register_admin_viewset` hook as above.


### Chooser views (other data sources)

See the base class implementations in `generic_chooser/views.py` - these provide numerous overrideable methods to allow adapting the chooser UI to other data sources, such as non-Django APIs.


### Chooser widgets (model-based)

The `generic_chooser.widgets` module provides an `AdminChooser` widget to be subclassed. For example, a widget for the `People` model, using the chooser views defined above, can be implemented as follows:

```python
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
    choose_modal_url_name = 'person_chooser:choose'

    def get_edit_item_url(self, item):
        return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item.pk)))
```

This widget can now be used in a form:

```python
from myapp.widgets import PersonChooser

class BlogPage(Page):
    author = models.ForeignKey(
        'base.People', related_name='blog_posts',
        null=True, blank=True, on_delete=models.SET_NULL
    )

    content_panels = [
        FieldPanel('author', widget=PersonChooser),
    ]
```

### Chooser widgets (Django Rest Framework-based)

`generic_chooser.widgets` also provides a `DRFChooser` base class for chooser widgets backed by Django Rest Framework API endpoints:

```python
from generic_chooser.widgets import DRFChooser

class PageAPIChooser(DRFChooser):
    choose_one_text = _('Choose a page')
    choose_another_text = _('Choose another page')
    link_to_chosen_text = _('Edit this page')
    choose_modal_url_name = 'page_chooser:choose'
    edit_item_url_name = 'wagtailadmin_pages:edit'
    api_base_url = 'http://localhost:8000/api/v2/pages/'

    def get_title(self, instance):
        return instance['title']
```

### Chooser widgets (other data sources)

See the base class implementations in `generic_chooser/widgets.py`.
