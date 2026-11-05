import csv
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from core.models import User, Person, Lead, ClassGroup
from core.permissions import IsInternal, IsAdministrative, is_administrative
from core.audit import record
from core.services import lock_student_identities
from .models import Enrollment, Charge, Payment, CommercialCondition
from .serializers import (EnrollmentSerializer, ChargeSerializer, PaymentSerializer, ReceiptSerializer, ConditionSerializer,
    EligibilitySerializer, SummarySerializer, PoliciesSerializer, DecisionErrorSerializer, CancelSerializer)
from .services import DecisionRequired, PENDING_DECISIONS, evaluate_eligibility
from .serializers import MessageRequestSerializer, MessageSentSerializer, MessageResponseSerializer, MessageConfirmationSerializer


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
    queryset = Enrollment.objects.select_related('student','class_group').prefetch_related('charges__payments')
    filterset_fields = ['student','class_group','administrative_status','kind','plan']
    search_fields = ['student__name','class_group__name']
    ordering_fields = ['id','start_date','created_at','amount']

    @transaction.atomic
    def perform_create(self, serializer, renewed_from=None):
        actor = locked_actor(self.request)
        lock_student_identities()
        group = ClassGroup.objects.select_for_update().get(pk=serializer.validated_data['class_group'].pk)
        student = Person.objects.select_for_update().get(pk=serializer.validated_data['student'].pk)
        if not group.active or student.archived:
            raise ValidationError('Aluno arquivado ou turma inativa. Atualize a oferta.')
        if serializer.validated_data.get('contract_version'):
            from .contracts import terms
            from core.models import Modality
            group.modality = Modality.objects.select_for_update().get(pk=group.modality_id)
            data = serializer.validated_data
            data.update(terms(group, data['start_date'], data['plan'], data.get('associated', False), data['payment_method'], data.get('installments', 1)))
            if renewed_from:
                data['fee_amount'] = Decimal('0.00')
                data['schedule'] = [item for item in data['schedule'] if item['category'] != 'enrollment_fee']
        enrollment = serializer.save(administrative_status='regular', renewed_from=renewed_from)
        if enrollment.contract_version:
            from .contracts import generate
            generate(enrollment, actor)
        CommercialCondition.objects.create(enrollment=enrollment, amount=enrollment.amount,
            plan=enrollment.plan, effective_on=enrollment.start_date, actor=actor, reason='Condição inicial informada no cadastro.')
        record(actor, 'enrollment.created', enrollment, metadata={'amount':str(enrollment.amount), 'plan':enrollment.plan})

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
            enrollment.save(update_fields=['administrative_status'])
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
        return Response(ConditionSerializer(self.get_object().conditions.order_by('-effective_on','-id'), many=True).data)


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
        enrollment = locked_enrollment(original.enrollment_id)
        charge = Charge.objects.select_for_update().get(pk=pk)
        existing = Payment.objects.select_for_update().filter(charge=charge).first()
        if existing:
            if enrollment.contract_version and all(getattr(existing, key) == value for key, value in receipt.validated_data.items()):
                return Response(PaymentSerializer(existing).data)
            raise DecisionRequired('Esta cobrança já possui recebimento. Correções e estornos aguardam política.', ['DN-008','RN-048'])
        if receipt.validated_data['amount'] != charge.amount:
            raise DecisionRequired('Baixa integral exige valor recebido igual ao devido. Pagamento parcial ou excedente não foi registrado.', ['DN-008'])
        payment = Payment.objects.create(charge=charge, actor=actor, **receipt.validated_data)
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
