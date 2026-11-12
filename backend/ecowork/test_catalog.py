from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from core.models import Person, User
from .models import Order


class EcoCatalogTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.coordinator = User.objects.create_user(email='coord@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.secretary = User.objects.create_user(email='secretary@example.test', password='password', access_status='approved', roles=['secretary'])
        self.person = Person.objects.create(name='Pessoa')
        self.client.force_authenticate(self.coordinator)

    def test_published_catalog_controls_new_orders_and_preserves_old(self):
        base = {'person': self.person.pk, 'quantity': 1, 'billing_mode': 'cash', 'installments': 1,
                'first_due': self.today.isoformat()}
        old = self.client.post('/api/ecowork/orders/', {**base, 'product': 'monthly', 'expected_total': '169.00', 'request_key': '8e8b8a36-ab83-4067-9d77-fd7cd7dafab8'}, format='json')
        self.assertEqual(old.status_code, 201, old.data)
        config = {'resident_discount_percent': 30, 'products': [{'code': 'flex', 'name': 'Plano flexível', 'price': '100.00', 'months': 1, 'hours': None, 'max_installments': 1}]}
        created = self.client.post('/api/ecowork/catalogs/', {'effective_from': self.today.isoformat(), 'configuration': config}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        url = f"/api/ecowork/catalogs/{created.data['id']}/"
        preview = self.client.post(url + 'preview/', {}, format='json')
        self.assertTrue(preview.data['valid'])
        published = self.client.post(url + 'publish/', {'reason': 'Tabela aprovada', 'revision': preview.data['revision']}, format='json')
        self.assertEqual(published.status_code, 200, published.data)
        self.assertEqual(self.client.get('/api/ecowork/products/').data[0]['code'], 'flex')
        new = self.client.post('/api/ecowork/orders/', {**base, 'product': 'flex', 'expected_total': '100.00', 'request_key': 'b2d59ccd-1e0a-4c21-a147-e0ab91811261'}, format='json')
        self.assertEqual(new.status_code, 201, new.data)
        self.assertEqual(Order.objects.get(pk=old.data['id']).total, 169)
        self.assertEqual(Order.objects.get(pk=new.data['id']).catalog_id, created.data['id'])
        self.assertEqual(self.client.patch(url, {'effective_from': (self.today + timedelta(days=1)).isoformat()}, format='json').status_code, 400)
        ended = self.client.post(url + 'end/', {'effective_until': self.today.isoformat(), 'reason': 'Nova tabela'}, format='json')
        self.assertEqual(ended.status_code, 200, ended.data)
        tomorrow = (self.today + timedelta(days=1)).isoformat()
        next_draft = self.client.post('/api/ecowork/catalogs/', {'effective_from': tomorrow, 'configuration': config}, format='json')
        next_url = f"/api/ecowork/catalogs/{next_draft.data['id']}/"
        self.assertTrue(self.client.post(next_url + 'preview/', {}, format='json').data['valid'])

    def test_secretary_cannot_manage_catalog(self):
        self.client.force_authenticate(self.secretary)
        self.assertEqual(self.client.get('/api/ecowork/catalogs/').status_code, 403)

    def test_fully_discounted_plan_starts_at_purchase_without_payment(self):
        from core.models import Condominium
        from .models import Payment
        condominium = Condominium.objects.create(name='Condomínio associado')
        self.assertEqual(self.client.post('/api/condominium-associations/', {
            'condominium': condominium.pk, 'starts_on': self.today.isoformat(),
        }).status_code, 201)
        self.assertEqual(self.client.post('/api/residence-verifications/', {
            'person': self.person.pk, 'condominium': condominium.pk, 'declared': True, 'proof_checked': True,
        }).status_code, 201)
        config = {'resident_discount_percent': 100, 'products': [
            {'code': 'flex', 'name': 'Plano flexível', 'price': '100.00', 'months': 1, 'hours': None, 'max_installments': 1},
            {'code': 'hour', 'name': 'Hora', 'price': '5.00', 'months': 0, 'hours': 1, 'max_installments': 1},
        ]}
        created = self.client.post('/api/ecowork/catalogs/', {'effective_from': self.today.isoformat(), 'configuration': config}, format='json')
        url = f"/api/ecowork/catalogs/{created.data['id']}/"
        preview = self.client.post(url + 'preview/', {}, format='json')
        self.assertTrue(preview.data['valid'], preview.data)
        self.assertEqual(self.client.post(url + 'publish/', {'reason': 'Aprovado', 'revision': preview.data['revision']}, format='json').status_code, 200)
        quote = self.client.post('/api/ecowork/quote/', {'person': self.person.pk, 'product': 'flex'}, format='json')
        self.assertEqual(quote.data['total'], '0.00')
        payload = {'person': self.person.pk, 'quantity': 1, 'billing_mode': 'cash', 'installments': 1,
                   'first_due': self.today.isoformat(), 'product': 'flex', 'expected_total': '0.00',
                   'request_key': '4ae37ad1-9b29-4d97-9c5a-2fa25a6d0a18'}
        response = self.client.post('/api/ecowork/orders/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['starts_on'], self.today.isoformat())
        self.assertEqual(response.data['coverage_status'], 'active')
        self.assertEqual(response.data['charges'], [])
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(self.client.post('/api/ecowork/orders/', payload, format='json').data['id'], response.data['id'])
        summary = self.client.get(f'/api/ecowork/orders/summary/?person={self.person.pk}').data
        self.assertEqual(summary['orders'], 1)
        self.assertEqual(summary['paid'], '0.00')
        self.assertEqual(summary['balance'], '0.00')
        casual = self.client.post('/api/ecowork/quote/', {'person': self.person.pk, 'product': 'hour'}, format='json')
        self.assertEqual(casual.data['total'], '5.00')

    def test_individual_benefit_applies_after_resident_discount(self):
        from core.models import Condominium
        condominium = Condominium.objects.create(name='Condomínio')
        self.assertEqual(self.client.post('/api/condominium-associations/', {'condominium': condominium.pk, 'starts_on': self.today.isoformat()}).status_code, 201)
        self.assertEqual(self.client.post('/api/residence-verifications/', {'person': self.person.pk, 'condominium': condominium.pk, 'declared': True, 'proof_checked': True}).status_code, 201)
        requested = self.client.post('/api/benefits/', {'person': self.person.pk, 'scope': 'ecowork', 'starts_on': self.today.isoformat(),
            'ends_on': (self.today + timedelta(days=30)).isoformat(), 'kind': 'percent', 'value': '10.00', 'reason': 'Benefício'}, format='json')
        self.assertEqual(requested.status_code, 201, requested.data)
        benefit_id = requested.data['id']
        self.assertEqual(self.client.post(f'/api/benefits/{benefit_id}/approve/', {'reason': 'Aprovado'}, format='json').status_code, 200)
        quote = self.client.post('/api/ecowork/quote/', {'person': self.person.pk, 'product': 'monthly', 'benefit': benefit_id}, format='json')
        self.assertEqual(quote.status_code, 200, quote.data)
        self.assertEqual(quote.data['total'], '76.05')
        self.assertEqual(quote.data['benefit_snapshot']['after_resident'], '84.50')
        response = self.client.post('/api/ecowork/orders/', {'person': self.person.pk, 'quantity': 1, 'product': 'monthly',
            'billing_mode': 'cash', 'installments': 1, 'first_due': self.today.isoformat(), 'benefit': benefit_id,
            'expected_total': '76.05', 'request_key': 'd2d9b14a-0f18-4aa6-bcac-efda7e25debd'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['benefit_snapshot']['discount'], '8.45')
        self.assertEqual(response.data['charges'][0]['amount'], '76.05')

    def test_individual_full_scholarship_requires_reference_and_starts_without_payment(self):
        requested = self.client.post('/api/benefits/', {'person': self.person.pk, 'scope': 'ecowork', 'starts_on': self.today.isoformat(),
            'ends_on': (self.today + timedelta(days=30)).isoformat(), 'kind': 'percent', 'value': '100.00', 'reason': 'Bolsa'}, format='json')
        self.assertEqual(requested.status_code, 201, requested.data)
        benefit_id = requested.data['id']
        url = f'/api/benefits/{benefit_id}/approve/'
        self.assertEqual(self.client.post(url, {'reason': 'Aprovado'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'reason': 'Aprovado', 'institutional_reference': 'Autorização 1'}, format='json').status_code, 200)
        response = self.client.post('/api/ecowork/orders/', {'person': self.person.pk, 'quantity': 1, 'product': 'monthly',
            'billing_mode': 'cash', 'installments': 1, 'first_due': self.today.isoformat(), 'benefit': benefit_id,
            'expected_total': '0.00', 'request_key': '813e1600-e1f9-4d84-8693-0a821b626489'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['coverage_status'], 'active')
        self.assertEqual(response.data['starts_on'], self.today.isoformat())
        self.assertEqual(response.data['charges'], [])
