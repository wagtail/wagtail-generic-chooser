from generic_chooser.views import ModelChooseView, ModelChosenView

from wagtail.core.models import Site


class ChooseSiteView(ModelChooseView):
    model = Site

    choose_url_name = 'site_chooser:choose_site'
    chosen_url_name = 'site_chooser:chosen_site'

    icon = 'site'
    page_title = "Choose a site"


class ChosenSiteView(ModelChosenView):
    model = Site
    edit_item_url_name = 'wagtailsites:edit'
