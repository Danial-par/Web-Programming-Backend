from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # OpenAPI schema + UIs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API routes (split per app)
    path("api/auth/", include("apps.users.urls")),
    path("api/ads/", include("apps.ads.urls")),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/tickets/", include("apps.tickets.urls")),
]
