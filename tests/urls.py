from django.conf.urls import include, url
from rest_framework import routers, serializers, viewsets
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls

from .api import api_router as wagtail_api_router
from .models import Person


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
    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^api/v2/', wagtail_api_router.urls),

    # Wire up our API using automatic URL routing.
    url(r'^', include(router.urls)),

    url(r'', include(wagtail_urls)),
]
