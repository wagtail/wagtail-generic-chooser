import django
from django.conf.urls import include
from rest_framework import routers, serializers, viewsets
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls

from .api import api_router as wagtail_api_router
from .models import Person

if django.VERSION >= (3, 1):
    from django.urls import re_path
else:
    from django.conf.urls import url as re_path


class PersonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Person
        fields = ('id', 'first_name', 'last_name', 'job_title')


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer

# Register a writeable API for the Person model at /person-api,
# separate from the Wagtail API
router = routers.DefaultRouter()
router.register(r'person-api', PersonViewSet)

urlpatterns = [
    re_path(r'^admin/', include(wagtailadmin_urls)),
    re_path(r'^api/v2/', wagtail_api_router.urls),

    # Wire up our API using automatic URL routing.
    re_path(r'^', include(router.urls)),

    re_path(r'', include(wagtail_urls)),
]
