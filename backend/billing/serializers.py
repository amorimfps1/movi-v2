from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Enrollment, Charge, Payment, CommercialCondition
from .services import DecisionRequired, evaluate_eligibility


class EligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField(allow_null=True)
    status = serializers.CharField()
    reason = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField())


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    class_name = serializers.CharField(source='class_group.name', read_only=True)
    eligibility = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id','student','class_group','student_name','class_name','start_date','plan','amount',
                  'administrative_status','kind','created_at','eligibility']
        read_only_fields = ['administrative_status','created_at']

    @extend_schema_field(EligibilitySerializer)
    def get_eligibility(self, obj):
        return evaluate_eligibility(obj)

    def validate(self, attrs):
        if attrs.get('kind') == 'trial':
            raise DecisionRequired('Experimental aguarda política detalhada de duração, quantidade e condições.', ['DN-013'])
        student = attrs.get('student', getattr(self.instance, 'student', None))
        group = attrs.get('class_group', getattr(self.instance, 'class_group', None))
        if student and student.archived:
            raise serializers.ValidationError({'student': 'Aluno arquivado.'})
        if group and not group.active:
            raise serializers.ValidationError({'class_group': 'Turma inativa.'})
        return attrs


class ChargeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)
    class_name = serializers.CharField(source='enrollment.class_group.name', read_only=True)
    received = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Charge
        fields = ['id','enrollment','category','competence','due_date','amount','description',
                  'student_name','class_name','received','status','created_at']
        read_only_fields = ['created_at']

    def validate(self, attrs):
        if attrs['category'] == 'tuition':
            competence = attrs.get('competence')
            if not competence or competence.day != 1:
                raise serializers.ValidationError({'competence': 'Informe o primeiro dia da competência (AAAA-MM-01).'})
        return attrs


class ReceiptSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    paid_on = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment._meta.get_field('method').choices)
    reference = serializers.CharField(max_length=160, required=False, allow_blank=True)

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
    class Meta:
        model = CommercialCondition
        fields = ['id','enrollment','amount','effective_on','plan','actor','reason','created_at']


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
