from rest_framework.routers import DefaultRouter

from .views import LessonViewSet
from .trials import TrialViewSet

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lesson")
router.register("trials", TrialViewSet, basename="trial")
urlpatterns = router.urls
