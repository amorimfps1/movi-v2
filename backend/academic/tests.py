"""Academic acceptance checks.

ATTENDANCE_POLICY and mocked eligibility below are technical fixtures, never an
institutional approval. The operational default stays blocked by DN-014/DN-004.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from billing.models import Charge, Enrollment, Payment
from core.models import AuditEvent, ClassGroup, Instructor, Modality, Student, User

from .models import Attendance, Lesson


TECHNICAL_POLICY = {
    "marking": "presence_absence", "eligibility_date": "lesson_date",
    "allow_past": False, "allow_future": False, "allow_empty": False,
}
ELIGIBLE = {"eligible": True, "status": "eligible", "reason": "Cenário técnico", "decisions": []}


class AcademicFixtures:
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(email="secretaria@example.test", password="only-test-secret", access_status="approved", roles=["secretary"])
        self.teacher_user = User.objects.create_user(email="titular@example.test", password="only-test-secret", access_status="approved", roles=["instructor"])
        self.substitute_user = User.objects.create_user(email="substituto@example.test", password="only-test-secret", access_status="approved", roles=["instructor"])
        self.other_user = User.objects.create_user(email="outro@example.test", password="only-test-secret", access_status="approved", roles=["instructor"])
        self.teacher = Instructor.objects.create(name="Instrutor titular", user=self.teacher_user)
        self.substitute = Instructor.objects.create(name="Instrutor substituto", user=self.substitute_user)
        self.other = Instructor.objects.create(name="Outro instrutor", user=self.other_user)
        self.modality = Modality.objects.create(name="Música", default_price=Decimal("100.00"))
        self.group = ClassGroup.objects.create(name="Música terça", modality=self.modality, instructor=self.teacher, weekdays=[1], start_time="10:00", end_time="11:00", room="Sala 1", capacity=20)
        self.other_group = ClassGroup.objects.create(name="Música quarta", modality=self.modality, instructor=self.other, weekdays=[2], start_time="10:00", end_time="11:00", room="Sala 2", capacity=20)
        self.today = timezone.localdate()
        self.lesson = Lesson.objects.create(class_group=self.group, date=self.today)
        self.other_lesson = Lesson.objects.create(class_group=self.other_group, date=self.today)
        self.students = [Student.objects.create(name=f"Participante teste {n}") for n in (1, 2)]
        self.enrollments = [Enrollment.objects.create(student=student, class_group=self.group, start_date=self.today, plan="monthly", amount=Decimal("100.00")) for student in self.students]
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def roster(self, lesson=None):
        return self.client.get(f"/api/lessons/{(lesson or self.lesson).pk}/roster/")

    def submit(self, payload=None, marks=None, lesson=None):
        if payload is None:
            response = self.roster(lesson)
            self.assertEqual(response.status_code, 200, response.data)
            payload = response.data
        if marks is None:
            marks = [{"enrollment": item["enrollment"], "present": True} for item in payload["participants"]]
        return self.client.post(f"/api/lessons/{(lesson or self.lesson).pk}/attendance/", {"version": payload["version"], "marks": marks}, format="json")

    def stored_history(self):
        """Historical fixture, not a policy enabling new attendance writes."""
        self.lesson.status = "completed"
        self.lesson.save(update_fields=["status"])
        for index, enrollment in enumerate(self.enrollments):
            Attendance.objects.create(lesson=self.lesson, enrollment=enrollment, present=index == 0, actor=self.admin)

    def history(self, lesson=None):
        return self.client.get(f"/api/lessons/{(lesson or self.lesson).pk}/attendance/")


@override_settings(BUSINESS_APPROVALS=[], ATTENDANCE_POLICY=None,
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AcademicDefaultTests(AcademicFixtures, APITestCase):
    def test_scheduled_lesson_has_empty_readonly_attendance_history(self):
        response = self.history()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["lesson"], self.lesson.pk)
        self.assertEqual(response.data["status"], "scheduled")
        self.assertEqual(response.data["marks"], [])
        self.assertEqual(response.data["definition"], "Marcações gravadas na conclusão; não recalculadas pela elegibilidade atual.")

    def test_own_attendance_history_is_visible_without_financial_or_actor_data(self):
        self.stored_history()
        self.client.force_authenticate(self.teacher_user)
        response = self.history()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual([mark["present"] for mark in response.data["marks"]], [True, False])
        for mark, student, enrollment in zip(response.data["marks"], self.students, self.enrollments):
            self.assertEqual(set(mark), {"enrollment", "student_name", "present", "created_at"})
            self.assertEqual(mark["student_name"], student.name)
            self.assertEqual(mark["enrollment"], enrollment.pk)
            self.assertTrue(mark["created_at"])

    def test_substitute_can_read_only_assigned_lesson_history(self):
        self.lesson.assigned_instructor = self.substitute
        self.lesson.save(update_fields=["assigned_instructor"])
        self.stored_history()
        adjacent = Lesson.objects.create(class_group=self.group, date=self.today + timedelta(days=1))
        self.client.force_authenticate(self.substitute_user)
        self.assertEqual(self.history().status_code, 200)
        self.assertEqual(self.history(adjacent).status_code, 404)
        self.assertEqual(self.history(self.other_lesson).status_code, 404)

    def test_third_party_cannot_read_attendance_history(self):
        self.stored_history()
        self.client.force_authenticate(self.other_user)
        self.assertEqual(self.history().status_code, 404)

    @patch("academic.services.evaluate_eligibility", side_effect=AssertionError("Histórico não deve recalcular elegibilidade"))
    def test_attendance_history_preserves_recorded_marks_after_financial_change(self, mocked):
        self.stored_history()
        original = self.history().data
        Enrollment.objects.filter(pk=self.enrollments[0].pk).update(administrative_status="cancelled")
        Charge.objects.create(enrollment=self.enrollments[1], category="tuition", competence=self.today.replace(day=1), due_date=self.today - timedelta(days=1), amount="100.00")
        response = self.history()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, original)
        mocked.assert_not_called()
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), 2)

    def test_revoked_user_cannot_read_old_attendance_history(self):
        self.stored_history()
        self.client.force_authenticate(self.teacher_user)
        User.objects.filter(pk=self.teacher_user.pk).update(access_status="pending", roles=[])
        self.assertEqual(self.history().status_code, 403)

    def test_pending_rejected_and_revoked_users_have_no_access(self):
        for status, roles in [("pending", []), ("rejected", []), ("approved", [])]:
            User.objects.filter(pk=self.admin.pk).update(access_status=status, roles=roles)
            response = self.client.get("/api/lessons/")
            self.assertEqual(response.status_code, 403)

    def test_substitution_grants_only_specific_lesson(self):
        self.lesson.assigned_instructor = self.substitute
        self.lesson.save()
        adjacent = Lesson.objects.create(class_group=self.group, date=self.today + timedelta(days=1))
        self.client.force_authenticate(self.substitute_user)
        response = self.client.get("/api/lessons/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [self.lesson.pk])
        self.assertEqual(self.client.get(f"/api/lessons/{adjacent.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/lessons/{self.other_lesson.pk}/roster/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/classes/{self.group.pk}/").status_code, 404)

    def test_instructor_cannot_transfer_or_create_lesson(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.client.patch(f"/api/lessons/{self.lesson.pk}/", {"assigned_instructor": self.substitute.pk}, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.client.post("/api/lessons/", {"class_group": self.group.pk, "date": str(self.today + timedelta(days=1))}, format="json")
        self.assertEqual(response.status_code, 403)
        self.lesson.refresh_from_db()
        self.assertIsNone(self.lesson.assigned_instructor_id)

    def test_communication_cannot_read_diary(self):
        communication = User.objects.create_user(email="comunicacao@example.test", password="only-test-secret", access_status="approved", roles=["communication"])
        self.client.force_authenticate(communication)
        self.assertEqual(self.client.get("/api/lessons/").data["count"], 0)
        self.assertEqual(self.roster().status_code, 404)

    def test_inactive_professional_does_not_retain_diary_scope(self):
        self.client.force_authenticate(self.teacher_user)
        Instructor.objects.filter(pk=self.teacher.pk).update(active=False)
        self.assertEqual(self.client.get("/api/lessons/").data["count"], 0)
        self.assertEqual(self.roster().status_code, 404)

    def test_lesson_unique_class_date_in_api_and_database(self):
        response = self.client.post("/api/lessons/", {"class_group": self.group.pk, "date": str(self.today)}, format="json")
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lesson.objects.create(class_group=self.group, date=self.today)
        self.assertEqual(Lesson.objects.filter(class_group=self.group, date=self.today).count(), 1)

    def test_admin_creates_and_assigns_lesson_with_audit(self):
        response = self.client.post("/api/lessons/", {"class_group": self.group.pk, "date": str(self.today + timedelta(days=1)), "assigned_instructor": self.substitute.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["instructor_name"], self.substitute.name)
        self.assertTrue(AuditEvent.objects.filter(action="lesson.created", target_id=str(response.data["id"])).exists())

    def test_completed_status_cannot_be_set_by_patch(self):
        response = self.client.patch(f"/api/lessons/{self.lesson.pk}/", {"status": "completed"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "scheduled")

    def test_no_physical_delete(self):
        self.assertEqual(self.client.delete(f"/api/lessons/{self.lesson.pk}/").status_code, 405)
        self.assertTrue(Lesson.objects.filter(pk=self.lesson.pk).exists())

    def test_unknown_eligibility_is_explicit_and_does_not_enter_roster(self):
        response = self.roster()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["participants"], [])
        self.assertEqual(len(response.data["excluded"]), 2)
        self.assertIn("DN-004", response.data["decisions"])
        self.assertIn("DN-014", response.data["decisions"])

    def test_instructor_receives_no_personal_or_financial_exclusion_details(self):
        self.client.force_authenticate(self.teacher_user)
        response = self.roster()
        self.assertEqual(response.status_code, 200)
        for item in response.data["excluded"]:
            self.assertEqual(set(item), {"enrollment", "reason", "decisions"})
            self.assertEqual(item["reason"], "Participação indisponível. Consulte a secretaria.")
        detail = self.client.get(f"/api/lessons/{self.lesson.pk}/").data
        self.assertNotIn("amount", detail)
        self.assertNotIn("charges", detail)

    def test_default_attendance_is_blocked_even_empty_or_retroactive(self):
        for offset in [0, -1]:
            self.lesson.date = self.today + timedelta(days=offset)
            self.lesson.save()
            response = self.submit()
            self.assertEqual(response.status_code, 409, response.data)
            self.assertIn("DN-014", response.data["decisions"])
        self.assertFalse(Attendance.objects.exists())
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "scheduled")

    @override_settings(BUSINESS_APPROVALS=["DN-014"])
    def test_approval_id_without_detailed_policy_does_not_unblock(self):
        self.assertEqual(self.submit().status_code, 409)
        self.assertFalse(Attendance.objects.exists())

    @override_settings(BUSINESS_APPROVALS=["DN-014"], ATTENDANCE_POLICY={**TECHNICAL_POLICY, "allow_future": True})
    def test_unsupported_policy_is_explicit_in_roster_and_blocks_submission(self):
        payload = self.roster().data
        self.assertIn("DN-014", payload["decisions"])
        self.assertEqual(self.submit(payload).status_code, 409)
        self.assertFalse(Attendance.objects.exists())

    def test_paid_tuition_does_not_become_eternal_coverage_in_roster(self):
        charge = Charge.objects.create(enrollment=self.enrollments[0], category="tuition", competence=self.today.replace(day=1), due_date=self.today, amount="100.00")
        Payment.objects.create(charge=charge, amount="100.00", paid_on=self.today, method="pix", actor=self.admin)
        response = self.roster()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["participants"], [])
        self.assertIn("DN-004", response.data["decisions"])


@override_settings(BUSINESS_APPROVALS=["DN-014"], ATTENDANCE_POLICY=TECHNICAL_POLICY,
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AcademicTechnicalEngineTests(AcademicFixtures, APITestCase):
    """Prove safeguards with approved-policy/eligibility fixtures only."""

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_exact_attendance_and_completion_are_recorded_together(self, mocked):
        response = self.submit(marks=[{"enrollment": self.enrollments[0].pk, "present": True}, {"enrollment": self.enrollments[1].pk, "present": False}])
        self.assertEqual(response.status_code, 200, response.data)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "completed")
        self.assertEqual(list(Attendance.objects.filter(lesson=self.lesson).values_list("present", flat=True)), [True, False])
        self.assertTrue(AuditEvent.objects.filter(action="attendance.completed", target_id=str(self.lesson.pk)).exists())
        mocked.assert_any_call(self.enrollments[0], on=self.today)

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_incomplete_duplicate_and_extra_marks_are_refused(self, mocked):
        payload = self.roster().data
        samples = [[], [{"enrollment": self.enrollments[0].pk, "present": True}],
                   [{"enrollment": self.enrollments[0].pk, "present": True}] * 2,
                   [{"enrollment": enrollment.pk, "present": True} for enrollment in self.enrollments] + [{"enrollment": 99999, "present": True}]]
        for marks in samples:
            response = self.submit(payload, marks)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertFalse(Attendance.objects.exists())
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "scheduled")

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_mark_values_require_explicit_booleans(self, mocked):
        payload = self.roster().data
        for value in ["false", 0, 1, None, "present"]:
            response = self.submit(payload, [{"enrollment": self.enrollments[0].pk, "present": value}])
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_new_enrollment_requires_roster_refresh(self, mocked):
        payload = self.roster().data
        Enrollment.objects.create(student=self.students[0], class_group=self.group, start_date=self.today, plan="monthly", amount="100.00")
        response = self.submit(payload)
        self.assertEqual(response.status_code, 409, response.data)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_eligibility_change_requires_roster_refresh(self, mocked):
        payload = self.roster().data
        mocked.return_value = {"eligible": False, "status": "blocked", "reason": "Cenário técnico de bloqueio", "decisions": []}
        self.assertEqual(self.submit(payload).status_code, 409)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_assignment_is_revalidated_and_titular_cannot_confirm_substitution(self, mocked):
        self.client.force_authenticate(self.teacher_user)
        payload = self.roster().data
        Lesson.objects.filter(pk=self.lesson.pk).update(assigned_instructor=self.substitute)
        self.assertEqual(self.submit(payload).status_code, 403)
        self.assertFalse(Attendance.objects.exists())
        self.client.force_authenticate(self.substitute_user)
        self.assertEqual(self.submit().status_code, 200)

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_revoked_role_is_revalidated(self, mocked):
        self.client.force_authenticate(self.teacher_user)
        payload = self.roster().data
        User.objects.filter(pk=self.teacher_user.pk).update(access_status="pending", roles=[])
        self.assertEqual(self.submit(payload).status_code, 403)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_inactivated_professional_cannot_confirm_old_roster(self, mocked):
        self.client.force_authenticate(self.teacher_user)
        payload = self.roster().data
        Instructor.objects.filter(pk=self.teacher.pk).update(active=False)
        self.assertEqual(self.submit(payload).status_code, 404)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_failure_after_insert_rolls_back_attendance_lesson_and_audit(self, mocked):
        payload = self.roster().data
        with patch("academic.services.record", side_effect=RuntimeError("Falha técnica controlada")):
            with self.assertRaises(RuntimeError):
                self.submit(payload)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "scheduled")
        self.assertFalse(Attendance.objects.exists())
        self.assertFalse(AuditEvent.objects.filter(action="attendance.completed").exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_repeated_submission_and_edits_to_completed_lesson_are_refused(self, mocked):
        payload = self.roster().data
        self.assertEqual(self.submit(payload).status_code, 200)
        self.assertEqual(self.submit(payload).status_code, 409)
        response = self.client.patch(f"/api/lessons/{self.lesson.pk}/", {"notes": "Alteração"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Attendance.objects.count(), 2)

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_tampered_or_other_actor_roster_token_is_refused(self, mocked):
        payload = self.roster().data
        tampered = {**payload, "version": payload["version"] + "bad"}
        self.assertEqual(self.submit(tampered).status_code, 409)
        self.client.force_authenticate(self.teacher_user)
        self.assertEqual(self.submit(payload).status_code, 409)
        self.assertFalse(Attendance.objects.exists())

    def test_unresolved_financial_eligibility_blocks_even_technical_policy(self):
        response = self.submit()
        self.assertEqual(response.status_code, 409, response.data)
        self.assertIn("DN-004", response.data["decisions"])
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_cancelled_past_future_and_empty_lessons_remain_unavailable(self, mocked):
        self.lesson.status = "cancelled"
        self.lesson.save()
        self.assertEqual(self.submit().status_code, 409)
        self.lesson.status = "scheduled"
        for offset in [-1, 1]:
            self.lesson.date = self.today + timedelta(days=offset)
            self.lesson.save()
            self.assertEqual(self.submit().status_code, 409)
        self.lesson.date = self.today
        self.lesson.save()
        mocked.return_value = {"eligible": False, "status": "pending", "reason": "Cenário técnico", "decisions": []}
        self.assertEqual(self.submit().status_code, 409)
        self.assertFalse(Attendance.objects.exists())

    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_database_attendance_uniqueness(self, mocked):
        Attendance.objects.create(lesson=self.lesson, enrollment=self.enrollments[0], present=True, actor=self.admin)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Attendance.objects.create(lesson=self.lesson, enrollment=self.enrollments[0], present=False, actor=self.admin)


@override_settings(BUSINESS_APPROVALS=["DN-014"], ATTENDANCE_POLICY=TECHNICAL_POLICY,
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AcademicPostgreSQLConcurrencyTests(AcademicFixtures, TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    @patch("academic.services.evaluate_eligibility", return_value=ELIGIBLE)
    def test_simultaneous_submissions_create_one_complete_set(self, mocked):
        payload = self.roster().data
        barrier = Barrier(2)
        def submit_from_connection():
            close_old_connections()
            try:
                user = User.objects.get(pk=self.admin.pk)
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait(timeout=15)
                result = client.post(f"/api/lessons/{self.lesson.pk}/attendance/", {
                    "version": payload["version"],
                    "marks": [{"enrollment": enrollment.pk, "present": True} for enrollment in self.enrollments],
                }, format="json")
                return result.status_code
            finally:
                # Worker connections must be closed even with CONN_MAX_AGE>0,
                # otherwise PostgreSQL refuses to drop the test database.
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit_from_connection) for _ in range(2)]
            statuses = sorted(future.result(timeout=30) for future in futures)
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), 2)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.status, "completed")
