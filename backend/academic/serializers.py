from rest_framework import serializers

from .models import Lesson


class LessonSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source="class_group.name", read_only=True)
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id", "name", "class_group", "class_name", "date", "assigned_instructor",
            "instructor_name", "status", "notes", "created_at",
        ]
        read_only_fields = ["id", "name", "class_name", "instructor_name", "created_at"]
        # UniqueConstraint is enforced inside the locked transaction too.
        validators = []

    def get_name(self, obj) -> str:
        return f"{obj.class_group.name} — {obj.date:%d/%m/%Y}"

    def get_instructor_name(self, obj) -> str:
        instructor = obj.assigned_instructor or obj.class_group.instructor
        return instructor.name

    def validate_status(self, value):
        if value == Lesson.Status.COMPLETED:
            raise serializers.ValidationError("A aula só pode ser realizada pela confirmação atômica da chamada.")
        return value


class AttendanceMarkSerializer(serializers.Serializer):
    enrollment = serializers.IntegerField(min_value=1)
    present = serializers.BooleanField()

    def to_internal_value(self, data):
        # Avoid accepting strings, 0/1 and missing fields as attendance decisions.
        if not isinstance(data, dict) or type(data.get("present")) is not bool:
            raise serializers.ValidationError({"present": "Informe presença como true ou false."})
        if type(data.get("enrollment")) is not int:
            raise serializers.ValidationError({"enrollment": "Informe o identificador inteiro da matrícula."})
        return super().to_internal_value(data)


class AttendanceSubmissionSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=512)
    marks = AttendanceMarkSerializer(many=True, allow_empty=True)

    def validate_marks(self, marks):
        identifiers = [mark["enrollment"] for mark in marks]
        if len(identifiers) != len(set(identifiers)):
            raise serializers.ValidationError("Cada matrícula deve possuir exatamente uma marcação.")
        return marks


class RosterParticipantSerializer(serializers.Serializer):
    enrollment = serializers.IntegerField()
    student_name = serializers.CharField()


class RosterExcludedSerializer(serializers.Serializer):
    enrollment = serializers.IntegerField()
    reason = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField())


class RosterSerializer(serializers.Serializer):
    lesson = serializers.IntegerField()
    version = serializers.CharField()
    participants = RosterParticipantSerializer(many=True)
    excluded = RosterExcludedSerializer(many=True)
    decisions = serializers.ListField(child=serializers.CharField())


class DecisionResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    decisions = serializers.ListField(child=serializers.CharField())


class AttendanceHistoryMarkSerializer(serializers.Serializer):
    enrollment = serializers.IntegerField()
    student_name = serializers.CharField()
    present = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class AttendanceHistorySerializer(serializers.Serializer):
    lesson = serializers.IntegerField()
    status = serializers.CharField()
    marks = AttendanceHistoryMarkSerializer(many=True)
    definition = serializers.CharField()
