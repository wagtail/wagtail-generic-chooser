from django.conf.urls import include, url
from wagtail.core import hooks

from tests import views


@hooks.register('register_admin_urls')
def register_admin_urls():
    site_chooser_urls = [
        url(r'^chooser/$', views.ChooseSiteView.as_view(), name='choose'),
        url(r'^chooser/(\d+)/$', views.ChosenSiteView.as_view(), name='chosen'),
    ]

    page_chooser_urls = [
        url(r'^chooser/$', views.ChoosePageView.as_view(), name='choose'),
        url(r'^chooser/(\d+)/$', views.ChosenPageView.as_view(), name='chosen'),
    ]

    api_page_chooser_urls = [
        url(r'^chooser/$', views.ChoosePageAPIView.as_view(), name='choose'),
        url(r'^chooser/(\d+)/$', views.ChosenPageAPIView.as_view(), name='chosen'),
    ]

    return [
        url(r'^site-chooser/', include((site_chooser_urls, 'site_chooser'), namespace='site_chooser')),
        url(r'^page-chooser/', include((page_chooser_urls, 'page_chooser'), namespace='page_chooser')),
        url(r'^api-page-chooser/', include((api_page_chooser_urls, 'api_page_chooser'), namespace='api_page_chooser')),
    ]
