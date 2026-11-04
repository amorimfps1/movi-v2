from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import AuditEvent, Condominium, CondominiumAssociation, Person, ResidenceVerification, Student, User


class EcoWorkFoundationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.operator = User.objects.create_user(email="eco@example.test", password="test-password", access_status="approved", roles=["secretary"])
        cls.person = Student.objects.create(name="Moradora existente")
        cls.condominium = Condominium.objects.create(name="Condomínio de teste")

    def setUp(self):
        self.client.force_authenticate(self.operator)

    def associate(self):
        response = self.client.post("/api/condominium-associations/", {
            "condominium": self.condominium.pk,
            "starts_on": (timezone.localdate() - timedelta(days=10)).isoformat(),
        })
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def verify(self, **changes):
        payload = {"person": self.person.pk, "condominium": self.condominium.pk, "declared": True, "proof_checked": True}
        return self.client.post("/api/residence-verifications/", {**payload, **changes})

    def quote(self, product):
        response = self.client.post("/api/ecowork/quote/", {"person": self.person.pk, "product": product})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_people_share_identity_and_history_with_academic_api(self):
        self.assertIs(Person, Student)
        response = self.client.patch(f"/api/people/{self.person.pk}/", {"phone": "11999999999"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(f"/api/students/{self.person.pk}/").data["phone"], "11999999999")
        self.assertTrue(AuditEvent.objects.filter(target_type="core.student", target_id=str(self.person.pk), action="student.update").exists())
        created = self.client.post("/api/people/", {"name": "Somente EcoWork"})
        self.assertEqual(created.status_code, 201)
        self.assertFalse(Person.objects.get(pk=created.data["id"]).enrollments.exists())

    def test_catalog_prices_and_limits(self):
        response = self.client.get("/api/ecowork/products/")
        self.assertEqual(response.status_code, 200)
        products = {item["code"]: item for item in response.data}
        self.assertEqual({code: item["price"] for code, item in products.items()}, {
            "hour": "5.00", "half_day": "15.00", "day": "25.00", "monthly": "169.00", "semiannual": "699.00", "annual": "969.00",
        })
        self.assertEqual(products["semiannual"]["max_installments"], 6)
        self.assertEqual(products["annual"]["max_installments"], 12)

    def test_discount_requires_both_residence_and_current_association(self):
        self.assertEqual(self.quote("monthly")["total"], "169.00")
        self.assertEqual(self.verify().status_code, 201)
        self.assertEqual(self.quote("monthly")["total"], "169.00")
        association = self.associate()
        for code, total in [("monthly", "84.50"), ("semiannual", "349.50"), ("annual", "484.50")]:
            result = self.quote(code)
            self.assertEqual(result["total"], total)
            self.assertEqual(result["discount_percent"], 50)
            self.assertEqual(result["association"], association)
        for code, total in [("hour", "5.00"), ("half_day", "15.00"), ("day", "25.00")]:
            self.assertEqual(self.quote(code)["total"], total)
            self.assertEqual(self.quote(code)["discount_percent"], 0)

    def test_false_evidence_duplicate_and_forged_actor(self):
        self.assertEqual(self.verify(proof_checked=False).status_code, 400)
        self.assertEqual(self.verify(declared=False).status_code, 400)
        self.assertEqual(ResidenceVerification.objects.count(), 0)
        response = self.verify(actor=999999)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["actor"], self.operator.pk)
        self.assertEqual(self.verify().status_code, 400)
        self.assertEqual(ResidenceVerification.objects.count(), 1)

    def test_revoke_preserves_evidence_and_allows_new_residence(self):
        self.associate()
        verification = self.verify().data["id"]
        url = f"/api/residence-verifications/{verification}/revoke/"
        self.assertEqual(self.client.post(url, {"reason": ""}).status_code, 400)
        self.assertEqual(self.client.post(url, {"reason": "Mudança de endereço declarada"}).status_code, 200)
        self.assertEqual(self.quote("monthly")["total"], "169.00")
        old = ResidenceVerification.objects.get(pk=verification)
        self.assertTrue(old.declared and old.proof_checked)
        self.assertEqual(old.revoked_by_id, self.operator.pk)
        self.assertEqual(self.verify().status_code, 201)
        self.assertEqual(ResidenceVerification.objects.count(), 2)

    def test_end_association_preserves_history_and_removes_new_quote_discount(self):
        association = self.associate()
        self.verify()
        response = self.client.post(f"/api/condominium-associations/{association}/end/", {
            "ends_on": timezone.localdate().isoformat(), "reason": "Fim da associação",
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.quote("annual")["total"], "969.00")
        self.assertTrue(CondominiumAssociation.objects.filter(pk=association).exists())
        self.assertTrue(AuditEvent.objects.filter(action="condominium.association.end", reason="Fim da associação").exists())

    def test_overlapping_associations_rejected_adjacent_allowed(self):
        today = timezone.localdate()
        payload = {"condominium": self.condominium.pk, "starts_on": today.isoformat(), "ends_on": (today + timedelta(days=5)).isoformat()}
        self.assertEqual(self.client.post("/api/condominium-associations/", payload).status_code, 201)
        self.assertEqual(self.client.post("/api/condominium-associations/", payload).status_code, 400)
        self.assertEqual(self.client.post("/api/condominium-associations/", {**payload, "starts_on": payload["ends_on"], "ends_on": (today + timedelta(days=10)).isoformat()}).status_code, 201)

    def test_future_association_and_inactive_condominium_not_eligible(self):
        self.verify()
        CondominiumAssociation.objects.create(condominium=self.condominium, starts_on=timezone.localdate() + timedelta(days=1), actor=self.operator)
        self.assertEqual(self.quote("monthly")["discount_percent"], 0)
        CondominiumAssociation.objects.all().update(starts_on=timezone.localdate())
        self.assertEqual(self.quote("monthly")["discount_percent"], 50)
        self.client.patch(f"/api/condominiums/{self.condominium.pk}/", {"active": False})
        self.assertEqual(self.quote("monthly")["discount_percent"], 0)

    def test_immutable_records_and_no_deletion(self):
        association = self.associate()
        residence = self.verify().data["id"]
        for url in [f"/api/residence-verifications/{residence}/", f"/api/condominium-associations/{association}/"]:
            self.assertEqual(self.client.patch(url, {}).status_code, 405)
            self.assertEqual(self.client.delete(url).status_code, 405)

    def test_rollback_when_audit_fails(self):
        with patch("ecowork.services.record", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                self.verify()
        self.assertEqual(ResidenceVerification.objects.count(), 0)

    def test_unauthorized_profiles_and_revoked_access(self):
        urls = ["/api/people/", "/api/condominiums/", "/api/condominium-associations/", "/api/residence-verifications/", "/api/ecowork/products/"]
        for role in ["instructor", "communication"]:
            User.objects.filter(pk=self.operator.pk).update(roles=[role])
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post("/api/ecowork/quote/", {"person": self.person.pk, "product": "annual"}).status_code, 403)
        User.objects.filter(pk=self.operator.pk).update(roles=["secretary"], access_status="rejected")
        self.assertEqual(self.client.get("/api/ecowork/products/").status_code, 403)
