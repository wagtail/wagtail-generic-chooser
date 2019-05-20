from django.conf.urls import include, url
from wagtail.core import hooks

from tests import views


@hooks.register('register_admin_urls')
def register_admin_urls():
    api_page_chooser_urls = [
        url(r'^chooser/$', views.ChoosePageAPIView.as_view(), name='choose'),
        url(r'^chooser/(\d+)/$', views.ChosenPageAPIView.as_view(), name='chosen'),
    ]

    return [
        url(r'^api-page-chooser/', include((api_page_chooser_urls, 'api_page_chooser'), namespace='api_page_chooser')),
    ]


@hooks.register('register_admin_viewset')
def register_site_chooser_viewset():
    return views.SiteChooserViewSet('site_chooser', url_prefix='site-chooser')


@hooks.register('register_admin_viewset')
def register_page_chooser_viewset():
    return views.PageChooserViewSet('page_chooser', url_prefix='page-chooser')
