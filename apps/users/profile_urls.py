from django.urls import path

from .profile_views import ContractorListView, ContractorProfileView, CustomerProfileView

urlpatterns = [
    path("contractors/", ContractorListView.as_view(), name="contractor-list"),
    path("contractors/<int:pk>/", ContractorProfileView.as_view(), name="contractor-profile"),
    path("customers/<int:pk>/", CustomerProfileView.as_view(), name="customer-profile"),
]
