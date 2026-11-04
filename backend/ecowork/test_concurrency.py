from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from uuid import uuid4

from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Student, User
from .models import Order, Payment


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks.')
class FinancialConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.actors = [User.objects.create_user(email=f'eco{i}@example.test', password='test', roles=['secretary'], access_status='approved') for i in range(2)]
        self.person = Student.objects.create(name='Pessoa concorrência')
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
