from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, ChargeViewSet, PaymentViewSet, PaymentRefundViewSet, SummaryView, ExportView, PoliciesView, WaitingListViewSet, OccupancyView, FrequencyView, FrequencyPolicyView, ConversionView, AttritionView, FinancialOptionsView
from .catalog_api import FinancialCatalogViewSet
from .payout_api import PayoutAgreementViewSet
from .benefit_api import BenefitViewSet

router = DefaultRouter()
router.register('enrollments',EnrollmentViewSet)
router.register('charges',ChargeViewSet)
router.register('payments',PaymentViewSet)
router.register('payment-refunds',PaymentRefundViewSet)
router.register('financial-catalogs', FinancialCatalogViewSet)
router.register('waiting-list', WaitingListViewSet)
router.register('payout-agreements', PayoutAgreementViewSet)
router.register('benefits', BenefitViewSet)
urlpatterns = [path('',include(router.urls)),path('financial-options/',FinancialOptionsView.as_view()),path('reports/summary/',SummaryView.as_view()),path('reports/occupancy/',OccupancyView.as_view()),path('reports/frequency/',FrequencyView.as_view()),path('reports/frequency-policy/',FrequencyPolicyView.as_view()),path('reports/conversion/',ConversionView.as_view()),path('reports/attrition/',AttritionView.as_view()),
               path('reports/export/',ExportView.as_view()),path('policies/',PoliciesView.as_view())]
