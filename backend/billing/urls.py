from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, ChargeViewSet, PaymentViewSet, SummaryView, ExportView, PoliciesView

router = DefaultRouter()
router.register('enrollments',EnrollmentViewSet)
router.register('charges',ChargeViewSet)
router.register('payments',PaymentViewSet)
urlpatterns = [path('',include(router.urls)),path('reports/summary/',SummaryView.as_view()),
               path('reports/export/',ExportView.as_view()),path('policies/',PoliciesView.as_view())]
