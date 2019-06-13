from wagtail.core import hooks

from tests import views


@hooks.register('register_admin_viewset')
def register_site_chooser_viewset():
    return views.SiteChooserViewSet('site_chooser', url_prefix='site-chooser')


@hooks.register('register_admin_viewset')
def register_page_chooser_viewset():
    return views.PageChooserViewSet('page_chooser', url_prefix='page-chooser')


@hooks.register('register_admin_viewset')
def register_api_page_chooser_viewset():
    return views.APIPageChooserViewSet('api_page_chooser', url_prefix='api-page-chooser')


@hooks.register('register_admin_viewset')
def register_person_chooser_viewset():
    return views.PersonChooserViewSet('person_chooser', url_prefix='person-chooser')
