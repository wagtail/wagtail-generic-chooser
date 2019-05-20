from generic_chooser.views import DRFChooserViewSet, ModelChooserViewSet

from wagtail.core.models import Page, Site


class SiteChooserViewSet(ModelChooserViewSet):
    model = Site
    icon = 'site'
    page_title = "Choose a site"
    per_page = 10
    edit_item_url_name = 'wagtailsites:edit'
    order_by = 'hostname'


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
