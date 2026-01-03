from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdRequestViewSet, AdViewSet

router = DefaultRouter()
router.register(r"", AdViewSet, basename="ad")                 # /api/ads/
router.register(r"requests", AdRequestViewSet, basename="ad-request")  # /api/ads/requests/

urlpatterns = [
    path("", include(router.urls)),
]
