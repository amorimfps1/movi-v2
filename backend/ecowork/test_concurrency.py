from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4

from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Person, User
from .models import Order, Payment, Refund


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks.')
class FinancialConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actors = [User.objects.create_user(email=f'eco{i}@example.test', password='test', roles=['secretary'], access_status='approved') for i in range(2)]
        self.person = Person.objects.create(name='Pessoa concorrência')
        self.payload = dict(person=self.person.pk, product='annual', billing_mode='office', installments=12, first_due=str(timezone.localdate()), expected_total='969.00', request_key=str(uuid4()))

    def parallel(self, fn):
        barrier = Barrier(2)
        def worker(index):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=self.actors[index].pk))
                barrier.wait(timeout=10)
                return fn(client, index)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, index) for index in range(2)]
            return [f.result(timeout=30) for f in futures]

    def test_same_order_request_creates_one_contract(self):
        statuses = self.parallel(lambda client, _: client.post('/api/ecowork/orders/', self.payload).status_code)
        self.assertEqual(statuses, [201, 201])
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().charges.count(), 12)

    def test_competing_payments_have_one_winner(self):
        client = APIClient()
        client.force_authenticate(self.actors[0])
        order = client.post('/api/ecowork/orders/', self.payload).data
        charge = order['charges'][0]
        payload = dict(amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix')
        statuses = self.parallel(lambda client, _: client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', {**payload, 'request_key': str(uuid4())}).status_code)
        self.assertEqual(sorted(statuses), [200, 400])
        self.assertEqual(Payment.objects.count(), 1)

    def paid_order(self):
        client = APIClient()
        client.force_authenticate(self.actors[0])
        order = client.post('/api/ecowork/orders/', self.payload).data
        charge = order['charges'][0]
        payment = client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix', request_key=str(uuid4()))).data
        return order, payment

    def test_competing_refunds_cannot_exceed_received(self):
        _, payment = self.paid_order()
        statuses = self.parallel(lambda client, _: client.post(f'/api/ecowork/payments/{payment["id"]}/refund/', dict(amount=payment['amount'], refunded_on=str(timezone.localdate()), method='pix', reason='Devolução', request_key=str(uuid4()))).status_code)
        self.assertEqual(sorted(statuses), [200, 400])
        self.assertEqual(Refund.objects.count(), 1)

    def test_refund_and_void_serialize(self):
        _, payment = self.paid_order()
        statuses = self.parallel(lambda client, index: client.post(
            f'/api/ecowork/payments/{payment["id"]}/' + ('refund/' if index else 'void/'),
            dict(amount=payment['amount'], refunded_on=str(timezone.localdate()), method='pix', reason='Correção', request_key=str(uuid4())) if index else dict(reason='Correção'),
        ).status_code)
        self.assertEqual(sorted(statuses), [200, 400])
        self.assertNotEqual(Payment.objects.get().voided_at is not None, Refund.objects.exists())

    def test_cancel_and_receive_preserve_consistent_charge(self):
        client = APIClient()
        client.force_authenticate(self.actors[0])
        order = client.post('/api/ecowork/orders/', self.payload).data
        charge = order['charges'][0]
        statuses = self.parallel(lambda client, index: client.post(
            f'/api/ecowork/orders/{order["id"]}/cancel/' if index else f'/api/ecowork/charges/{charge["id"]}/receive/',
            dict(mode='cancel_unpaid', reason='Encerramento') if index else dict(amount=charge['amount'], paid_on=str(timezone.localdate()), method='pix', request_key=str(uuid4())),
        ).status_code)
        self.assertEqual(statuses[1], 200)
        saved = Order.objects.get(pk=order['id'])
        self.assertEqual(saved.coverage_status, 'cancelled')
        first = saved.charges.get(number=1)
        self.assertNotEqual(first.cancelled_at is not None, first.payment is not None)
