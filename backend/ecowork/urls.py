from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AssociationViewSet, CondominiumViewSet, ProductView, QuoteView, ResidenceViewSet
from .finance_api import ChargeViewSet, OrderViewSet, PaymentViewSet

router = DefaultRouter()
router.register("condominiums", CondominiumViewSet, basename="condominium")
router.register("condominium-associations", AssociationViewSet, basename="condominium-association")
router.register("residence-verifications", ResidenceViewSet, basename="residence-verification")
router.register("ecowork/orders", OrderViewSet, basename="ecowork-order")
router.register("ecowork/charges", ChargeViewSet, basename="ecowork-charge")
router.register("ecowork/payments", PaymentViewSet, basename="ecowork-payment")

urlpatterns = [
    path("", include(router.urls)),
    path("ecowork/products/", ProductView.as_view()),
    path("ecowork/quote/", QuoteView.as_view()),
]
