import csv
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Sum, Count, F, Q, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from core.models import User, Person, Lead, ClassGroup, OperationLock
from core.permissions import IsInternal, IsAdministrative, is_administrative
from core.audit import record
from core.services import lock_student_identities
from .models import Enrollment, Charge, Payment, CommercialCondition, EnrollmentSuspension, WaitingListEntry, FrequencyPolicy
from .serializers import (EnrollmentSerializer, ChargeSerializer, PaymentSerializer, ReceiptSerializer, ConditionSerializer,
    EligibilitySerializer, SummarySerializer, PoliciesSerializer, DecisionErrorSerializer, CancelSerializer)
from .services import DecisionRequired, PENDING_DECISIONS, active_on_q, ensure_class_capacity, evaluate_eligibility
from .serializers import MessageRequestSerializer, MessageSentSerializer, MessageResponseSerializer, MessageConfirmationSerializer
from .serializers import EnrollmentCancelSerializer, SuspensionSerializer, WaitingListSerializer


def locked_actor(request):
    actor = User.objects.select_for_update().get(pk=request.user.pk)
    if not is_administrative(actor):
        raise PermissionDenied('A autorização administrativa foi revogada. Atualize a sessão.')
    return actor


def locked_enrollment(pk):
    group_id = Enrollment.objects.values_list('class_group_id', flat=True).get(pk=pk)
    ClassGroup.objects.select_for_update().get(pk=group_id)
    return Enrollment.objects.select_for_update(of=('self',)).select_related('student','class_group').get(pk=pk)


class EnrollmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                        mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    serializer_class = EnrollmentSerializer
    queryset = Enrollment.objects.select_related('student','class_group','financial_catalog').prefetch_related('charges__payments')
    filterset_fields = ['student','class_group','kind','plan']
    search_fields = ['student__name','class_group__name']
    ordering_fields = ['id','start_date','created_at','amount']

    def get_queryset(self):
        qs = super().get_queryset()
        requested = self.request.query_params.get('administrative_status')
        if requested == 'regular':
            return qs.filter(active_on_q(timezone.localdate()))
        if requested == 'cancelled':
            return qs.exclude(active_on_q(timezone.localdate()))
        if requested:
            raise ValidationError({'administrative_status': 'Situação inválida.'})
        return qs

    @extend_schema(request=SuspensionSerializer, responses=SuspensionSerializer(many=True))
    @action(detail=True, methods=['get', 'post'])
    @transaction.atomic
    def suspensions(self, request, pk=None):
        original = self.get_object()
        if request.method == 'GET':
            return Response(SuspensionSerializer(original.suspensions.all(), many=True).data)
        actor = locked_actor(request)
        if 'coordinator' not in actor.roles:
            raise PermissionDenied('Somente a Coordenação pode autorizar suspensões.')
        enrollment = locked_enrollment(pk)
        if enrollment.administrative_status != 'regular':
            raise ValidationError('Somente matrículas regulares podem ser suspensas.')
        serializer = SuspensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start, end = serializer.validated_data['starts_on'], serializer.validated_data['ends_on']
        if start < enrollment.start_date or (enrollment.end_date and end > enrollment.end_date):
            raise ValidationError('A suspensão deve estar dentro da vigência do contrato.')
        if enrollment.suspensions.filter(starts_on__lte=end, ends_on__gte=start).exists():
            raise ValidationError('Já existe suspensão sobreposta a este período.')
        suspension = serializer.save(enrollment=enrollment, actor=actor)
        record(actor, 'enrollment.suspended', suspension, reason=suspension.reason,
               metadata={'enrollment': enrollment.pk, 'starts_on': start.isoformat(), 'ends_on': end.isoformat()})
        return Response(SuspensionSerializer(suspension).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_create(self, serializer, renewed_from=None):
        actor = locked_actor(self.request)
        OperationLock.objects.get_or_create(key='financial-catalog-versions')
        OperationLock.objects.select_for_update().get(key='financial-catalog-versions')
        lock_student_identities()
        group = ClassGroup.objects.select_for_update().get(pk=serializer.validated_data['class_group'].pk)
        student = Person.objects.select_for_update().get(pk=serializer.validated_data['student'].pk)
        if not group.active or student.archived:
            raise ValidationError('Aluno arquivado ou turma inativa. Atualize a oferta.')
        if serializer.validated_data.get('source_lead'):
            lead = Lead.objects.select_for_update().get(pk=serializer.validated_data['source_lead'].pk)
            if lead.status != 'converted' or lead.student_id != student.pk:
                raise ValidationError({'source_lead': 'O lead já não corresponde a esta pessoa.'})
        first_waiting = WaitingListEntry.objects.select_for_update().filter(class_group=group, status='waiting').order_by('created_at', 'id').first()
        if first_waiting and first_waiting.person_id != student.pk:
            raise ValidationError({'class_group': 'A primeira pessoa da lista de espera tem prioridade para a vaga.'})
        if serializer.validated_data.get('contract_version'):
            from .contracts import terms
            from core.models import Modality
            group.modality = Modality.objects.select_for_update().get(pk=group.modality_id)
            data = serializer.validated_data
            data.update(terms(group, data['start_date'], data['plan'], data.get('associated', False), data['payment_method'], data.get('installments', 1)))
            if renewed_from:
                data['fee_amount'] = Decimal('0.00')
                data['schedule'] = [item for item in data['schedule'] if item['category'] != 'enrollment_fee']
        exception_reason = serializer.validated_data.pop('capacity_exception_reason', None) or None
        if exception_reason and ('coordinator' not in actor.roles or group.physical_capacity is None):
            raise PermissionDenied('A exceção exige Coordenação e limite físico cadastrado para a turma.')
        ensure_class_capacity(group, serializer.validated_data['start_date'], serializer.validated_data.get('end_date'), student.pk,
                              group.physical_capacity if exception_reason else None)
        enrollment = serializer.save(administrative_status='regular', renewed_from=renewed_from)
        if first_waiting:
            first_waiting.status, first_waiting.enrollment = 'enrolled', enrollment
            first_waiting.save(update_fields=['status', 'enrollment'])
            record(actor, 'waiting_list.enrolled', first_waiting, metadata={'enrollment': enrollment.pk})
        if enrollment.contract_version:
            from .contracts import generate
            generate(enrollment, actor)
        CommercialCondition.objects.create(enrollment=enrollment, amount=enrollment.amount,
            plan=enrollment.plan, effective_on=enrollment.start_date, actor=actor, reason='Condição inicial informada no cadastro.')
        record(actor, 'enrollment.created', enrollment, metadata={'amount':str(enrollment.amount), 'plan':enrollment.plan})
        if exception_reason:
            record(actor, 'enrollment.capacity_exception', enrollment, reason=exception_reason,
                   metadata={'class_group': group.pk, 'regular_capacity': group.capacity, 'physical_capacity': group.physical_capacity})

    def update(self, request, *args, **kwargs):
        self.get_object()
        raise DecisionRequired('Alterações contratuais exigem política de efeito e vigência. Consulte o histórico original.', ['RN-035','DN-004','DN-011','DN-021'])

    @extend_schema(request=None, responses=EnrollmentSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def repair_charges(self, request, pk=None):
        self.get_object()
        actor = locked_actor(request)
        enrollment = locked_enrollment(pk)
        from .contracts import generate
        generate(enrollment, actor)
        return Response(self.get_serializer(enrollment).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def renew(self, request, pk=None):
        self.get_object()
        actor = locked_actor(request)
        OperationLock.objects.get_or_create(key='financial-catalog-versions')
        OperationLock.objects.select_for_update().get(key='financial-catalog-versions')
        lock_student_identities()
        previous = locked_enrollment(pk)
        existing = Enrollment.objects.filter(renewed_from=previous).first()
        if existing:
            return Response(self.get_serializer(existing).data)
        if not previous.end_date or previous.administrative_status != 'regular':
            raise ValidationError('Somente contrato regular com vigência definida pode ser renovado.')
        data = dict(request.data)
        data.update(student=previous.student_id, class_group=previous.class_group_id)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get('contract_version') or serializer.validated_data['start_date'] <= previous.end_date:
            raise ValidationError('A renovação exige contrato parametrizado com início após o fim da vigência anterior.')
        self.perform_create(serializer, renewed_from=previous)
        enrollment = serializer.instance
        enrollment.renewed_from = previous
        enrollment.save(update_fields=['renewed_from'])
        record(actor, 'enrollment.renewed', enrollment, metadata={'previous': previous.pk})
        return Response(self.get_serializer(enrollment).data, status=201)

    @extend_schema(request=CancelSerializer,responses=EnrollmentSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        self.get_object()
        data = CancelSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        reason = data.validated_data['reason']
        actor = locked_actor(request)
        enrollment = locked_enrollment(pk)
        if enrollment.administrative_status != 'cancelled':
            enrollment.administrative_status = 'cancelled'
            enrollment.cancelled_on = timezone.localdate()
            enrollment.save(update_fields=['administrative_status', 'cancelled_on'])
            record(actor, 'enrollment.cancelled', enrollment, reason=reason,
                   metadata={'effective_on':timezone.localdate().isoformat()})
        return Response(self.get_serializer(enrollment).data)

    @extend_schema(parameters=[OpenApiParameter('on',OpenApiTypes.DATE)],responses=EligibilitySerializer)
    @action(detail=True, methods=['get'])
    def eligibility(self, request, pk=None):
        raw_on = request.query_params.get('on')
        try:
            on = date.fromisoformat(raw_on) if raw_on else None
        except ValueError:
            raise ValidationError({'on':'Data inválida; use AAAA-MM-DD.'})
        return Response(evaluate_eligibility(self.get_object(), on))

    @extend_schema(responses=ConditionSerializer(many=True))
    @action(detail=True, methods=['get'])
    def conditions(self, request, pk=None):
        return Response(ConditionSerializer(self.get_object().conditions.select_related('enrollment__financial_catalog').order_by('-effective_on','-id'), many=True).data)


class ChargeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    serializer_class = ChargeSerializer
    queryset = Charge.objects.select_related('enrollment__student','enrollment__class_group').prefetch_related('payments')
    filterset_fields = ['enrollment','category','competence','enrollment__student']
    search_fields = ['enrollment__student__name','enrollment__class_group__name','description']
    ordering_fields = ['id','due_date','amount','competence']
    ordering = ['due_date','id']

    @extend_schema(methods=['GET'], responses=MessageResponseSerializer(many=True))
    @extend_schema(methods=['POST'], request=MessageRequestSerializer, responses=MessageResponseSerializer(many=True))
    @action(detail=True, methods=['get', 'post'])
    @transaction.atomic
    def messages(self, request, pk=None):
        from urllib.parse import quote
        from .models import CollectionMessage
        from .serializers import MessageRequestSerializer
        charge = self.get_object()
        if request.method == 'POST':
            data = MessageRequestSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            actor = locked_actor(request)
            locked_enrollment(charge.enrollment_id)
            charge = Charge.objects.select_for_update().get(pk=pk)
            if charge.is_paid:
                raise ValidationError('Cobrança já quitada. Atualize a consulta.')
            text = (f'Olá, {data.validated_data["recipient"]}. Identificamos uma cobrança de '
                    f'{charge.enrollment.student.name}, atividade {charge.enrollment.class_group.modality.name}: '
                    f'R$ {charge.amount}, vencimento {charge.due_date:%d/%m/%Y}. '
                    'Entre em contato com a secretaria para orientações de regularização. '
                    'Se já pagou, encaminhe o comprovante para conferência.')
            message = CollectionMessage.objects.create(charge=charge, actor=actor, text=text, **data.validated_data)
            record(actor, 'collection.prepared', message)
        messages = charge.messages.all()
        return Response([{'id': m.pk, 'recipient': m.recipient, 'phone': m.phone, 'text': m.text,
                          'created_at': m.created_at, 'actor': m.actor_id, 'sent_at': m.sent_at,
                          'confirmed_by': m.confirmed_by_id,
                          'url': f'https://wa.me/{m.phone}?text={quote(m.text)}'} for m in messages])

    @extend_schema(request=MessageSentSerializer, responses=MessageConfirmationSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def confirm_message(self, request, pk=None):
        from .serializers import MessageSentSerializer
        charge = self.get_object()
        data = MessageSentSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor = locked_actor(request)
        message = charge.messages.select_for_update().filter(pk=data.validated_data['message']).first()
        if not message:
            raise ValidationError('Mensagem não pertence a esta cobrança.')
        if not message.sent_at:
            message.sent_at, message.confirmed_by = timezone.now(), actor
            message.save(update_fields=['sent_at', 'confirmed_by'])
            record(actor, 'collection.sent_manually', message, metadata={'channel': 'whatsapp', 'confirmation': 'secretaria'})
        return Response({'sent_at': message.sent_at})

    def get_queryset(self):
        qs = super().get_queryset()
        qs = filter_dates(qs, self.request.query_params, 'due_date')
        requested_status = self.request.query_params.get('status')
        if requested_status:
            if requested_status not in ['paid','open','overdue']:
                raise ValidationError({'status':'Situação inválida.'})
            qs = qs.annotate(received_total=Coalesce(Sum('payments__amount'),Decimal('0.00'),
                output_field=DecimalField(max_digits=12,decimal_places=2)))
            paid = Q(received_total__gte=models_f_amount())
            qs = qs.filter(paid) if requested_status == 'paid' else qs.exclude(paid)
            if requested_status == 'overdue':
                qs = qs.filter(due_date__lt=timezone.localdate())
            elif requested_status == 'open':
                qs = qs.filter(due_date__gte=timezone.localdate())
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        actor = locked_actor(self.request)
        enrollment = locked_enrollment(serializer.validated_data['enrollment'].pk)
        if enrollment.contract_version and serializer.validated_data['category'] in ('tuition', 'enrollment_fee'):
            raise ValidationError('Use a regularização do contrato para gerar parcelas e taxa sem duplicação.')
        if enrollment.administrative_status == 'cancelled':
            raise DecisionRequired('Novas obrigações após cancelamento exigem política específica.', ['DN-011'])
        key = None
        if serializer.validated_data['category'] == 'tuition' and 'RN-037' in settings.BUSINESS_APPROVALS:
            competence = serializer.validated_data['competence']
            key = f'tuition:{enrollment.pk}:{competence.isoformat()}'
            if Charge.objects.filter(enrollment=enrollment, category='tuition', competence=competence).exists():
                raise ValidationError({'competence':'Já existe mensalidade nesta competência.'})
        charge = serializer.save(idempotency_key=key)
        record(actor, 'charge.created', charge, metadata={'amount':str(charge.amount), 'category':charge.category})

    @extend_schema(request=None,responses={409:DecisionErrorSerializer})
    @action(detail=False, methods=['post'])
    def generate(self, request):
        raise DecisionRequired('Geração automática indisponível: periodicidade, cobertura e horizonte aguardam decisão.', ['DN-004','DN-005','DN-006'])

    @extend_schema(request=ReceiptSerializer,responses={201:PaymentSerializer,409:DecisionErrorSerializer})
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def receive(self, request, pk=None):
        original = self.get_object()
        receipt = ReceiptSerializer(data=request.data)
        receipt.is_valid(raise_exception=True)
        actor = locked_actor(request)
        key = receipt.validated_data.pop('request_key', None)
        if key:
            lock_key = f'billing-payment:{key}'
            OperationLock.objects.get_or_create(key=lock_key)
            OperationLock.objects.select_for_update().get(key=lock_key)
        enrollment = locked_enrollment(original.enrollment_id)
        charge = Charge.objects.select_for_update().get(pk=pk)
        if key:
            existing = Payment.objects.filter(request_key=key).first()
            if existing:
                if existing.charge_id == charge.pk and all(getattr(existing, field) == value for field, value in receipt.validated_data.items()):
                    return Response(PaymentSerializer(existing).data)
                raise ValidationError({'request_key': 'Esta chave já foi usada para outro recebimento.'})
        payments = list(Payment.objects.select_for_update().filter(charge=charge))
        balance = charge.amount - sum((p.amount for p in payments), Decimal('0'))
        if not key and len(payments) == 1 and enrollment.contract_version and payments[0].request_key is None and all(getattr(payments[0], field) == value for field, value in receipt.validated_data.items()):
            return Response(PaymentSerializer(payments[0]).data)
        if receipt.validated_data['amount'] > balance:
            raise DecisionRequired('O valor recebido excede o saldo da cobrança.', ['DN-008'])
        if not key and (payments or receipt.validated_data['amount'] != charge.amount):
            raise ValidationError({'request_key': 'Informe uma chave única para registrar pagamentos parciais.'})
        payment = Payment.objects.create(charge=charge, actor=actor, request_key=key, **receipt.validated_data)
        record(actor, 'payment.received', payment, metadata={
            'charge':charge.pk,'enrollment':enrollment.pk,'amount':str(payment.amount),
            'paid_on':payment.paid_on.isoformat(),'method':payment.method})
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


def models_f_amount():
    from django.db.models import F
    return F('amount')


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    queryset = Payment.objects.select_related('charge__enrollment__student','actor')
    serializer_class = PaymentSerializer
    filterset_fields = ['charge','method','charge__category','charge__enrollment']
    search_fields = ['charge__enrollment__student__name','reference']
    ordering_fields = ['paid_on','id','amount']

    def get_queryset(self):
        return filter_dates(super().get_queryset(), self.request.query_params, 'paid_on')


def filter_dates(qs, params, field):
    for key, lookup in [('start','gte'),('end','lte')]:
        if params.get(key):
            try:
                parsed = date.fromisoformat(params[key])
            except ValueError:
                raise ValidationError({key:'Data inválida; use AAAA-MM-DD.'})
            qs = qs.filter(**{f'{field}__{lookup}':parsed})
    if params.get('start') and params.get('end') and params['start'] > params['end']:
        raise ValidationError('Início do período deve anteceder o fim.')
    return qs


class OccupancyRowSerializer(serializers.Serializer):
    class_group = serializers.IntegerField()
    name = serializers.CharField()
    capacity = serializers.IntegerField()
    regular = serializers.IntegerField()
    experimental = serializers.IntegerField()
    waiting = serializers.IntegerField()
    percent = serializers.DecimalField(max_digits=10, decimal_places=2)


class AvailablePlanSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    months = serializers.IntegerField()
    installments = serializers.ListField(child=serializers.IntegerField())


class FinancialOptionsSerializer(serializers.Serializer):
    plans = AvailablePlanSerializer(many=True)
    methods = serializers.ListField(child=serializers.CharField())


class FinancialOptionsView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(parameters=[OpenApiParameter('on', OpenApiTypes.DATE)], responses=FinancialOptionsSerializer)
    def get(self, request):
        from .models import FinancialCatalogVersion
        try:
            on = date.fromisoformat(request.query_params.get('on', timezone.localdate().isoformat()))
        except ValueError:
            raise ValidationError({'on': 'Informe uma data válida.'})
        published = FinancialCatalogVersion.objects.filter(status='published')
        matches = list(published.filter(effective_from__lte=on).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=on))[:2])
        if len(matches) > 1:
            raise ValidationError('Há tabelas publicadas sobrepostas para esta data.')
        labels = {'monthly': 'Mensal', 'quarterly': 'Trimestral', 'yearly': 'Anual'}
        if matches:
            config = matches[0].configuration
            plans = [{'code': code, 'name': plan.get('name') or labels.get(code, code), 'months': plan['months'], 'installments': plan['installments']} for code, plan in config['plans'].items()]
            return Response({'plans': plans, 'methods': sorted({item['method'] for item in config['prices']})})
        if not published.exists() and on.year == 2026:
            return Response({'plans': [{'code': 'quarterly', 'name': 'Trimestral', 'months': 3, 'installments': [1, 2, 3]},
                                       {'code': 'yearly', 'name': 'Anual', 'months': 12, 'installments': [3, 6, 10, 12]}], 'methods': ['card']})
        return Response({'plans': [], 'methods': []})


class OccupancySerializer(serializers.Serializer):
    on = serializers.DateField()
    definition = serializers.CharField()
    classes = OccupancyRowSerializer(many=True)


class OccupancyView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(responses=OccupancySerializer)
    def get(self, request):
        today = timezone.localdate()
        active = Q(enrollments__administrative_status='regular', enrollments__start_date__lte=today) & (
            Q(enrollments__end_date__isnull=True) | Q(enrollments__end_date__gte=today))
        groups = ClassGroup.objects.filter(active=True).annotate(
            regular_count=Count('enrollments', filter=active & Q(enrollments__kind='regular'), distinct=True),
            trial_count=Count('enrollments', filter=active & Q(enrollments__kind='trial'), distinct=True),
            session_trial_count=Count('lessons__trials', filter=Q(lessons__date=today, lessons__status__in=['scheduled', 'completed']) & (Q(lessons__trials__status='scheduled') | Q(lessons__trials__status='completed', lessons__trials__present=True)), distinct=True),
            waiting_count=Count('waiting_list', filter=Q(waiting_list__status='waiting'), distinct=True),
        ).order_by('name', 'id')
        return Response({'on': today, 'definition': 'Matrículas regulares vigentes divididas pela capacidade; experimentais agendadas ou presentes e lista de espera são contadas separadamente.',
                         'classes': [{'class_group': group.pk, 'name': group.name, 'capacity': group.capacity,
                                      'regular': group.regular_count, 'experimental': group.trial_count + group.session_trial_count,
                                      'waiting': group.waiting_count,
                                      'percent': (Decimal(group.regular_count) * 100 / Decimal(group.capacity)).quantize(Decimal('0.01'))}
                                     for group in groups]})


class ConversionSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    leads = serializers.IntegerField()
    converted_people = serializers.IntegerField()
    converted_enrollments = serializers.IntegerField()
    person_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    enrollment_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    definition = serializers.CharField()


class ConversionView(APIView):
    permission_classes = [IsInternal]

    @extend_schema(parameters=[OpenApiParameter('start', OpenApiTypes.DATE), OpenApiParameter('end', OpenApiTypes.DATE)], responses=ConversionSerializer)
    def get(self, request):
        if not is_administrative(request.user) and 'communication' not in request.user.roles:
            raise PermissionDenied('Seu perfil não permite consultar indicadores comerciais.')
        today = timezone.localdate()
        try:
            start = date.fromisoformat(request.query_params.get('start', today.replace(day=1).isoformat()))
            end = date.fromisoformat(request.query_params.get('end', today.isoformat()))
        except ValueError:
            raise ValidationError('Informe datas válidas no formato AAAA-MM-DD.')
        if start > end:
            raise ValidationError('O início deve ser anterior ou igual ao fim.')
        cohort = Lead.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
        total = cohort.count()
        people = cohort.filter(status='converted', student__isnull=False).count()
        enrollments = cohort.filter(origin_enrollments__isnull=False).distinct().count()
        def percent(value):
            return (Decimal(value) * 100 / total).quantize(Decimal('0.01')) if total else None
        return Response({'start': start, 'end': end, 'leads': total, 'converted_people': people,
                         'converted_enrollments': enrollments, 'person_percent': percent(people),
                         'enrollment_percent': percent(enrollments),
                         'definition': 'Coorte por data de cadastro do lead; resultados até hoje. Matrículas contam apenas quando o lead de origem foi informado.'})


class AttritionSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    active_at_start = serializers.IntegerField()
    early_cancellations = serializers.IntegerField()
    normal_completions = serializers.IntegerField()
    unknown_end = serializers.IntegerField()
    unknown_cancellation = serializers.IntegerField()
    percent = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)
    definition = serializers.CharField()


class AttritionView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(parameters=[OpenApiParameter('start', OpenApiTypes.DATE), OpenApiParameter('end', OpenApiTypes.DATE)], responses=AttritionSerializer)
    def get(self, request):
        today = timezone.localdate()
        try:
            start = date.fromisoformat(request.query_params.get('start', today.replace(day=1).isoformat()))
            end = date.fromisoformat(request.query_params.get('end', today.isoformat()))
        except ValueError:
            raise ValidationError('Informe datas válidas no formato AAAA-MM-DD.')
        if start > end or end > today:
            raise ValidationError('Informe um período encerrado, com início anterior ou igual ao fim.')
        candidates = Enrollment.objects.filter(kind='regular', start_date__lte=start).filter(Q(end_date__isnull=True) | Q(end_date__gte=start)).exclude(administrative_status='cancelled', cancelled_on__lte=start)
        unknown_end = candidates.filter(end_date__isnull=True).count()
        known = candidates.filter(end_date__isnull=False)
        unknown_cancellation = known.filter(administrative_status='cancelled', cancelled_on__isnull=True).count()
        baseline = known.filter(Q(administrative_status='regular') | Q(administrative_status='cancelled', cancelled_on__gt=start))
        count = baseline.count()
        early = baseline.filter(administrative_status='cancelled', cancelled_on__gt=start, cancelled_on__lte=end, cancelled_on__lt=F('end_date')).count()
        normal = baseline.filter(end_date__gte=start, end_date__lte=end).filter(Q(administrative_status='regular') | Q(cancelled_on__gte=F('end_date'))).count()
        return Response({'start': start, 'end': end, 'active_at_start': count, 'early_cancellations': early,
                         'normal_completions': normal, 'unknown_end': unknown_end,
                         'unknown_cancellation': unknown_cancellation,
                         'percent': (Decimal(early) * 100 / count).quantize(Decimal('0.01')) if count else None,
                         'definition': 'Cancelamentos antecipados durante o período divididos pelas matrículas regulares vigentes no início. Registros sem vigência ou data de cancelamento conhecida são apresentados separadamente.'})


class FrequencyWindowSerializer(serializers.Serializer):
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class FrequencyRowSerializer(serializers.Serializer):
    enrollment = serializers.IntegerField()
    person = serializers.CharField()
    class_name = serializers.CharField()
    short_window = FrequencyWindowSerializer()
    long_window = FrequencyWindowSerializer()
    consecutive_absences = serializers.IntegerField()
    alert = serializers.BooleanField()


class FrequencySerializer(serializers.Serializer):
    on = serializers.DateField()
    definition = serializers.CharField()
    short_days = serializers.IntegerField()
    long_days = serializers.IntegerField()
    absence_threshold = serializers.IntegerField()
    enrollments = FrequencyRowSerializer(many=True)


class FrequencyView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(responses=FrequencySerializer)
    def get(self, request):
        from academic.models import Attendance, Lesson
        today = timezone.localdate()
        policy = FrequencyPolicy.objects.filter(pk=1).first()
        short_days, long_days, threshold = (policy.short_days, policy.long_days, policy.absence_threshold) if policy else (30, 90, 3)
        active = Enrollment.objects.filter(administrative_status='regular', kind='regular', start_date__lte=today,
            student__archived=False, class_group__active=True).filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        rows = {e.pk: {'enrollment': e.pk, 'person': e.student.name, 'class_name': e.class_group.name,
                       'short_window': {'present': 0, 'absent': 0}, 'long_window': {'present': 0, 'absent': 0},
                       'consecutive_absences': 0, '_streak_open': True}
                for e in active.select_related('student', 'class_group').order_by('student__name', 'id')}
        marks = Attendance.objects.filter(enrollment_id__in=rows, lesson__status=Lesson.Status.COMPLETED,
            lesson__date__lte=today, lesson__date__gte=F('enrollment__start_date')).filter(
            Q(enrollment__end_date__isnull=True) | Q(lesson__date__lte=F('enrollment__end_date'))
        ).select_related('lesson').order_by('enrollment_id', '-lesson__date', '-id')
        for mark in marks.iterator():
            row = rows[mark.enrollment_id]
            if row['_streak_open']:
                if mark.present:
                    row['_streak_open'] = False
                else:
                    row['consecutive_absences'] += 1
            for days, key in ((short_days, 'short_window'), (long_days, 'long_window')):
                if mark.lesson.date >= today - timedelta(days=days - 1):
                    row[key]['present' if mark.present else 'absent'] += 1
        for row in rows.values():
            del row['_streak_open']
            row['alert'] = row['consecutive_absences'] >= threshold
            for key in ('short_window', 'long_window'):
                window = row[key]
                total = window['present'] + window['absent']
                window['percent'] = (Decimal(window['present']) * 100 / total).quantize(Decimal('0.01')) if total else None
        return Response({'on': today, 'definition': 'Presenças divididas por presenças e faltas em aulas concluídas; canceladas e experimentais são excluídas.', 'short_days': short_days, 'long_days': long_days, 'absence_threshold': threshold, 'enrollments': list(rows.values())})


class FrequencyPolicySerializer(serializers.Serializer):
    short_days = serializers.IntegerField(min_value=1, max_value=3650)
    long_days = serializers.IntegerField(min_value=1, max_value=3650)
    absence_threshold = serializers.IntegerField(min_value=1, max_value=100)
    reason = serializers.CharField(max_length=2000, write_only=True)

    def validate(self, data):
        if data['short_days'] > data['long_days']:
            raise serializers.ValidationError({'short_days': 'A janela menor não pode superar a maior.'})
        return data


class FrequencyPolicyView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(responses=FrequencyPolicySerializer)
    def get(self, request):
        policy = FrequencyPolicy.objects.filter(pk=1).first()
        return Response({'short_days': policy.short_days if policy else 30, 'long_days': policy.long_days if policy else 90,
                         'absence_threshold': policy.absence_threshold if policy else 3})

    @extend_schema(request=FrequencyPolicySerializer, responses=FrequencyPolicySerializer)
    @transaction.atomic
    def post(self, request):
        actor = locked_actor(request)
        if 'coordinator' not in actor.roles:
            raise PermissionDenied('Somente a Coordenação pode configurar os indicadores.')
        data = FrequencyPolicySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        OperationLock.objects.get_or_create(key='frequency-policy')
        OperationLock.objects.select_for_update().get(key='frequency-policy')
        policy, _ = FrequencyPolicy.objects.get_or_create(pk=1)
        before = {'short_days': policy.short_days, 'long_days': policy.long_days, 'absence_threshold': policy.absence_threshold}
        for key in before:
            setattr(policy, key, data.validated_data[key])
        policy.updated_by = actor
        policy.save()
        after = {key: getattr(policy, key) for key in before}
        record(actor, 'frequency_policy.updated', policy, reason=data.validated_data['reason'], metadata={'before': before, 'after': after})
        return Response(after)


class SummaryView(APIView):
    permission_classes = [IsInternal]
    serializer_class = SummarySerializer

    @extend_schema(parameters=[OpenApiParameter('start',OpenApiTypes.DATE),OpenApiParameter('end',OpenApiTypes.DATE)],responses=SummarySerializer)
    def get(self, request):
        today = timezone.localdate()
        params = {'start':request.query_params.get('start',today.replace(day=1).isoformat()),
                  'end':request.query_params.get('end',today.isoformat())}
        # Validation also runs for roles without access to financial records.
        leads = filter_dates(Lead.objects.all(), params, 'created_at__date')
        result = {'start':params['start'],'end':params['end'], 'demo':settings.DEMO_MODE,
                  'timezone':settings.TIME_ZONE, 'pending_decisions':['DN-017','DN-018','DN-019']}
        if is_administrative(request.user) or 'communication' in request.user.roles:
            result.update(leads=leads.count(), conversions=leads.filter(student__isnull=False).count(),
                converted_enrollments=Enrollment.objects.filter(student__in=leads.values('student')).count(),
                commercial_definition='Interessados criados no período e vínculo de conversão atual; matrículas dos alunos dessa população contadas separadamente. Não representa taxa de conversão.')
        if not is_administrative(request.user):
            if 'instructor' in request.user.roles:
                result['classes'] = ClassGroup.objects.filter(instructor__user=request.user,instructor__active=True,active=True).count()
            return Response(result)
        charges = list(filter_dates(Charge.objects.all(),params,'due_date').prefetch_related('payments'))
        payments = filter_dates(Payment.objects.all(),params,'paid_on')
        zero = Decimal('0.00')
        received = payments.aggregate(value=Sum('amount'))['value'] or zero
        expected = sum((c.amount for c in charges),zero)
        outstanding = sum((max(c.amount-c.received,zero) for c in charges),zero)
        overdue = sum((max(c.amount-c.received,zero) for c in charges if c.due_date < today),zero)
        categories = {category: str(payments.filter(charge__category=category).aggregate(value=Sum('amount'))['value'] or zero)
                      for category in ['tuition','enrollment_fee','extra']}
        result.update(students=Person.objects.filter(archived=False, enrollments__isnull=False).distinct().count(),
            enrollments=Enrollment.objects.filter(administrative_status='regular').count(),
            classes=ClassGroup.objects.filter(active=True).count(),
            pending_users=User.objects.filter(access_status='pending').count(),
            received=str(received), expected=str(expected),outstanding=str(outstanding), overdue=str(overdue),
            categories=categories, base=None, final_payout=None,
            financial_definition='Recebido: data de recebimento no período. Previsto: cobranças com vencimento no período. Saldo e vencidos: dessas cobranças, recebimentos registrados até a consulta. Contagens cadastrais refletem a situação atual. Definição institucional e atribuição do repasse pendentes.')
        return Response(result)


def safe_csv(value):
    value = '' if value is None else str(value)
    return "'" + value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value


class ExportView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(parameters=[OpenApiParameter('resource',str,enum=['students','charges','payments']),
        OpenApiParameter('search',str),OpenApiParameter('start',OpenApiTypes.DATE),OpenApiParameter('end',OpenApiTypes.DATE)],
        responses={(200,'text/csv'):OpenApiTypes.BINARY})
    def get(self, request):
        resource = request.query_params.get('resource','students')
        if resource not in ['students','charges','payments']:
            raise ValidationError({'resource':'Selecione students, charges ou payments.'})
        cls = {'students':None,'charges':ChargeViewSet,'payments':PaymentViewSet}[resource]
        if resource == 'students':
            from core.views import PersonViewSet
            cls = PersonViewSet
        view = cls()
        view.request, view.action, view.format_kwarg = request, 'list', None
        qs = view.filter_queryset(view.get_queryset())
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="movi-{resource}-todos-filtrados.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        if resource == 'students':
            writer.writerow(['ID','Nome','E-mail','Telefone','Arquivado'])
            rows = ((o.pk,o.name,o.email,o.phone,o.archived) for o in qs)
        elif resource == 'charges':
            writer.writerow(['ID','Matrícula','Aluno','Categoria','Competência','Vencimento','Devido','Recebido','Situação'])
            rows = ((o.pk,o.enrollment_id,o.enrollment.student.name,o.category,o.competence,o.due_date,o.amount,o.received,o.status) for o in qs)
        else:
            writer.writerow(['ID','Cobrança','Recebido','Data','Forma'])
            rows = ((o.pk,o.charge_id,o.amount,o.paid_on,o.method) for o in qs)
        for row in rows:
            writer.writerow([safe_csv(value) for value in row])
        return response


class PoliciesView(APIView):
    permission_classes = [IsInternal]
    serializer_class = PoliciesSerializer

    @extend_schema(responses=PoliciesSerializer)
    def get(self, request):
        return Response({'pending':[{'id':pk,'title':title,'impact':impact} for pk,title,impact in PENDING_DECISIONS],
                         'approved':settings.BUSINESS_APPROVALS,'demo':settings.DEMO_MODE,'timezone':settings.TIME_ZONE})


class WaitingListViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    serializer_class = WaitingListSerializer
    queryset = WaitingListEntry.objects.select_related('person', 'class_group').all()
    filterset_fields = ['class_group', 'person', 'status']
    ordering_fields = ['created_at', 'id']

    @transaction.atomic
    def perform_create(self, serializer):
        actor = locked_actor(self.request)
        lock_student_identities()
        group = ClassGroup.objects.select_for_update().get(pk=serializer.validated_data['class_group'].pk)
        person = Person.objects.select_for_update().get(pk=serializer.validated_data['person'].pk)
        if not group.active or person.archived:
            raise ValidationError('Pessoa ou turma inativa.')
        if WaitingListEntry.objects.filter(class_group=group, person=person, status='waiting').exists():
            raise ValidationError('Esta pessoa já está na lista de espera da turma.')
        entry = serializer.save(class_group=group, person=person, actor=actor)
        record(actor, 'waiting_list.created', entry, metadata={'class_group': group.pk, 'person': person.pk})

    @extend_schema(request=CancelSerializer, responses=WaitingListSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        original = self.get_object()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = locked_actor(request)
        ClassGroup.objects.select_for_update().get(pk=original.class_group_id)
        entry = WaitingListEntry.objects.select_for_update().get(pk=pk)
        if entry.status != 'waiting':
            raise ValidationError('A pessoa já saiu da lista de espera.')
        entry.status = 'cancelled'
        entry.save(update_fields=['status'])
        record(actor, 'waiting_list.cancelled', entry, reason=serializer.validated_data['reason'])
        return Response(self.get_serializer(entry).data)
