from datetime import timedelta
from uuid import uuid4

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Person, User


class EcoWorkQueryTests(APITestCase):
    def setUp(self):
        self.actor = User.objects.create_user(email='queries@example.test', password='test', roles=['secretary'], access_status='approved')
        self.person = Person.objects.create(name='Pessoa com histórico')
        self.other = Person.objects.create(name='Outra pessoa')
        self.client.force_authenticate(self.actor)
        self.today = timezone.localdate()

    def order(self, person=None, **changes):
        data = dict(
            person=(person or self.person).pk, product='semiannual', billing_mode='office', installments=6,
            first_due=str(self.today - timedelta(days=10)), expected_total='699.00', request_key=str(uuid4()),
        )
        response = self.client.post('/api/ecowork/orders/', {**data, **changes}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_filters_match_same_installment_without_duplicates(self):
        order = self.order()
        self.order(self.other)
        url = f'/api/ecowork/orders/?person={self.person.pk}'
        response = self.client.get(url + '&status=overdue')
        self.assertEqual([row['id'] for row in response.data['results']], [order['id']])
        response = self.client.get(url + f'&status=overdue&due_from={self.today}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(self.client.get(url + '&status=open').data['count'], 1)
        self.assertEqual(self.client.get(url + '&status=paid').data['count'], 0)
        self.assertEqual(self.client.get(url + f'&due_from={self.today}&due_to=2020-01-01').status_code, 400)
        self.assertEqual(self.client.get(url + '&status=invalid').status_code, 400)

    def test_person_summary_keeps_old_debt_alongside_paid_plan(self):
        self.order()
        paid = self.order(product='monthly', billing_mode='cash', installments=1, expected_total='169.00')
        charge = paid['charges'][0]
        result = self.client.post(f'/api/ecowork/charges/{charge["id"]}/receive/', dict(
            amount=charge['amount'], paid_on=str(self.today), method='pix', request_key=str(uuid4()),
        ))
        self.assertEqual(result.status_code, 200, result.data)
        self.order(self.other)
        result = self.client.get(f'/api/ecowork/orders/summary/?person={self.person.pk}&coverage=active')
        self.assertEqual(result.data, dict(total='868.00', paid='169.00', balance='699.00', overdue='116.50', orders=2, refunded='0.00', net_paid='169.00'))
        response = self.client.get(f'/api/ecowork/orders/?person={self.person.pk}&coverage=active&status=paid')
        self.assertEqual([row['id'] for row in response.data['results']], [paid['id']])

    def test_empty_summary_and_restricted_access(self):
        self.assertEqual(self.client.get(f'/api/ecowork/orders/summary/?person={self.person.pk}').data['balance'], '0.00')
        self.assertEqual(self.client.get('/api/ecowork/orders/summary/').status_code, 400)
        self.actor.roles = ['instructor']
        self.actor.save()
        self.assertEqual(self.client.get(f'/api/ecowork/orders/summary/?person={self.person.pk}').status_code, 403)

    def test_people_filters_do_not_turn_ecowork_member_into_student(self):
        self.order()
        response = self.client.get('/api/people/?has_ecowork=true&has_enrollments=false')
        self.assertEqual([row['id'] for row in response.data['results']], [self.person.pk])
        self.assertEqual(self.client.get('/api/students/?has_enrollments=true').data['count'], 0)
        self.assertEqual(self.client.get(f'/api/students/{self.person.pk}/').status_code, 200)
