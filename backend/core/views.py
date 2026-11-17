from django.apps import apps
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import CharField, OuterRef, Subquery
from django.db.models.functions import Cast, Coalesce
from django.utils import timezone
from calendar import monthrange
from datetime import date
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from config.pagination import StandardPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .audit import record
from .filters import PersonFilter, with_person_links
from .models import AuditEvent, ClassGroup, ContactPreference, Instructor, Lead, Modality, OperationLock, Person, User
from .permissions import IsAdministrative, IsCoordinator, IsInternal, is_administrative, is_internal
from .serializers import (
    AccessRoleSerializer, AccessRolesSerializer, AuditSerializer, ClassGroupSerializer,
    ConvertSerializer, InstructorSerializer, LeadSerializer, CommercialLeadSerializer, ContactPreferenceSerializer, LoginSerializer,
    ModalitySerializer, ReasonSerializer, RegisterSerializer, PersonSerializer, UserSerializer,
)
from .services import change_access, convert_lead, lock_admin, lock_student_identities


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
    permission_classes = [IsInternal, IsCoordinator]
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

    @extend_schema(request=ReasonSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._change(request, "reopen", ReasonSerializer)

    @extend_schema(request=ReasonSerializer, responses=UserSerializer)
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        return self._change(request, "deactivate", ReasonSerializer)

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
        if self.queryset.model in (ClassGroup, Instructor):
            OperationLock.objects.get_or_create(key='class-schedule')
            OperationLock.objects.select_for_update().get(key='class-schedule')
        if self.queryset.model is Person:
            lock_student_identities()
            if self.kwargs.get("pk") and apps.is_installed("billing"):
                enrollment_model = apps.get_model("billing", "Enrollment")
                waiting_model = apps.get_model("billing", "WaitingListEntry")
                group_ids = set(enrollment_model.objects.filter(student_id=self.kwargs["pk"]).values_list("class_group_id", flat=True))
                group_ids.update(waiting_model.objects.filter(person_id=self.kwargs["pk"], status='waiting').values_list('class_group_id', flat=True))
                if apps.is_installed('academic'):
                    trial_model = apps.get_model('academic', 'TrialParticipation')
                    group_ids.update(trial_model.objects.filter(person_id=self.kwargs['pk'], status='scheduled').values_list('lesson__class_group_id', flat=True))
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
        name = "student" if instance._meta.model_name == "person" else instance._meta.model_name
        record(self.request.user, f"{name}.create", instance)

    def perform_update(self, serializer):
        before = dict(self.get_serializer(serializer.instance).data)
        instance = serializer.save()
        if instance._meta.model_name == 'person' and instance.archived and not before.get('archived'):
            waiting_model = apps.get_model('billing', 'WaitingListEntry')
            for entry in waiting_model.objects.select_for_update().filter(person=instance, status='waiting'):
                entry.status = 'cancelled'
                entry.save(update_fields=['status'])
                record(self.request.user, 'waiting_list.cancelled', entry, reason='Pessoa arquivada.')
            if apps.is_installed('academic'):
                trial_model = apps.get_model('academic', 'TrialParticipation')
                for trial in trial_model.objects.select_for_update().filter(person=instance, status='scheduled'):
                    trial.status = 'cancelled'
                    trial.save(update_fields=['status'])
                    record(self.request.user, 'trial.cancelled', trial, reason='Pessoa arquivada.')
        name = "student" if instance._meta.model_name == "person" else instance._meta.model_name
        record(self.request.user, f"{name}.update", instance, metadata={"before": before, "after": dict(self.get_serializer(instance).data)})


class PersonViewSet(AdministrativeModelViewSet):
    queryset = with_person_links(Person.objects.all())
    serializer_class = PersonSerializer
    filterset_class = PersonFilter
    search_fields = ["name", "cpf", "email", "phone"]
    ordering_fields = ["id", "name", "created_at"]


class LeadViewSet(AdministrativeModelViewSet):
    queryset = Lead.objects.prefetch_related("interests", "lead_trials__lesson__class_group").all()
    serializer_class = LeadSerializer
    filterset_fields = ["status", "source", "interests", "student"]
    search_fields = ["name", "cpf", "email", "phone"]
    ordering_fields = ["id", "name", "created_at", "status"]

    def get_permissions(self):
        if self.action in {'list', 'retrieve'}:
            return [IsInternal()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        trial_status = self.request.query_params.get('trial_status')
        if trial_status:
            trial_model = apps.get_model('academic', 'TrialParticipation')
            latest = trial_model.objects.filter(lead_id=OuterRef('pk')).order_by('-created_at', '-pk').values('status')[:1]
            queryset = queryset.annotate(latest_trial_status=Subquery(latest))
            if trial_status == 'none':
                queryset = queryset.filter(latest_trial_status__isnull=True)
            elif trial_status in {'scheduled', 'completed', 'cancelled'}:
                queryset = queryset.filter(latest_trial_status=trial_status)
            else:
                raise ValidationError({'trial_status': 'Situação de experimental inválida.'})
        if is_administrative(self.request.user):
            return queryset
        if 'communication' in self.request.user.roles:
            if 'student' in self.request.query_params:
                raise PermissionDenied('Seu perfil não permite filtrar leads por pessoa vinculada.')
            self.search_fields = ['name']
            return queryset.prefetch_related('contact_preferences')
        raise PermissionDenied('Seu perfil não permite consultar leads.')

    def perform_create(self, serializer):
        trial_data = serializer.validated_data.pop('trial', None)
        if not trial_data:
            return super().perform_create(serializer)
        from academic.serializers import TrialSerializer
        from academic.trials import TrialViewSet
        lock_student_identities()
        cpf = serializer.validated_data.get('cpf', '')
        email = serializer.validated_data.get('email', '').strip()
        from django.db.models import Q
        criteria = Q(pk__in=[])
        if cpf:
            criteria |= Q(cpf=cpf)
        if email:
            criteria |= Q(email__iexact=email)
        candidate_ids = set(Person.objects.filter(criteria).values_list('pk', flat=True))
        person_id = trial_data.get('person')
        if person_id:
            person = Person.objects.select_for_update().filter(pk=person_id, archived=False).first()
            if not person or (candidate_ids and candidate_ids != {person_id}):
                raise ValidationError({'trial': 'Confira a pessoa selecionada e os cadastros com o mesmo CPF ou e-mail.'})
            if cpf and person.cpf and cpf != person.cpf:
                raise ValidationError({'trial': 'O CPF do lead difere do cadastro selecionado.'})
            if person.birth_date and person.birth_date != trial_data['birth_date']:
                raise ValidationError({'trial': 'A data de nascimento difere do cadastro selecionado.'})
            if not person.birth_date:
                person.birth_date = trial_data['birth_date']
                person.save(update_fields=['birth_date'])
                record(self.request.user, 'person.birth_date.updated', person, metadata={'source': 'lead_trial'})
        else:
            if candidate_ids:
                raise ValidationError({'trial': 'Já existe pessoa com este CPF ou e-mail. Selecione o cadastro existente.'})
            person = Person.objects.create(name=serializer.validated_data['name'], cpf=cpf, email=email,
                phone=serializer.validated_data.get('phone', ''), birth_date=trial_data['birth_date'])
            record(self.request.user, 'student.create', person, metadata={'source': 'lead_trial'})
        trial = TrialSerializer(data={'person': person.pk, 'lesson': trial_data['lesson'],
            'guardian_authorization': trial_data['guardian_authorization']})
        trial.is_valid(raise_exception=True)
        lead = serializer.save()
        record(self.request.user, 'lead.create', lead)
        trial_view = TrialViewSet()
        trial_view.request = self.request
        trial_view.perform_create(trial, lead=lead)

    def perform_update(self, serializer):
        if 'trial' in serializer.validated_data:
            raise ValidationError({'trial': 'O agendamento integrado está disponível apenas na criação do lead.'})
        return super().perform_update(serializer)

    def get_serializer_class(self):
        if self.action in {'list', 'retrieve'} and not is_administrative(self.request.user):
            return CommercialLeadSerializer
        return super().get_serializer_class()

    @extend_schema(responses=inline_serializer('LeadRetentionReviewList', {'results': serializers.ListField(child=serializers.DictField())}))
    @action(detail=False, methods=['get'], url_path='retention-review')
    def retention_review(self, request):
        today = timezone.localdate()
        events = AuditEvent.objects.filter(target_type='core.lead', target_id=Cast(OuterRef('pk'), output_field=CharField()),
            action__in=['lead.create', 'lead.update', 'lead.convert', 'lead.retention.review']).order_by('-created_at', '-id')
        leads = Lead.objects.annotate(last_activity=Coalesce(Subquery(events.values('created_at')[:1]), 'created_at')).order_by('last_activity', 'id')
        results = []
        for lead in leads:
            last = timezone.localtime(lead.last_activity).date()
            due = date(last.year + 1, last.month, min(last.day, monthrange(last.year + 1, last.month)[1]))
            if due <= today:
                results.append({'id': lead.pk, 'name': lead.name, 'status': lead.status, 'last_activity': last.isoformat(), 'review_due': due.isoformat()})
        return Response({'results': results})

    @extend_schema(request=ReasonSerializer, responses=inline_serializer('LeadRetentionReviewed', {'detail': serializers.CharField()}))
    @action(detail=True, methods=['post'], url_path='review-retention')
    @transaction.atomic
    def review_retention(self, request, pk=None):
        self.get_object()
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor = lock_admin(request.user)
        lead = Lead.objects.select_for_update().get(pk=pk)
        record(actor, 'lead.retention.review', lead, reason=data.validated_data['reason'])
        return Response({'detail': 'Revisão registrada; o histórico foi preservado.'})

    @extend_schema(request=ConvertSerializer, responses=LeadSerializer)
    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        self.get_object()
        serializer = ConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead, created = convert_lead(request.user, int(pk), serializer.validated_data)
        return Response(LeadSerializer(lead).data)


class ContactPreferenceViewSet(ListConfiguration, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal]
    serializer_class = ContactPreferenceSerializer
    queryset = ContactPreference.objects.all()
    filterset_fields = ['person', 'lead', 'channel', 'purpose']
    ordering_fields = ['created_at', 'id']

    def get_permissions(self):
        return [IsInternal(), IsAdministrative()] if self.action == 'create' else [IsInternal()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        if is_administrative(self.request.user):
            return queryset
        if 'communication' in self.request.user.roles:
            return queryset.filter(lead__isnull=False, purpose='commercial')
        raise PermissionDenied('Seu perfil não permite consultar preferências de contato.')

    @transaction.atomic
    def perform_create(self, serializer):
        actor = lock_admin(self.request.user)
        lock_student_identities()
        data = serializer.validated_data
        if data.get('person'):
            subject = Person.objects.select_for_update().get(pk=data['person'].pk)
            if subject.archived:
                raise ValidationError('Não é possível registrar preferência para pessoa arquivada.')
        else:
            subject = Lead.objects.select_for_update().get(pk=data['lead'].pk)
        preference = serializer.save(actor=actor)
        record(actor, 'contact.preference', preference, metadata={'subject_type': subject._meta.model_name,
            'subject_id': subject.pk, 'channel': preference.channel, 'purpose': preference.purpose, 'allowed': preference.allowed})


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
