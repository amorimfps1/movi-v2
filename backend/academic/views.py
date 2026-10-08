from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import Instructor
from core.permissions import IsInternal, is_administrative

from .models import Lesson
from .serializers import AttendanceHistorySerializer, AttendanceSubmissionSerializer, DecisionResponseSerializer, LessonSerializer, RosterSerializer
from .services import attendance_history, roster, save_lesson, submit_attendance


class LessonViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = LessonSerializer
    permission_classes = [IsInternal]
    filterset_fields = ["class_group", "date", "status", "assigned_instructor"]
    search_fields = ["class_group__name", "class_group__modality__name"]
    ordering_fields = ["date", "id", "class_group__name"]
    ordering = ["-date", "-id"]

    def get_queryset(self):
        queryset = Lesson.objects.select_related("class_group__instructor", "assigned_instructor")
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        user = self.request.user
        if is_administrative(user):
            return queryset
        if "instructor" not in user.roles:
            return queryset.none()
        instructor_id = Instructor.objects.filter(user_id=user.pk, active=True).values_list("pk", flat=True).first()
        if not instructor_id:
            return queryset.none()
        return queryset.filter(Q(class_group__instructor_id=instructor_id) | Q(assigned_instructor_id=instructor_id))

    def perform_create(self, serializer):
        serializer.instance = save_lesson(self.request.user.pk, serializer.validated_data)

    def perform_update(self, serializer):
        if not is_administrative(self.request.user):
            raise PermissionDenied("Somente Secretaria e Coordenação podem alterar aulas e atribuições.")
        serializer.instance = save_lesson(self.request.user.pk, serializer.validated_data, serializer.instance.pk)

    @extend_schema(responses={200: RosterSerializer, 409: DecisionResponseSerializer})
    @action(detail=True, methods=["get"])
    def roster(self, request, pk=None):
        lesson = self.get_object()
        return Response(roster(request.user.pk, lesson.pk))

    @extend_schema(methods=["GET"], responses={200: AttendanceHistorySerializer, 409: DecisionResponseSerializer})
    @extend_schema(methods=["POST"], request=AttendanceSubmissionSerializer,
                   responses={200: LessonSerializer, 409: DecisionResponseSerializer})
    @action(detail=True, methods=["get", "post"])
    def attendance(self, request, pk=None):
        lesson = self.get_object()
        if request.method == "GET":
            return Response(AttendanceHistorySerializer(attendance_history(request.user.pk, lesson.pk)).data)
        serializer = AttendanceSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        completed = submit_attendance(request.user.pk, lesson.pk, **serializer.validated_data)
        return Response(LessonSerializer(completed).data)
