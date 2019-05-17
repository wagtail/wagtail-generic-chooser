from generic_chooser.views import DRFChooseView, DRFChosenView, ModelChooseView, ModelChosenView

from wagtail.core.models import Page, Site


class ChooseSiteView(ModelChooseView):
    model = Site

    choose_url_name = 'site_chooser:choose'
    chosen_url_name = 'site_chooser:chosen'

    icon = 'site'
    page_title = "Choose a site"

    per_page = 10

    def get_unfiltered_object_list(self):
        # enforce ordering by hostname, for consistent pagination
        return super().get_unfiltered_object_list().order_by('hostname')


class ChosenSiteView(ModelChosenView):
    model = Site
    edit_item_url_name = 'wagtailsites:edit'


class ChoosePageView(ModelChooseView):
    model = Page

    choose_url_name = 'page_chooser:choose'
    chosen_url_name = 'page_chooser:chosen'

    icon = 'page'
    page_title = "Choose a page"


class ChosenPageView(ModelChosenView):
    model = Page
    edit_item_url_name = 'wagtailadmin_pages:edit'


class ChoosePageAPIView(DRFChooseView):
    icon = 'page'
    page_title = "Choose a page"
    choose_url_name = 'api_page_chooser:choose'
    chosen_url_name = 'api_page_chooser:chosen'

    api_base_url = 'http://testserver/api/v2/pages/'

    # enables the search box and passes search terms to the API as the 'search' query parameter
    is_searchable = True

    per_page = 10

    def get_object_string(self, item):
        # Given an object dictionary from the API response, return the text to use as the label
        return item['title']


class ChosenPageAPIView(DRFChosenView):
    edit_item_url_name = 'wagtailadmin_pages:edit'
    api_base_url = 'http://testserver/api/v2/pages/'

    def get_object_string(self, item):
        return item['title']
