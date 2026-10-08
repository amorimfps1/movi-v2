from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuditViewSet, ClassGroupViewSet, CsrfView, InstructorViewSet, LeadViewSet, LoginView,
    LogoutView, MeView, ModalityViewSet, RegisterView, StudentViewSet, UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("students", StudentViewSet, basename="student")
router.register("leads", LeadViewSet, basename="lead")
router.register("modalities", ModalityViewSet, basename="modality")
router.register("instructors", InstructorViewSet, basename="instructor")
router.register("classes", ClassGroupViewSet, basename="class")
router.register("audit", AuditViewSet, basename="audit")

urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="csrf"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
