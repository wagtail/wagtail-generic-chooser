from django.conf.urls import include, url
from wagtail.core import hooks

from tests import views


@hooks.register('register_admin_urls')
def register_admin_urls():
    site_chooser_urls = [
        url(r'^chooser/$', views.ChooseSiteView.as_view(), name='choose_site'),
        url(r'^chooser/(\d+)/$', views.ChosenSiteView.as_view(), name='chosen_site'),
    ]

    return [
        url(r'^site-chooser/', include((site_chooser_urls, 'site_chooser'), namespace='site_chooser')),
    ]
