from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from billing.models import Enrollment
from core.audit import record
from core.models import ClassGroup, Instructor, Person
from core.permissions import IsInternal, is_administrative
from core.serializers import ReasonSerializer
from core.services import lock_admin, lock_student_identities
from .models import Lesson, TrialParticipation
from .serializers import TrialCorrectionSerializer, TrialMarkSerializer, TrialSerializer
from .services import _can_submit, _locked_lesson


class TrialViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal]
    serializer_class = TrialSerializer
    filterset_fields = ['lesson', 'person', 'status']
    queryset = TrialParticipation.objects.select_related('person', 'lesson__class_group').all()

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        user = self.request.user
        if is_administrative(user):
            return qs
        instructor = Instructor.objects.filter(user=user, active=True).values_list('pk', flat=True).first()
        if instructor and 'instructor' in user.roles:
            return qs.filter(Q(lesson__class_group__instructor_id=instructor) | Q(lesson__assigned_instructor_id=instructor))
        return qs.none()

    @transaction.atomic
    def perform_create(self, serializer):
        actor = lock_admin(self.request.user)
        lock_student_identities()
        lesson_ref = serializer.validated_data['lesson']
        group = ClassGroup.objects.select_for_update().get(pk=lesson_ref.class_group_id)
        lesson = Lesson.objects.select_for_update().get(pk=lesson_ref.pk, class_group=group)
        person = Person.objects.select_for_update().get(pk=serializer.validated_data['person'].pk)
        if not group.active or not group.allows_trial or person.archived:
            raise ValidationError('A turma deve estar ativa, permitir experimentais e a pessoa não pode estar arquivada.')
        if lesson.status != Lesson.Status.SCHEDULED or lesson.date < timezone.localdate():
            raise ValidationError('A aula experimental exige encontro agendado para hoje ou data futura.')
        if person.birth_date:
            age = lesson.date.year - person.birth_date.year - ((lesson.date.month, lesson.date.day) < (person.birth_date.month, person.birth_date.day))
            if age < 18 and not serializer.validated_data.get('guardian_authorization'):
                raise ValidationError({'guardian_authorization': 'Registre a autorização do responsável para menor de idade.'})
        if TrialParticipation.objects.filter(person=person, modality=group.modality).exclude(status='cancelled').exists():
            raise ValidationError('Esta pessoa já possui experimental registrada nesta modalidade.')
        regular = Enrollment.objects.filter(class_group=group, administrative_status='regular', kind='regular', start_date__lte=lesson.date).filter(Q(end_date__isnull=True) | Q(end_date__gte=lesson.date)).count()
        if Enrollment.objects.filter(class_group=group, student=person, administrative_status='regular', kind='regular', start_date__lte=lesson.date).filter(Q(end_date__isnull=True) | Q(end_date__gte=lesson.date)).exists():
            raise ValidationError('Esta pessoa já possui matrícula regular vigente na turma nesta data.')
        trial_count = TrialParticipation.objects.filter(lesson=lesson, status__in=['scheduled', 'completed']).count()
        if regular + trial_count >= group.capacity:
            raise ValidationError('A aula não possui vaga para participação experimental.')
        trial = serializer.save(person=person, lesson=lesson, modality=group.modality, actor=actor)
        record(actor, 'trial.scheduled', trial, metadata={'person': person.pk, 'lesson': lesson.pk, 'modality': group.modality_id, 'guardian_authorization': trial.guardian_authorization})

    @extend_schema(request=TrialMarkSerializer, responses=TrialSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def mark(self, request, pk=None):
        original = self.get_object()
        data = TrialMarkSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor, group, lesson = _locked_lesson(request.user.pk, original.lesson_id)
        _can_submit(actor, lesson, group)
        trial = TrialParticipation.objects.select_for_update().get(pk=pk)
        if lesson.status != Lesson.Status.COMPLETED or trial.status != 'scheduled':
            raise ValidationError('A marcação exige aula concluída e experimental ainda não registrada.')
        trial.status, trial.present = 'completed', data.validated_data['present']
        trial.save(update_fields=['status', 'present'])
        record(actor, 'trial.marked', trial, metadata={'present': trial.present, 'lesson': lesson.pk})
        return Response(self.get_serializer(trial).data)

    @extend_schema(request=TrialCorrectionSerializer, responses=TrialSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def correct(self, request, pk=None):
        original = self.get_object()
        data = TrialCorrectionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor, group, lesson = _locked_lesson(request.user.pk, original.lesson_id)
        _can_submit(actor, lesson, group)
        trial = TrialParticipation.objects.select_for_update().get(pk=pk)
        if lesson.status != Lesson.Status.COMPLETED or trial.status != 'completed':
            raise ValidationError('A correção exige uma marcação já registrada em aula concluída.')
        before = trial.present
        trial.present = data.validated_data['present']
        trial.save(update_fields=['present'])
        record(actor, 'trial.corrected', trial, reason=data.validated_data['reason'], metadata={'before': before, 'after': trial.present, 'lesson': lesson.pk})
        return Response(self.get_serializer(trial).data)

    @extend_schema(request=ReasonSerializer, responses=TrialSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        original = self.get_object()
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor = lock_admin(request.user)
        ClassGroup.objects.select_for_update().get(pk=original.lesson.class_group_id)
        lesson = Lesson.objects.select_for_update().get(pk=original.lesson_id)
        trial = TrialParticipation.objects.select_for_update().get(pk=pk)
        if trial.status != 'scheduled' or lesson.status == Lesson.Status.COMPLETED:
            raise ValidationError('Apenas experimentais agendadas de aulas não concluídas podem ser canceladas.')
        trial.status = 'cancelled'
        trial.save(update_fields=['status'])
        record(actor, 'trial.cancelled', trial, reason=data.validated_data['reason'])
        return Response(self.get_serializer(trial).data)
