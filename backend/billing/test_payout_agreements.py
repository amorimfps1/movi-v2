from rest_framework.test import APITestCase
from core.models import AuditEvent, Instructor, Modality, User


class PayoutAgreementTests(APITestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(email='coord@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.secretary = User.objects.create_user(email='secretary@example.test', password='password', access_status='approved', roles=['secretary'])
        self.instructor = Instructor.objects.create(name='Instrutor')
        self.modality = Modality.objects.create(name='Dança', default_price='100.00')
        self.payload = {'instructor': self.instructor.pk, 'modality': self.modality.pk, 'effective_from': '2026-01-01',
                        'effective_until': '2026-12-31', 'percentage': '25.00', 'allocation_method': 'calendar_days', 'reason': 'Acordo firmado'}

    def test_restricts_access_rejects_overlap_and_preserves_history(self):
        self.client.force_authenticate(self.secretary)
        self.assertEqual(self.client.post('/api/payout-agreements/', self.payload, format='json').status_code, 403)
        self.client.force_authenticate(self.coordinator)
        created = self.client.post('/api/payout-agreements/', self.payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.client.post('/api/payout-agreements/', self.payload, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f"/api/payout-agreements/{created.data['id']}/", {'percentage': '50'}, format='json').status_code, 405)
        self.assertTrue(AuditEvent.objects.filter(action='payout.agreement.created', reason='Acordo firmado').exists())
        self.assertEqual(self.client.post(f"/api/payout-agreements/{created.data['id']}/void/", {'reason': 'Correção'}, format='json').status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action='payout.agreement.voided', reason='Correção').exists())
        self.assertEqual(self.client.post('/api/payout-agreements/', self.payload, format='json').status_code, 201)
