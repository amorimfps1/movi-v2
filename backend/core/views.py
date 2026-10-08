from django.apps import apps
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .audit import record
from .models import AuditEvent, ClassGroup, Instructor, Lead, Modality, Student, User
from .permissions import IsAdministrative, IsInternal, is_administrative, is_internal
from .serializers import (
    AccessRoleSerializer, AccessRolesSerializer, AuditSerializer, ClassGroupSerializer,
    ConvertSerializer, InstructorSerializer, LeadSerializer, LoginSerializer,
    ModalitySerializer, ReasonSerializer, RegisterSerializer, StudentSerializer, UserSerializer,
)
from .services import change_access, convert_lead, lock_admin, lock_student_identities


class StandardPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ListConfiguration:
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=inline_serializer("CsrfToken", {"csrfToken": serializers.CharField()}))
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
                record(None, "access.request", user)
        except IntegrityError:
            raise ValidationError({"email": "Este e-mail já possui uma solicitação."})
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        with transaction.atomic():
            candidate = User.objects.select_for_update().filter(email__iexact=email).first()
            # Dummy password hashing mitigates account existence timing differences.
            if candidate is None:
                User().set_password(serializer.validated_data["password"])
                return Response({"detail": "E-mail ou senha inválidos."}, status=400)
            user = authenticate(request, username=candidate.username, password=serializer.validated_data["password"])
            if user is None:
                return Response({"detail": "E-mail ou senha inválidos."}, status=400)
            if not is_internal(candidate):
                return Response({"detail": "Sua conta ainda não possui autorização interna.", "access_status": candidate.access_status, "roles": candidate.roles}, status=403)
            login(request, user)
            record(user, "session.login", user)
            return Response(UserSerializer(candidate).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=inline_serializer("LogoutResult", {"detail": serializers.CharField()}))
    def post(self, request):
        logout(request)
        return Response({"detail": "Sessão encerrada."})


class MeView(APIView):
    # Account status is public to its authenticated holder, including after revocation.
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        current = User.objects.get(pk=request.user.pk)
        return Response(UserSerializer(current).data)


class UserViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_fields = ["access_status"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["id", "email", "date_joined", "access_status"]

    def _change(self, request, operation, serializer_class):
        self.get_object()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = change_access(request.user, int(self.kwargs["pk"]), operation, serializer.validated_data)
        return Response(UserSerializer(target).data)

    @extend_schema(request=AccessRolesSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._change(request, "approve", AccessRolesSerializer)

    @extend_schema(request=ReasonSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._change(request, "reject", ReasonSerializer)

    @extend_schema(request=AccessRoleSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"], url_path="add-role")
    def add_role(self, request, pk=None):
        return self._change(request, "add_role", AccessRoleSerializer)

    @extend_schema(request=AccessRoleSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"], url_path="remove-role")
    def remove_role(self, request, pk=None):
        return self._change(request, "remove_role", AccessRoleSerializer)


class AdministrativeModelViewSet(ListConfiguration, viewsets.ModelViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def _lock_dependencies(self):
        if self.queryset.model is Student:
            lock_student_identities()
            if self.kwargs.get("pk") and apps.is_installed("billing"):
                enrollment_model = apps.get_model("billing", "Enrollment")
                group_ids = enrollment_model.objects.filter(student_id=self.kwargs["pk"]).values_list("class_group_id", flat=True)
                list(ClassGroup.objects.select_for_update().filter(pk__in=group_ids).order_by("pk"))
        if self.queryset.model is Instructor and self.kwargs.get("pk"):
            # Same ordering as attendance: User, ClassGroup, then dependent rows.
            list(ClassGroup.objects.select_for_update().filter(instructor_id=self.kwargs["pk"]).order_by("pk"))

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        lock_admin(request.user)
        self._lock_dependencies()
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        lock_admin(request.user)
        self._lock_dependencies()
        # get_object uses this locked queryset throughout serializer validation/save.
        # Restrict PostgreSQL locks to this table; select_related must not silently
        # acquire Instructor/Modality locks out of the documented domain order.
        self.queryset = self.queryset.select_for_update(of=("self",))
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        record(self.request.user, f"{instance._meta.model_name}.create", instance)

    def perform_update(self, serializer):
        before = dict(self.get_serializer(serializer.instance).data)
        instance = serializer.save()
        record(self.request.user, f"{instance._meta.model_name}.update", instance, metadata={"before": before, "after": dict(self.get_serializer(instance).data)})


class StudentViewSet(AdministrativeModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filterset_fields = ["archived"]
    search_fields = ["name", "cpf", "email", "phone"]
    ordering_fields = ["id", "name", "created_at"]


class LeadViewSet(AdministrativeModelViewSet):
    queryset = Lead.objects.prefetch_related("interests").all()
    serializer_class = LeadSerializer
    filterset_fields = ["status", "source", "interests"]
    search_fields = ["name", "cpf", "email", "phone"]
    ordering_fields = ["id", "name", "created_at", "status"]

    @extend_schema(request=ConvertSerializer, responses=LeadSerializer)
    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        self.get_object()
        serializer = ConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead, created = convert_lead(request.user, int(pk), serializer.validated_data)
        return Response(LeadSerializer(lead).data)


class ModalityViewSet(AdministrativeModelViewSet):
    queryset = Modality.objects.all()
    serializer_class = ModalitySerializer
    filterset_fields = ["active", "area"]
    search_fields = ["name", "area"]
    ordering_fields = ["id", "name", "default_price"]


class InstructorViewSet(AdministrativeModelViewSet):
    queryset = Instructor.objects.prefetch_related("specialties").all()
    serializer_class = InstructorSerializer
    filterset_fields = ["active", "specialties"]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["id", "name"]


class ClassGroupViewSet(AdministrativeModelViewSet):
    queryset = ClassGroup.objects.select_related("modality", "instructor").all()
    serializer_class = ClassGroupSerializer
    filterset_fields = ["active", "modality", "instructor", "allows_trial", "room"]
    search_fields = ["name", "room", "modality__name", "instructor__name"]
    ordering_fields = ["id", "name", "start_time", "capacity"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [IsInternal()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return queryset.none()
        if is_administrative(self.request.user):
            return queryset
        if "instructor" in self.request.user.roles:
            return queryset.filter(instructor__user=self.request.user, instructor__active=True)
        raise PermissionDenied("Seu perfil não permite consultar turmas.")


class AuditViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.select_related("actor").all()
    serializer_class = AuditSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_fields = ["actor", "action", "target_type", "target_id"]
    search_fields = ["action", "reason", "target_type", "target_id"]
    ordering_fields = ["created_at", "id"]
