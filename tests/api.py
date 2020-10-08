from wagtail import VERSION as WAGTAIL_VERSION

if WAGTAIL_VERSION >= (2, 8):
    from wagtail.api.v2.views import PagesAPIViewSet
else:
    from wagtail.api.v2.endpoints import PagesAPIEndpoint as PagesAPIViewSet

from wagtail.api.v2.router import WagtailAPIRouter

api_router = WagtailAPIRouter('wagtailapi')

api_router.register_endpoint('pages', PagesAPIViewSet)
