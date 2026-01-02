from django.urls import path

from .views import (
    LoginView,
    MeView,
    RegisterView,
    SetContractorRoleView,
    SetSupportRoleView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),

    # Role assignment endpoints
    path("users/<int:pk>/role/support/", SetSupportRoleView.as_view(), name="role-set-support"),
    path("users/<int:pk>/role/contractor/", SetContractorRoleView.as_view(), name="role-set-contractor"),
]
