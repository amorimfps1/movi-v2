from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AuditEvent, ClassGroup, ContactPreference, Instructor, Lead, Modality, Person, User
from .permissions import ROLES
from .policies import DecisionRequired, approved
from .validators import normalize_cpf, validate_weekdays


class CPFSerializerField(serializers.CharField):
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return normalize_cpf(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "access_status", "roles", "is_active"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este e-mail já possui uma solicitação.")
        return value

    def validate(self, attrs):
        candidate = User(email=attrs["email"], first_name=attrs["first_name"], last_name=attrs.get("last_name", ""))
        try:
            password_validation.validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class AccessRolesSerializer(serializers.Serializer):
    roles = serializers.ListField(child=serializers.ChoiceField(choices=sorted(ROLES)), allow_empty=False)
    instructor_id = serializers.IntegerField(min_value=1, required=False)

    def validate_roles(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("As funções não podem se repetir.")
        return value


class AccessRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=sorted(ROLES))
    instructor_id = serializers.IntegerField(min_value=1, required=False)
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, max_length=2000)


class PersonSerializer(serializers.ModelSerializer):
    cpf = CPFSerializerField(required=False, allow_blank=True, max_length=18)

    class Meta:
        model = Person
        fields = ["id", "name", "cpf", "email", "phone", "birth_date", "address", "notes", "archived", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_cpf(self, value):
        if value:
            matches = Person.objects.filter(cpf=value)
            if self.instance:
                matches = matches.exclude(pk=self.instance.pk)
            if matches.exists():
                raise serializers.ValidationError("Já existe um aluno com este CPF.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.archived and attrs.get("archived") is False:
            raise DecisionRequired("A reabertura de um aluno arquivado exige política institucional.", ["DN-021"])
        return attrs


class ModalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Modality
        fields = ["id", "name", "area", "default_price", "active", "price_category", "enrollment_fee_kind"]


class InstructorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instructor
        fields = ["id", "name", "email", "phone", "active", "specialties", "user"]
        read_only_fields = ["user"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_specialties(self, value):
        if self.instance:
            selected = {modality.pk for modality in value}
            if self.instance.classes.filter(active=True).exclude(modality_id__in=selected).exists():
                raise serializers.ValidationError('Há turmas ativas vinculadas a modalidades removidas das especialidades.')
        return value


class ClassGroupSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.name", read_only=True)
    modality_name = serializers.CharField(source="modality.name", read_only=True)

    class Meta:
        model = ClassGroup
        fields = ["id", "name", "modality", "modality_name", "instructor", "instructor_name", "weekdays", "start_time", "end_time", "room", "age_range", "capacity", "physical_capacity", "active", "allows_trial"]

    def validate_weekdays(self, value):
        try:
            validate_weekdays(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value

    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "O término deve ser posterior ao início."})
        capacity = attrs.get('capacity', getattr(self.instance, 'capacity', None))
        physical = attrs.get('physical_capacity', getattr(self.instance, 'physical_capacity', None))
        if physical is not None and capacity is not None and physical < capacity:
            raise serializers.ValidationError({'physical_capacity': 'O limite físico não pode ser inferior à capacidade regular.'})
        if self.instance and 'modality' in attrs and attrs['modality'].pk != self.instance.modality_id and self.instance.lessons.filter(trials__isnull=False).exists():
            raise serializers.ValidationError({'modality': 'Turma com experimentais registradas não pode trocar de modalidade; crie outra turma.'})
        changed = not self.instance or bool(set(attrs) & {'start_time', 'end_time', 'weekdays', 'room', 'instructor', 'modality', 'active'})
        active = attrs.get('active', getattr(self.instance, 'active', True))
        if changed and active:
            instructor = attrs.get('instructor', getattr(self.instance, 'instructor', None))
            modality = attrs.get('modality', getattr(self.instance, 'modality', None))
            weekdays = set(attrs.get('weekdays', getattr(self.instance, 'weekdays', [])))
            room = attrs.get('room', getattr(self.instance, 'room', '')).strip()
            if instructor and modality and not instructor.specialties.filter(pk=modality.pk).exists():
                raise serializers.ValidationError({'instructor': 'O instrutor precisa ter a modalidade entre suas especialidades.'})
            candidates = ClassGroup.objects.filter(active=True, start_time__lt=end, end_time__gt=start)
            if self.instance:
                candidates = candidates.exclude(pk=self.instance.pk)
            for other in candidates:
                if weekdays.intersection(other.weekdays):
                    if instructor and other.instructor_id == instructor.pk:
                        raise serializers.ValidationError({'instructor': 'O instrutor já possui turma no mesmo horário.'})
                    if room and other.room.strip().casefold() == room.casefold():
                        raise serializers.ValidationError({'room': 'A sala já está ocupada neste horário.'})
        return attrs


class LeadSerializer(serializers.ModelSerializer):
    cpf = CPFSerializerField(required=False, allow_blank=True, max_length=18)

    class Meta:
        model = Lead
        fields = ["id", "name", "cpf", "email", "phone", "source", "status", "interests", "notes", "student", "created_at"]
        read_only_fields = ["student", "created_at"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate_status(self, value):
        if value == "converted" and (not self.instance or self.instance.status != "converted"):
            raise serializers.ValidationError("Utilize a ação de conversão para identificar o aluno.")
        if self.instance and self.instance.status == "converted" and value != "converted":
            raise DecisionRequired("Desfazer uma conversão depende de política institucional.", ["DN-003", "DN-019"])
        if self.instance and self.instance.status == "not_converted" and value not in {"not_converted", "converted"}:
            raise DecisionRequired("Reabrir acompanhamento depende de política institucional.", ["DN-019"])
        return value


class CommercialLeadSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    whatsapp = serializers.SerializerMethodField()

    def _allowed(self, obj, channel):
        preference = next((item for item in obj.contact_preferences.all() if item.channel == channel and item.purpose == 'commercial'), None)
        return bool(preference and preference.allowed)

    def get_email(self, obj) -> str:
        return obj.email if self._allowed(obj, 'email') else ''

    def get_phone(self, obj) -> str:
        return obj.phone if self._allowed(obj, 'phone') else ''

    def get_whatsapp(self, obj) -> str:
        return obj.phone if self._allowed(obj, 'whatsapp') else ''

    class Meta:
        model = Lead
        fields = ['id', 'name', 'email', 'phone', 'whatsapp', 'source', 'status', 'created_at']
        read_only_fields = fields


class ContactPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactPreference
        fields = ['id', 'person', 'lead', 'channel', 'purpose', 'allowed', 'actor', 'created_at']
        read_only_fields = ['id', 'actor', 'created_at']

    def validate(self, attrs):
        if bool(attrs.get('person')) == bool(attrs.get('lead')):
            raise serializers.ValidationError('Informe uma pessoa ou um lead.')
        return attrs


class ConvertSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(min_value=1, required=False)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=False)


class AuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = ["id", "actor", "actor_name", "action", "target_type", "target_id", "reason", "metadata", "created_at"]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str:
        return obj.actor.get_full_name() or obj.actor.email if obj.actor else "Sistema"
