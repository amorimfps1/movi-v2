from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Person, User, AuditEvent
from .models import Order, Payment, Refund


class CorrectionTests(APITestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email='correction@example.test', password='test', roles=['secretary'], access_status='approved')
        self.person = Person.objects.create(name='Correções EcoWork')
        self.client.force_authenticate(self.actor)
        response = self.client.post('/api/ecowork/orders/', dict(person=self.person.pk, product='semiannual', billing_mode='office', installments=6, first_due=str(timezone.localdate()), expected_total='699.00', request_key=str(uuid4())))
        self.assertEqual(response.status_code, 201, response.data)
        self.order = response.data

    def pay(self, index=0):
        charge = self.order['charges'][index]
        return self.client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix', request_key=str(uuid4())))

    def cancel(self, mode='cancel_unpaid', reason='Encerramento solicitado'):
        return self.client.post(f'/api/ecowork/orders/{self.order["id"]}/cancel/', dict(mode=mode, reason=reason))

    def void(self, payment, reason='Lançamento incorreto'):
        return self.client.post(f'/api/ecowork/payments/{payment}/void/', {'reason': reason})

    def refund(self, payment, **changes):
        data = dict(amount='20.00', refunded_on=str(timezone.localdate()), method='pix', reference='', reason='Devolução conferida', request_key=str(uuid4()))
        return self.client.post(f'/api/ecowork/payments/{payment}/refund/', {**data, **changes})

    def summary(self):
        return self.client.get(f'/api/ecowork/orders/summary/?person={self.person.pk}').data

    def test_void_preserves_original_and_allows_new_payment_without_double_count(self):
        payment = self.pay().data
        self.assertEqual(self.void(payment['id']).status_code, 200)
        self.assertEqual(self.void(payment['id']).status_code, 200)
        self.assertIsNone(Order.objects.get(pk=self.order['id']).starts_on)
        self.assertEqual(self.summary()['balance'], '699.00')
        replacement = self.pay()
        self.assertEqual(replacement.status_code, 200, replacement.data)
        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(self.summary()['paid'], '116.50')
        self.assertEqual(self.summary()['total'], '699.00')
        self.assertEqual(self.client.get('/api/ecowork/orders/?status=paid').data['count'], 1)
        details = self.client.get(f'/api/ecowork/orders/{self.order["id"]}/').data['charges'][0]
        self.assertEqual(len(details['payments']), 2)
        self.assertEqual(details['payment']['id'], replacement.data['id'])
        self.assertEqual(AuditEvent.objects.filter(action='ecowork.payment.void').count(), 1)

    def test_first_payment_requires_correction_of_later_payments(self):
        first = self.pay().data
        second = self.pay(1).data
        self.assertEqual(self.void(first['id']).status_code, 400)
        self.assertEqual(self.void(second['id']).status_code, 200)
        self.assertEqual(self.void(first['id']).status_code, 200)

    def test_cancel_unpaid_preserves_paid_and_does_not_refund(self):
        self.pay()
        result = self.cancel()
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['coverage_status'], 'cancelled')
        self.assertEqual([c['status'] for c in result.data['charges']], ['paid'] + ['cancelled'] * 5)
        self.assertEqual(self.summary()['balance'], '0.00')
        self.assertEqual(self.summary()['paid'], '116.50')
        self.assertFalse(Refund.objects.exists())
        self.assertEqual(self.pay(1).status_code, 400)
        self.assertEqual(self.cancel().status_code, 200)
        self.assertEqual(self.cancel('keep_unpaid').status_code, 400)
        self.assertEqual(self.client.get('/api/ecowork/orders/?coverage=active').data['count'], 0)
        self.assertEqual(self.client.get('/api/ecowork/orders/?coverage=cancelled&status=cancelled').data['count'], 1)
        self.assertEqual(self.client.get('/api/ecowork/orders/?status=open').data['count'], 0)

    def test_cancel_keep_unpaid_accepts_later_payment_without_reactivation(self):
        self.assertEqual(self.cancel('keep_unpaid').status_code, 200)
        self.assertEqual(self.summary()['balance'], '699.00')
        self.assertEqual(self.pay().status_code, 200)
        self.assertEqual(self.pay(1).status_code, 200)
        saved = Order.objects.get(pk=self.order['id'])
        self.assertEqual(saved.coverage_status, 'cancelled')
        self.assertIsNone(saved.starts_on)
        self.assertEqual(self.summary()['balance'], '466.00')

    def test_void_after_cancel_applies_existing_cancellation_decision(self):
        payment = self.pay().data
        self.cancel()
        self.assertEqual(self.void(payment['id']).status_code, 200)
        self.assertEqual(self.summary()['balance'], '0.00')
        self.assertEqual(self.summary()['total'], '0.00')
        self.assertEqual(self.pay().status_code, 400)

    def test_partial_and_full_refunds_preserve_quittance_and_coverage(self):
        payment = self.pay().data
        key = str(uuid4())
        first = self.refund(payment['id'], request_key=key)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(self.refund(payment['id'], request_key=key).data['id'], first.data['id'])
        self.assertEqual(self.refund(payment['id'], request_key=key, amount='21.00').status_code, 400)
        self.assertEqual(self.refund(payment['id'], amount='96.50').status_code, 200)
        self.assertEqual(self.refund(payment['id'], amount='0.01').status_code, 400)
        self.assertEqual(self.void(payment['id']).status_code, 400)
        self.assertEqual(self.summary()['refunded'], '116.50')
        self.assertEqual(self.summary()['net_paid'], '0.00')
        self.assertEqual(self.summary()['balance'], '582.50')
        self.assertEqual(Order.objects.get(pk=self.order['id']).coverage_status, 'active')
        self.assertEqual(self.pay().status_code, 400)

    def test_invalid_inputs_and_no_refund_of_voided_payment(self):
        payment = self.pay().data
        for changes in [{'amount': '0'}, {'amount': '-1'}, {'amount': '117'}, {'reason': '  '}, {'refunded_on': str(timezone.localdate()+timedelta(days=1))}, {'refunded_on': str(timezone.localdate()-timedelta(days=1))}]:
            self.assertEqual(self.refund(payment['id'], **changes).status_code, 400)
        self.assertEqual(self.cancel(reason=' ').status_code, 400)
        self.assertEqual(self.void(payment['id'], reason=' ').status_code, 400)
        self.void(payment['id'])
        self.assertEqual(self.refund(payment['id']).status_code, 400)

    def test_authorization_and_audit_rollback(self):
        payment = self.pay().data
        with patch('ecowork.finance.record', side_effect=RuntimeError('audit')):
            for operation in [lambda: self.refund(payment['id']), lambda: self.void(payment['id']), self.cancel]:
                with self.assertRaises(RuntimeError):
                    operation()
        self.assertFalse(Refund.objects.exists())
        self.assertIsNone(Payment.objects.get(pk=payment['id']).voided_at)
        self.assertIsNone(Order.objects.get(pk=self.order['id']).cancelled_at)
        for roles in [['instructor'], ['communication'], []]:
            User.objects.filter(pk=self.actor.pk).update(roles=roles)
            self.assertEqual(self.refund(payment['id']).status_code, 403)
            self.assertEqual(self.void(payment['id']).status_code, 403)
            self.assertEqual(self.cancel().status_code, 403)
