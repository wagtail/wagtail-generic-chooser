# wagtail-generic-chooser

`wagtail-generic-chooser` provides base classes for building chooser popups and form widgets for the Wagtail admin, matching the look and feel of Wagtail's built-in choosers for pages, documents, snippets and images.

It differs from existing model chooser add-ons ([Naeka/wagtailmodelchooser](https://github.com/Naeka/wagtailmodelchooser/), [neon-jungle/wagtailmodelchooser](https://github.com/neon-jungle/wagtailmodelchooser), [springload/wagtailmodelchoosers](https://github.com/springload/wagtailmodelchoosers)) in that it is designed to be fully configurable through subclassing - in particular, it can be used on data sources other than Django models, such as REST API endpoints.

It is intended that `wagtail-generic-chooser` will be expanded to cover all the functionality of Wagtail's built-in choosers, such as inline object creation forms, and will then be incorporated into Wagtail as the new base implementation of those built-in choosers - this will reduce code duplication and greatly simplify the process of building new admin apps.

## Requirements

Wagtail 2.4 or higher

## Installation

Run: `pip install wagtail-generic-chooser`

Then add `generic_chooser` to your project's `INSTALLED_APPS`.

## Usage

`wagtail-generic-chooser`'s functionality is split into two distinct components: chooser views (the URL endpoints that implement the modal interface for choosing an item) and chooser widgets (form elements that display the currently selected item, with a button that opens up the modal interface to choose a new one). Chooser views can be used independently of chooser widgets; they are used by rich text editors, for example.

### Chooser views (model-based)

The `generic_chooser.views` module provides a viewset class `ModelChooserViewSet`, which can be used to build a modal interface for choosing a Django model instance. Viewsets are Wagtail's way of grouping several related views into a single unit along with their URL configuration; this makes it possible to configure the overall behaviour of a workflow within Wagtail without having to know how that workflow breaks down into individual views.

At minimum, a chooser can be implemented by subclassing `ModelChooserViewSet` and setting a `model` attribute. Other attributes can be specified to customise the look and feel of the chooser, such as the heading icon and number of items per page. For example, to implement a chooser for [bakerydemo](https://github.com/wagtail/bakerydemo)'s `People` model:

```python
# myapp/views.py

from django.utils.translation import gettext_lazy as _

from generic_chooser.views import ModelChooserViewSet

from bakerydemo.base.models import People


class PersonChooserViewSet(ModelChooserViewSet):
    icon = 'user'
    model = People
    page_title = _("Choose a person")
    per_page = 10
    order_by = 'first_name'
    fields = ['first_name', 'last_name', 'job_title']
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

### Chooser views (Django REST Framework-based)

The `generic_chooser.views` module also provides a viewset class `DRFChooserViewSet` for building choosers based on Django REST Framework API endpoints. Subclasses need to specify an `api_base_url` attribute. For example, an API-based chooser for Wagtail's Page model can be implemented as follows:

```python
from django.utils.translation import gettext_lazy as _

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


### Creating objects within the chooser

Setting a `form_class` attribute on the viewset will add a 'Create' tab containing that form, allowing users to create new objects within the chooser.

For a model-based chooser, this form class should be a `ModelForm`, and the form will be shown for all users with 'create' permission on the corresponding model. As a shortcut, a `fields` list can be specified in place of `form_class`.

```python
class PersonChooserViewSet(ModelChooserViewSet):
    # ...
    fields = ['first_name', 'last_name', 'job_title']
```

For a Django REST Framework-based chooser, `form_class` must be defined explicitly (i.e. the `fields` shortcut is not available) and the object will be created by sending a POST request to the API endpoint consisting of the form's `cleaned_data` in JSON format. An API-based equivalent of `PersonChooserViewSet` would be:

```python
from django import forms
from django.contrib.admin.utils import quote
from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from generic_chooser.views import DRFChooserMixin, DRFChooserViewSet


class PersonChooserMixin(DRFChooserMixin):
    def get_edit_item_url(self, item):
        return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item['id'])))

    def get_object_string(self, item):
        return "%s %s" % (item['first_name'], item['last_name'])


class PersonForm(forms.Form):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    job_title = forms.CharField(required=True)


class PersonChooserViewSet(DRFChooserViewSet):
    icon = 'user'
    api_base_url = 'http://localhost:8000/people-api/'
    page_title = _("Choose a person")
    per_page = 10
    form_class = PersonForm

    chooser_mixin_class = PersonChooserMixin
    prefix = 'person-chooser'
```

This example requires the API to be configured with write access enabled, which can be done with a setting such as the following:

```python
REST_FRAMEWORK = {
    # Allow unauthenticated write access to the API. You probably don't want to this in production!
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ],

    'DEFAULT_PAGINATION_CLASS': 'wagtail.api.v2.pagination.WagtailPagination',
    'PAGE_SIZE': 100,
}
```

### Customising chooser views

If the configuration options on `ModelChooserViewSet` and `DRFChooserViewSet` are not sufficient, it's possible to fully customise the chooser behaviour by overriding methods. To do this you'll need to work with the individual class-based views and mixins that make up the viewsets - this is best done by referring to the base implementations in `generic_chooser/views.py`. The classes are:

* `ChooserMixin` - an abstract class providing helper methods shared by all views. These deal with data retrieval, and providing string and ID representations and URLs corresponding to the objects being chosen. To implement a chooser for a different data source besides Django models and Django REST Framework, you'll need to subclass this.
* `ModelChooserMixin` - implementation of `ChooserMixin` using a Django model as the data source.
* `DRFChooserMixin` - implementation of `ChooserMixin` using a Django REST Framework endpoint as the data source.
* `ChooserListingTabMixin` - handles the behaviour and rendering of the results listing tab, including pagination and searching.
* `ChooserCreateTabMixin` - handles the behaviour and rendering of the 'create' form tab
* `ModelChooserCreateTabMixin` - version of `ChooserCreateTabMixin` for model forms
* `DRFChooserCreateTabMixin` - version of `ChooserCreateTabMixin` for Django REST Framework
* `BaseChooseView` - abstract class-based view handling the main chooser UI. Subclasses should extend this and include the mixins `ChooserMixin`, `ChooserListingTabMixin` and `ChooserCreateTabMixin` (or suitable subclasses of them).
* `ModelChooseView`, `DRFChooseView` - model-based and DRF-based subclasses of `BaseChooseView`
* `BaseChosenView` - class-based view that returns the chosen object as a JSON response
* `ModelChosenView`, `DRFChosenView` - model-based and DRF-based subclasses of `BaseChosenView`
* `ChooserViewSet` - common base implementation of `ModelChooserViewSet` and `DRFChooserViewSet`

For example, we may want to extend the PersonChooserViewSet above to return an 'edit this person' URL as part of its JSON response, pointing to the `'wagtailsnippets:edit'` view. Including an 'edit' URL in the response would normally be achieved by setting the `edit_item_url_name` attribute on the viewset to a suitable URL route name, but `'wagtailsnippets:edit'` won't work here; this is because `edit_item_url_name` expects it to take a single URL parameter, the ID, whereas the snippet edit view also needs to be passed the model's app name and model name. Instead, we can do this by overriding the `get_edit_item_url` method on `ModelChooserMixin`:

```python
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from generic_chooser.views import ModelChooserMixin, ModelChooserViewSet

from bakerydemo.base.models import People


class PersonChooserMixin(ModelChooserMixin):
    def get_edit_item_url(self, item):
        return reverse('wagtailsnippets:edit', args=('base', 'people', quote(item.pk)))


class PersonChooserViewSet(ModelChooserViewSet):
    icon = 'user'
    model = People
    page_title = _("Choose a person")
    per_page = 10
    order_by = 'first_name'

    chooser_mixin_class = PersonChooserMixin
```

### Chooser widgets (model-based)

The `generic_chooser.widgets` module provides an `AdminChooser` widget to be subclassed. For example, a widget for the `People` model, using the chooser views defined above, can be implemented as follows:

```python
from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

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


### StreamField blocks

A chooser widget as defined above can be wrapped in Wagtail's `ChooserBlock` class to be used inside a StreamField. As of Wagtail 2.13, the block definition should be as follows:

```python
from wagtail.core.blocks import ChooserBlock


class PersonChooserBlock(ChooserBlock):
    @cached_property
    def target_model(self):
        from .models import People
        return People

    @cached_property
    def widget(self):
        from .widgets import PersonChooser
        return PersonChooser()

    def get_form_state(self, value):
        return self.widget.get_value_data(value)
```


### Limiting choices via linked fields

wagtail-generic-chooser provides a mechanism for limiting the options displayed in the chooser according to another input field on the calling page. For example, suppose the person model has a country field - we can then set up a page model with a country dropdown and a person chooser, where an editor first selects a country from the dropdown and then opens the person chooser to be presented with a list of people from that country.

First, we customise the chooser view to expose a `country` URL parameter; to do this, we define a custom `chooser_mixin_class` for the viewset to use, and override its `get_unfiltered_object_list` method to filter by the `country` parameter.


```python
from generic_chooser.views import ModelChooserMixin, ModelChooserViewSet


class PersonChooserMixin(ModelChooserMixin):
    preserve_url_parameters = ['country',]  # preserve this URL parameter on pagination / search

    def get_unfiltered_object_list(self):
        objects = super().get_unfiltered_object_list()
        country = self.request.GET.get('country')
        if country:
            objects = objects.filter(country_id=country)
        return objects


class PersonChooserViewSet(ModelChooserViewSet):
    model = Person
    chooser_mixin_class = PersonChooserMixin
```


We now set up our chooser widget to inherit from `LinkedFieldMixin`:

```python
from generic_chooser.widgets import AdminChooser, LinkedFieldMixin

class PersonChooser(LinkedFieldMixin, AdminChooser):
    icon = 'user'
    model = People
    page_title = _("Choose a person")
```

This mixin allows us to pass a `linked_fields` dict when constructing a `PersonChooser` instance, specifying the URL parameters to pass to the chooser along with a CSS selector to indicate which field each one should be taken from.

```python
class BlogPage(Page):
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)

    content_panels = Page.content_panels + [
        FieldPanel('country'),
        FieldPanel('person', widget=PersonChooser(linked_fields={
            # pass the country selected in the id_country input to the person chooser
            # as a URL parameter `country`
            'country': '#id_country',
        })),
    ]
```

A number of other lookup mechanisms are available:
```python
PersonChooser(linked_fields={
    'country': {'selector': '#id_country'}  # equivalent to 'country': '#id_country'
})

# Look up by ID
PersonChooser(linked_fields={
    'country': {'id': 'id_country'}
})

# Regexp match, for use in StreamFields and InlinePanels where IDs are dynamic:
# 1) Match the ID of the current widget's (the PersonChooser) against the regexp
#      '^id_blog_person_relationship-\d+-'
# 2) Append 'country' to the matched substring
# 3) Retrieve the input field with that ID
PersonChooser(linked_fields={
    'country': {'match': r'^id_blog_person_relationship-\d+-', 'append': 'country'},
})
```
