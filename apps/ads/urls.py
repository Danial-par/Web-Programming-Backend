from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdViewSet

router = DefaultRouter()
router.register(r"", AdViewSet, basename="ad")  # /api/ads/

urlpatterns = [
    path("", include(router.urls)),
]
