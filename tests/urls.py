from django.conf.urls import include, url

from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls

from .api import api_router


urlpatterns = [
    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^api/v2/', api_router.urls),

    url(r'', include(wagtail_urls)),
]
