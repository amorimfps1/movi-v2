from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import User, Person, Condominium, CondominiumAssociation, ResidenceVerification
from .finance import add_months
from .models import Order, Payment


class FinanceTests(APITestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email='finance@example.test', password='test', roles=['secretary'], access_status='approved')
        self.person = Person.objects.create(name='Pessoa EcoWork')
        self.client.force_authenticate(self.actor)

    def create_order(self, **changes):
        data = dict(person=self.person.pk, product='semiannual', quantity=1, billing_mode='office', installments=6,
                    first_due=str(timezone.localdate()), expected_total='699.00', request_key=str(uuid4()))
        return self.client.post('/api/ecowork/orders/', {**data, **changes}, format='json')

    def pay(self, charge, **changes):
        return self.client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(
            amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix', reference='', request_key=str(uuid4()), **changes), format='json')

    def test_installments_exact_total_and_activation(self):
        response = self.create_order()
        self.assertEqual(response.status_code, 201, response.data)
        order = response.data
        self.assertIsNone(order['starts_on'])
        self.assertEqual(sum(Decimal(c['amount']) for c in order['charges']), Decimal('699'))
        self.assertEqual(len(order['charges']), 6)
        self.assertEqual(self.pay(order['charges'][1]).status_code, 400)
        self.assertEqual(self.pay(order['charges'][0]).status_code, 200)
        saved = Order.objects.get(pk=order['id'])
        self.assertEqual(saved.starts_on, timezone.localdate())
        self.assertEqual(saved.ends_on, add_months(timezone.localdate(), 6))
        self.assertEqual(self.pay(order['charges'][1]).status_code, 200)
        saved.refresh_from_db()
        self.assertEqual(saved.starts_on, timezone.localdate())

    def test_discount_snapshot_survives_loss_of_association(self):
        condo = Condominium.objects.create(name='Condomínio')
        association = CondominiumAssociation.objects.create(condominium=condo, starts_on=timezone.localdate()-timedelta(days=1), actor=self.actor)
        ResidenceVerification.objects.create(person=self.person, condominium=condo, declared=True, proof_checked=True, actor=self.actor)
        response = self.create_order(product='annual', installments=12, expected_total='484.50')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(sum(Decimal(c['amount']) for c in response.data['charges']), Decimal('484.50'))
        association.ends_on = timezone.localdate()
        association.save()
        saved = Order.objects.get(pk=response.data['id'])
        self.assertEqual(saved.total, Decimal('484.50'))
        self.assertEqual(saved.discount_percent, 50)
        self.assertEqual(self.create_order(expected_total='349.50').status_code, 400)

    def test_card_is_one_customer_charge_not_monthly_debt(self):
        result = self.create_order(billing_mode='card').data
        self.assertEqual(len(result['charges']), 1)
        charge = result['charges'][0]
        self.assertEqual(self.pay(charge).status_code, 400)
        response = self.client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(amount='699.00', paid_on=str(timezone.localdate()), method='card', reference='APPROVED-123', request_key=str(uuid4())))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Order.objects.get(pk=result['id']).starts_on, timezone.localdate())

    def test_idempotent_order_and_payment(self):
        key = str(uuid4())
        first = self.create_order(request_key=key)
        second = self.create_order(request_key=key)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(self.create_order(request_key=key, installments=3).status_code, 400)
        charge = first.data['charges'][0]
        key = str(uuid4())
        payload = dict(amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix', reference='', request_key=key)
        url = f'/api/ecowork/charges/{charge["id"]}/receive/'
        self.assertEqual(self.client.post(url, payload).status_code, 200)
        self.assertEqual(self.client.post(url, payload).status_code, 200)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(self.pay(charge).status_code, 400)

    def test_limits_and_partial_rejected(self):
        self.assertEqual(self.create_order(installments=7).status_code, 400)
        self.assertEqual(self.create_order(billing_mode='cash').status_code, 400)
        result = self.create_order().data
        charge = result['charges'][0]
        for amount in ['1.00', '999.00']:
            response = self.client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(amount=amount, paid_on=str(timezone.localdate()), method='pix', request_key=str(uuid4())))
            self.assertEqual(response.status_code, 400)
        self.assertIsNone(Order.objects.get(pk=result['id']).starts_on)

    def test_avulso_not_ready_until_paid(self):
        response = self.create_order(product='hour', quantity=3, billing_mode='cash', installments=1, expected_total='15.00')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['coverage_status'], 'awaiting_payment')
        self.assertEqual(self.pay(response.data['charges'][0]).status_code, 200)
        self.assertEqual(Order.objects.get(pk=response.data['id']).coverage_status, 'paid_use')

    def test_month_end_and_payment_rollback(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))
        self.assertEqual(add_months(date(2026, 1, 31), 2), date(2026, 3, 31))
        order = self.create_order().data
        with patch('ecowork.finance.record', side_effect=RuntimeError('audit')):
            with self.assertRaises(RuntimeError):
                self.pay(order['charges'][0])
        self.assertEqual(Payment.objects.count(), 0)
        self.assertIsNone(Order.objects.get(pk=order['id']).starts_on)

    def test_financial_access_denied_and_records_not_editable(self):
        order = self.create_order().data
        self.assertEqual(self.client.patch(f'/api/ecowork/orders/{order["id"]}/', {'total': '1.00'}).status_code, 405)
        User.objects.filter(pk=self.actor.pk).update(roles=['instructor'])
        self.assertEqual(self.create_order().status_code, 403)
        self.assertEqual(self.client.get('/api/ecowork/orders/').status_code, 403)
        self.assertEqual(self.pay(order['charges'][0]).status_code, 403)
