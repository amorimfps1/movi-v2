from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, ChargeViewSet, PaymentViewSet, SummaryView, ExportView, PoliciesView, WaitingListViewSet, OccupancyView, FrequencyView, FrequencyPolicyView, ConversionView, AttritionView, FinancialOptionsView
from .catalog_api import FinancialCatalogViewSet

router = DefaultRouter()
router.register('enrollments',EnrollmentViewSet)
router.register('charges',ChargeViewSet)
router.register('payments',PaymentViewSet)
router.register('financial-catalogs', FinancialCatalogViewSet)
router.register('waiting-list', WaitingListViewSet)
urlpatterns = [path('',include(router.urls)),path('financial-options/',FinancialOptionsView.as_view()),path('reports/summary/',SummaryView.as_view()),path('reports/occupancy/',OccupancyView.as_view()),path('reports/frequency/',FrequencyView.as_view()),path('reports/frequency-policy/',FrequencyPolicyView.as_view()),path('reports/conversion/',ConversionView.as_view()),path('reports/attrition/',AttritionView.as_view()),
               path('reports/export/',ExportView.as_view()),path('policies/',PoliciesView.as_view())]
