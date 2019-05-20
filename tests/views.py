from generic_chooser.views import DRFChooserViewSet, ModelChooserViewSet, ModelChooseView

from wagtail.core.models import Page, Site


class ChooseSiteView(ModelChooseView):
    def get_unfiltered_object_list(self):
        # enforce ordering by hostname, for consistent pagination
        return super().get_unfiltered_object_list().order_by('hostname')


class SiteChooserViewSet(ModelChooserViewSet):
    model = Site
    icon = 'site'
    page_title = "Choose a site"
    per_page = 10
    edit_item_url_name = 'wagtailsites:edit'

    choose_view_class = ChooseSiteView


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
