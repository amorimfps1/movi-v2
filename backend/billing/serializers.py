from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Enrollment, Charge, Payment, CommercialCondition, EnrollmentSuspension, WaitingListEntry
from .services import DecisionRequired, evaluate_eligibility


class EligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField(allow_null=True)
    status = serializers.CharField()
    reason = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField())


class EnrollmentSerializer(serializers.ModelSerializer):
    payment_method = serializers.ChoiceField(choices=['card', 'boleto'], required=False)
    capacity_exception_reason = serializers.CharField(max_length=2000, required=False, write_only=True, allow_blank=True)
    student_name = serializers.CharField(source='student.name', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)
    eligibility = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    administrative_status = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id','student','class_group','student_name','class_name','start_date','plan','plan_name','amount',
                  'administrative_status','cancelled_on','kind','created_at','eligibility', 'contract_version',
                  'end_date', 'associated', 'payment_method', 'installments', 'fee_amount', 'renewed_from', 'schedule', 'financial_catalog', 'source_lead', 'capacity_exception_reason']
        read_only_fields = ['administrative_status','cancelled_on','created_at', 'contract_version', 'end_date', 'fee_amount', 'renewed_from', 'schedule', 'financial_catalog']
        extra_kwargs = {'amount': {'required': False}}

    @extend_schema_field(EligibilitySerializer)
    def get_eligibility(self, obj):
        return evaluate_eligibility(obj)

    def get_plan_name(self, obj) -> str:
        if obj.financial_catalog_id:
            plan = obj.financial_catalog.configuration.get('plans', {}).get(obj.plan, {})
            return plan.get('name') or {'monthly': 'Mensal', 'quarterly': 'Trimestral', 'yearly': 'Anual'}.get(obj.plan, obj.plan)
        return {'monthly': 'Mensal', 'quarterly': 'Trimestral', 'yearly': 'Anual'}.get(obj.plan, obj.plan)

    def get_administrative_status(self, obj) -> str:
        if obj.administrative_status == 'cancelled' and obj.cancelled_on and obj.cancelled_on > timezone.localdate():
            return 'regular'
        return obj.administrative_status

    def validate(self, attrs):
        if attrs.get('kind') == 'trial':
            raise DecisionRequired('Experimental aguarda política detalhada de duração, quantidade e condições.', ['DN-013'])
        student = attrs.get('student', getattr(self.instance, 'student', None))
        group = attrs.get('class_group', getattr(self.instance, 'class_group', None))
        source = attrs.get('source_lead')
        if source and (source.status != 'converted' or source.student_id != getattr(student, 'pk', None)):
            raise serializers.ValidationError({'source_lead': 'Selecione um lead convertido para esta pessoa.'})
        if student and student.archived:
            raise serializers.ValidationError({'student': 'Aluno arquivado.'})
        if group and not group.active:
            raise serializers.ValidationError({'class_group': 'Turma inativa.'})
        if attrs.get('payment_method'):
            from .contracts import terms
            attrs.update(terms(group, attrs['start_date'], attrs['plan'], attrs.get('associated', False),
                               attrs['payment_method'], attrs.get('installments', 1)))
        else:
            raise serializers.ValidationError({'payment_method': 'Novas matrículas exigem meio de pagamento e contrato parametrizado.'})
        return attrs


class ChargeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)
    class_name = serializers.CharField(source='enrollment.class_group.name', read_only=True)
    received = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Charge
        fields = ['id','enrollment','category','competence','due_date','amount','description',
                  'student_name','class_name','received','status','created_at','cancelled_on','cancelled_by','cancellation_reason']
        read_only_fields = ['created_at','cancelled_on','cancelled_by','cancellation_reason']

    def validate(self, attrs):
        if attrs['category'] == 'tuition':
            competence = attrs.get('competence')
            if not competence or competence.day != 1:
                raise serializers.ValidationError({'competence': 'Informe o primeiro dia da competência (AAAA-MM-01).'})
        return attrs


class ReceiptSerializer(serializers.Serializer):
    request_key = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    paid_on = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment._meta.get_field('method').choices)
    reference = serializers.CharField(max_length=160, required=False, allow_blank=True, default='')

    def validate_paid_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('Recebimento não pode ter data futura.')
        return value


class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='charge.enrollment.student.name', read_only=True)
    category = serializers.CharField(source='charge.category', read_only=True)

    class Meta:
        model = Payment
        fields = ['id','charge','amount','paid_on','method','reference','actor','created_at','student_name','category']


class ConditionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()

    def get_plan_name(self, obj) -> str:
        catalog = obj.enrollment.financial_catalog
        if catalog:
            data = catalog.configuration.get('plans', {}).get(obj.plan, {})
            return data.get('name') or {'monthly': 'Mensal', 'quarterly': 'Trimestral', 'yearly': 'Anual'}.get(obj.plan, obj.plan)
        return {'monthly': 'Mensal', 'quarterly': 'Trimestral', 'yearly': 'Anual'}.get(obj.plan, obj.plan)

    class Meta:
        model = CommercialCondition
        fields = ['id','enrollment','amount','effective_on','plan','plan_name','actor','reason','created_at']


class SummarySerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()
    demo = serializers.BooleanField()
    timezone = serializers.CharField()
    pending_decisions = serializers.ListField(child=serializers.CharField())
    students = serializers.IntegerField(required=False)
    enrollments = serializers.IntegerField(required=False)
    classes = serializers.IntegerField(required=False)
    pending_users = serializers.IntegerField(required=False)
    leads = serializers.IntegerField(required=False)
    conversions = serializers.IntegerField(required=False)
    converted_enrollments = serializers.IntegerField(required=False)
    received = serializers.DecimalField(max_digits=12,decimal_places=2,required=False)
    expected = serializers.DecimalField(max_digits=12,decimal_places=2,required=False)
    outstanding = serializers.DecimalField(max_digits=12,decimal_places=2,required=False)
    overdue = serializers.DecimalField(max_digits=12,decimal_places=2,required=False)
    categories = serializers.DictField(child=serializers.DecimalField(max_digits=12,decimal_places=2),required=False)
    base = serializers.DecimalField(max_digits=12,decimal_places=2,allow_null=True,required=False)
    final_payout = serializers.DecimalField(max_digits=12,decimal_places=2,allow_null=True,required=False)
    financial_definition = serializers.CharField(required=False)
    commercial_definition = serializers.CharField(required=False)


class PendingDecisionSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    impact = serializers.CharField()


class PoliciesSerializer(serializers.Serializer):
    pending = PendingDecisionSerializer(many=True)
    approved = serializers.ListField(child=serializers.CharField())
    demo = serializers.BooleanField()
    timezone = serializers.CharField()


class DecisionErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField())


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False,max_length=2000)


class EnrollmentCancelSerializer(CancelSerializer):
    effective_on = serializers.DateField(required=False, default=timezone.localdate)
    charge_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, default=list)
    service_unprovided_confirmed = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs['effective_on'] < timezone.localdate():
            raise serializers.ValidationError({'effective_on': 'A data de efeito não pode ser retroativa.'})
        if len(set(attrs['charge_ids'])) != len(attrs['charge_ids']):
            raise serializers.ValidationError({'charge_ids': 'Não repita parcelas.'})
        if attrs['charge_ids'] and not attrs['service_unprovided_confirmed']:
            raise serializers.ValidationError({'service_unprovided_confirmed': 'Confirme que as parcelas selecionadas se referem a serviços não prestados.'})
        return attrs


class SuspensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnrollmentSuspension
        fields = ['id', 'starts_on', 'ends_on', 'reason', 'actor', 'created_at']
        read_only_fields = ['id', 'actor', 'created_at']

    def validate(self, attrs):
        start, end = attrs['starts_on'], attrs['ends_on']
        if start < timezone.localdate():
            raise serializers.ValidationError({'starts_on': 'Suspensão retroativa não é permitida.'})
        if end < start or (end - start).days >= 30:
            raise serializers.ValidationError({'ends_on': 'Informe um período de até 30 dias, contando início e fim.'})
        return attrs


class WaitingListSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)

    class Meta:
        model = WaitingListEntry
        fields = ['id', 'class_group', 'class_name', 'person', 'person_name', 'status', 'actor', 'enrollment', 'created_at']
        read_only_fields = ['id', 'class_name', 'person_name', 'status', 'actor', 'enrollment', 'created_at']
        validators = []


class MessageRequestSerializer(serializers.Serializer):
    recipient = serializers.CharField(max_length=160)
    phone = serializers.RegexField(r'^[1-9][0-9]{9,14}$', max_length=15)


class MessageSentSerializer(serializers.Serializer):
    message = serializers.IntegerField(min_value=1)


class MessageResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    recipient = serializers.CharField()
    phone = serializers.CharField()
    text = serializers.CharField()
    actor = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)
    confirmed_by = serializers.IntegerField(allow_null=True)
    url = serializers.URLField()


class MessageConfirmationSerializer(serializers.Serializer):
    sent_at = serializers.DateTimeField()
