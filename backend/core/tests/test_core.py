from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.apps import apps
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from core.models import AuditEvent, ClassGroup, Instructor, Lead, Modality, Student, User
from core.services import change_access, convert_lead


PASSWORD = "DifferentPassphrase749!"


class CoreFixtures(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(email="admin@example.com", password=PASSWORD, first_name="Gestora", access_status="approved", roles=["coordinator"])
        cls.pending = User.objects.create_user(email="pending@example.com", password=PASSWORD, first_name="Solicitante")
        cls.instructor_user = User.objects.create_user(email="instructor@example.com", password=PASSWORD, first_name="Instrutora", access_status="approved", roles=["instructor"])
        cls.communication = User.objects.create_user(email="com@example.com", password=PASSWORD, access_status="approved", roles=["communication"])
        cls.modality = Modality.objects.create(name="Dança", area="Cultura", default_price="100.00")
        cls.instructor = Instructor.objects.create(name="Instrutora", user=cls.instructor_user, email=cls.instructor_user.email)
        cls.other_instructor = Instructor.objects.create(name="Outro instrutor")
        cls.group = ClassGroup.objects.create(name="Dança manhã", modality=cls.modality, instructor=cls.instructor, weekdays=[0, 2], start_time="09:00", end_time="10:00", room="Sala 1", capacity=20)
        cls.other_group = ClassGroup.objects.create(name="Dança tarde", modality=cls.modality, instructor=cls.other_instructor, weekdays=[0], start_time="14:00", end_time="15:00", room="Sala 1", capacity=20)

    def setUp(self):
        self.client.force_authenticate(self.admin)


class AuthenticationTests(CoreFixtures):
    def test_register_pending_and_sensitive_access_fields_ignored(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/auth/csrf/")
        payload = {"email": "NEW@Example.com", "password": PASSWORD, "first_name": "Nova", "roles": ["coordinator"], "access_status": "approved"}
        self.assertEqual(client.post("/api/auth/register/", payload, format="json").status_code, 403)
        response = client.post("/api/auth/register/", payload, format="json", HTTP_X_CSRFTOKEN=csrf.data["csrfToken"])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["access_status"], "pending")
        self.assertEqual(response.data["roles"], [])
        self.assertEqual(response.data["email"], "new@example.com")
        self.assertNotIn("password", response.data)
        self.assertTrue(AuditEvent.objects.filter(action="access.request", target_id=str(response.data["id"])).exists())

    def test_login_requires_csrf_and_pending_cannot_enter(self):
        client = APIClient(enforce_csrf_checks=True)
        payload = {"email": self.pending.email, "password": PASSWORD}
        self.assertEqual(client.post("/api/auth/login/", payload, format="json").status_code, 403)
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        response = client.post("/api/auth/login/", payload, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["access_status"], "pending")
        self.assertNotIn("_auth_user_id", client.session)

    def test_session_login_rejection_and_logout(self):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        response = client.post("/api/auth/login/", {"email": self.admin.email, "password": PASSWORD}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/students/").status_code, 200)
        self.assertEqual(client.post("/api/auth/logout/", {}, format="json").status_code, 403)
        token = client.get("/api/auth/csrf/").data["csrfToken"]
        self.assertEqual(client.post("/api/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get("/api/students/").status_code, 403)

    def test_case_insensitive_email_is_unique(self):
        response = self.client.post("/api/auth/register/", {"email": self.admin.email.upper(), "password": PASSWORD, "first_name": "Outro"}, format="json")
        self.assertEqual(response.status_code, 400)


class AccessTests(CoreFixtures):
    def test_pending_rejected_and_roleless_accounts_blocked(self):
        for state, roles in [("pending", []), ("rejected", ["coordinator"]), ("approved", [])]:
            self.pending.access_status, self.pending.roles = state, roles
            self.pending.save()
            self.client.force_authenticate(self.pending)
            self.assertEqual(self.client.get("/api/students/").status_code, 403)

    def test_approval_add_remove_and_last_role_revocation(self):
        url = f"/api/users/{self.pending.pk}/"
        self.assertEqual(self.client.post(url + "approve/", {"roles": []}, format="json").status_code, 400)
        response = self.client.post(url + "approve/", {"roles": ["secretary"]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["roles"], ["secretary"])
        self.assertEqual(self.client.post(url + "approve/", {"roles": ["coordinator"]}, format="json").status_code, 409)
        self.assertEqual(self.client.post(url + "add-role/", {"role": "communication"}, format="json").status_code, 200)
        self.assertEqual(self.client.post(url + "remove-role/", {"role": "communication"}, format="json").status_code, 200)
        stale = User.objects.get(pk=self.pending.pk)
        response = self.client.post(url + "remove-role/", {"role": "secretary"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["access_status"], "pending")
        self.client.force_authenticate(stale)
        self.assertEqual(self.client.get("/api/students/").status_code, 403)
        self.assertEqual(AuditEvent.objects.filter(action="access.remove_role", target_id=str(self.pending.pk)).count(), 2)

    def test_self_mutation_refused(self):
        response = self.client.post(f"/api/users/{self.admin.pk}/remove-role/", {"role": "coordinator"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.roles, ["coordinator"])

    def test_rejection_requires_reason_and_invalidates_existing_session(self):
        holder = APIClient()
        holder.force_login(self.instructor_user)
        url = f"/api/users/{self.instructor_user.pk}/reject/"
        self.assertEqual(self.client.post(url, {"reason": " "}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"reason": "Acesso revogado"}, format="json").status_code, 200)
        self.assertEqual(holder.get("/api/classes/").status_code, 403)
        self.assertEqual(holder.get("/api/auth/me/").data["access_status"], "rejected")
        event = AuditEvent.objects.get(action="access.reject", target_id=str(self.instructor_user.pk))
        self.assertEqual(event.actor_id, self.admin.pk)
        self.assertEqual(event.reason, "Acesso revogado")

    def test_instructor_requires_unambiguous_binding(self):
        url = f"/api/users/{self.pending.pk}/approve/"
        self.assertEqual(self.client.post(url, {"roles": ["instructor"]}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"roles": ["instructor"], "instructor_id": self.instructor.pk}, format="json").status_code, 400)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.access_status, "pending")
        response = self.client.post(url, {"roles": ["instructor"], "instructor_id": self.other_instructor.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.other_instructor.refresh_from_db()
        self.assertEqual(self.other_instructor.user_id, self.pending.pk)

    def test_access_audit_failure_rolls_back_authorization(self):
        with patch("core.services.record", side_effect=RuntimeError("Audit unavailable")):
            with self.assertRaises(RuntimeError):
                change_access(self.admin, self.pending.pk, "approve", {"roles": ["secretary"]})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.access_status, "pending")
        self.assertEqual(self.pending.roles, [])

    def test_communication_cannot_manage_leads_or_students(self):
        self.client.force_authenticate(self.communication)
        for resource in ("leads", "students", "users", "instructors", "audit", "modalities", "classes"):
            self.assertEqual(self.client.get(f"/api/{resource}/").status_code, 403, resource)


class StudentTests(CoreFixtures):
    def test_valid_optional_and_normalized_cpf(self):
        response = self.client.post("/api/students/", {"name": "Maria", "cpf": "529.982.247-25"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cpf"], "52998224725")
        self.assertEqual(self.client.post("/api/students/", {"name": "Sem CPF"}, format="json").status_code, 201)
        for value in ("11111111111", "52998224724", "5299822472x", "123"):
            self.assertEqual(self.client.post("/api/students/", {"name": "Inválido", "cpf": value}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/students/", {"name": " "}, format="json").status_code, 400)

    @override_settings(BUSINESS_APPROVALS=[])
    def test_duplicate_proposal_not_assumed_approved(self):
        Student.objects.create(name="Original", cpf="52998224725")
        self.assertEqual(self.client.post("/api/students/", {"name": "Outro", "cpf": "529.982.247-25"}, format="json").status_code, 201)

    @override_settings(BUSINESS_APPROVALS=["RN-013"])
    def test_approved_duplicate_rule_blocks_equivalent_cpfs(self):
        original = Student.objects.create(name="Original", cpf="52998224725")
        response = self.client.post("/api/students/", {"name": "Outro", "cpf": "529.982.247-25"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(self.client.patch(f"/api/students/{original.pk}/", {"cpf": "529.982.247-25"}, format="json").status_code, 200)

    def test_delete_absent_and_archiving_pending_approval(self):
        student = Student.objects.create(name="Histórico")
        url = f"/api/students/{student.pk}/"
        self.assertEqual(self.client.delete(url).status_code, 405)
        response = self.client.patch(url, {"archived": True}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertIn("RN-019", response.data["decisions"])
        with override_settings(BUSINESS_APPROVALS=["RN-019"]):
            self.assertEqual(self.client.patch(url, {"archived": True}, format="json").status_code, 200)
        student.refresh_from_db()
        self.assertTrue(student.archived)
        self.assertTrue(AuditEvent.objects.filter(action="student.update", target_id=str(student.pk)).exists())

    def test_search_filters_order_and_pagination(self):
        Student.objects.create(name="Ana", email="ana@example.com")
        Student.objects.create(name="Bia", archived=True)
        response = self.client.get("/api/students/?search=Ana&archived=false&ordering=name&page_size=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Ana")
        self.assertIn("next", response.data)


class ConversionTests(CoreFixtures):
    def setUp(self):
        super().setUp()
        self.lead = Lead.objects.create(name="Interesse", cpf="52998224725", email="family@example.com", source="Indicação")
        self.url = f"/api/leads/{self.lead.pk}/convert/"

    @override_settings(BUSINESS_APPROVALS=[])
    def test_conversion_waits_for_link_proposal(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertIn("RN-016", response.data["decisions"])
        self.assertEqual(Student.objects.count(), 0)

    @override_settings(BUSINESS_APPROVALS=["RN-016"])
    def test_conversion_is_idempotent_does_not_enroll_and_preserves_history(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        second = self.client.post(self.url, {}, format="json")
        self.assertEqual(second.data["student"], response.data["student"])
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(response.data["status"], "converted")
        self.assertEqual(AuditEvent.objects.filter(action="lead.convert").count(), 1)
        if apps.is_installed("billing"):
            self.assertEqual(apps.get_model("billing", "Enrollment").objects.count(), 0)

    @override_settings(BUSINESS_APPROVALS=["RN-016"])
    def test_unique_match_reuses_student(self):
        student = Student.objects.create(name="Já cadastrado", cpf=self.lead.cpf)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["student"], student.pk)
        self.assertEqual(Student.objects.count(), 1)

    @override_settings(BUSINESS_APPROVALS=["RN-016"])
    def test_identity_conflict_requires_explicit_student_and_reason(self):
        cpf_student = Student.objects.create(name="CPF", cpf=self.lead.cpf)
        email_student = Student.objects.create(name="E-mail", email=self.lead.email)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 409)
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.student_id)
        self.assertEqual(self.client.post(self.url, {"student_id": cpf_student.pk}, format="json").status_code, 400)
        response = self.client.post(self.url, {"student_id": cpf_student.pk, "reason": "Documento conferido presencialmente"}, format="json")
        self.assertEqual(response.status_code, 200)
        event = AuditEvent.objects.get(action="lead.convert")
        self.assertEqual(event.metadata["candidate_ids"], sorted([cpf_student.pk, email_student.pk]))
        self.assertTrue(event.metadata["identity_resolved"])

    @override_settings(BUSINESS_APPROVALS=["RN-016"])
    def test_shared_email_is_not_unique_identity(self):
        Student.objects.create(name="Pessoa A", email=self.lead.email)
        Student.objects.create(name="Pessoa B", email=self.lead.email)
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 409)

    @override_settings(BUSINESS_APPROVALS=["RN-016"])
    def test_failed_audit_rolls_back_student_and_conversion(self):
        with patch("core.services.record", side_effect=RuntimeError("Audit unavailable")):
            with self.assertRaises(RuntimeError):
                convert_lead(self.admin, self.lead.pk, {})
        self.lead.refresh_from_db()
        self.assertIsNone(self.lead.student_id)
        self.assertEqual(self.lead.status, "new")
        self.assertEqual(Student.objects.count(), 0)

    def test_cannot_bypass_conversion_by_patching_status(self):
        response = self.client.patch(f"/api/leads/{self.lead.pk}/", {"status": "converted"}, format="json")
        self.assertEqual(response.status_code, 400)


class ClassScopeTests(CoreFixtures):
    def test_instructor_only_sees_own_classes_and_cannot_reassign(self):
        self.client.force_authenticate(self.instructor_user)
        response = self.client.get("/api/classes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.group.pk])
        self.assertEqual(self.client.get(f"/api/classes/{self.other_group.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/classes/{self.group.pk}/", {"instructor": self.other_instructor.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.get("/api/students/").status_code, 403)

    def test_valid_schedule_required(self):
        url = f"/api/classes/{self.group.pk}/"
        self.assertEqual(self.client.patch(url, {"end_time": "08:30"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"weekdays": [0, 0]}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"weekdays": [True]}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"capacity": 0}, format="json").status_code, 400)


@skipUnless(connection.vendor == "postgresql", "Row-lock concurrency is validated against PostgreSQL, not SQLite.")
@override_settings(BUSINESS_APPROVALS=["RN-013", "RN-016"])
class PostgreSQLConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.admins = [User.objects.create_user(email=f"admin{i}@example.com", password=PASSWORD, access_status="approved", roles=["coordinator"]) for i in range(2)]

    def _parallel(self, callable_factory):
        barrier = Barrier(2)

        def worker(index):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=self.admins[index].pk))
                barrier.wait(timeout=10)
                return callable_factory(client, index)
            finally:
                # Test workers are short lived; close healthy connections too.
                # close_old_connections alone leaves CONN_MAX_AGE sessions alive
                # and PostgreSQL cannot drop the isolated test database.
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_concurrent_cpf_creation_has_one_winner(self):
        statuses = self._parallel(lambda client, index: client.post("/api/students/", {"name": f"Aluno {index}", "cpf": "529.982.247-25"}, format="json").status_code)
        self.assertEqual(sorted(statuses), [201, 400])
        self.assertEqual(Student.objects.count(), 1)

    def test_concurrent_conversion_creates_one_student(self):
        lead = Lead.objects.create(name="Conversão", cpf="52998224725")
        statuses = self._parallel(lambda client, index: client.post(f"/api/leads/{lead.pk}/convert/", {}, format="json").status_code)
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(AuditEvent.objects.filter(action="lead.convert").count(), 1)

    def test_concurrent_approval_cannot_silently_replace_decision(self):
        target = User.objects.create_user(email="request@example.com", password=PASSWORD)
        statuses = self._parallel(lambda client, index: client.post(f"/api/users/{target.pk}/approve/", {"roles": [["secretary"], ["communication"]][index]}, format="json").status_code)
        self.assertEqual(sorted(statuses), [200, 409])
        self.assertEqual(AuditEvent.objects.filter(action="access.approve", target_id=str(target.pk)).count(), 1)

    def test_concurrent_partial_updates_preserve_distinct_fields(self):
        student = Student.objects.create(name="Original")
        payloads = [{"phone": "11999990000"}, {"email": "updated@example.com"}]
        statuses = self._parallel(lambda client, index: client.patch(f"/api/students/{student.pk}/", payloads[index], format="json").status_code)
        self.assertEqual(statuses, [200, 200])
        student.refresh_from_db()
        self.assertEqual(student.phone, "11999990000")
        self.assertEqual(student.email, "updated@example.com")
