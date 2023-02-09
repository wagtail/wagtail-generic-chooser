from wagtail.models import Site
from generic_chooser.widgets import AdminChooser


class SiteChooser(AdminChooser):
    model = Site
    icon = "site"
    choose_one_text = "Choose a site"
    choose_another_text = "Choose another site"
    link_to_chosen_text = "Edit this site"
    edit_item_url_name = "wagtailsites:edit"
