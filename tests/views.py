from django import forms
from wagtail.core.models import Page, Site
from generic_chooser.views import DRFChooserMixin, DRFChooserViewSet, ModelChooserViewSet


class SiteChooserViewSet(ModelChooserViewSet):
    model = Site
    icon = 'site'
    page_title = "Choose a site"
    per_page = 10
    edit_item_url_name = 'wagtailsites:edit'
    order_by = 'hostname'
    fields = ['hostname', 'port', 'site_name', 'root_page', 'is_default_site']


class PageChooserViewSet(ModelChooserViewSet):
    model = Page
    icon = 'page'
    page_title = "Choose a page"
    edit_item_url_name = 'wagtailadmin_pages:edit'


class APIPageChooserViewSet(DRFChooserViewSet):
    icon = 'page'
    page_title = "Choose a page"
    title_field_name = 'title'
    api_base_url = 'http://testserver/api/v2/pages/'
    edit_item_url_name = 'wagtailadmin_pages:edit'

    # enables the search box and passes search terms to the API as the 'search' query parameter
    is_searchable = True

    per_page = 10


class PersonChooserMixin(DRFChooserMixin):
    def get_object_string(self, item):
        return "%s %s" % (item['first_name'], item['last_name'])


class PersonForm(forms.Form):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    job_title = forms.CharField(required=True)


class PersonChooserViewSet(DRFChooserViewSet):
    icon = 'user'
    api_base_url = 'http://testserver/person-api/'
    form_class = PersonForm
    chooser_mixin_class = PersonChooserMixin
    prefix = 'person-chooser'
