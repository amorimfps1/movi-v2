from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import APIException

from academic.models import Lesson, Attendance
from academic.services import roster, submit_attendance, correct_attendance
from core.models import AuditEvent, User, Person, Lead
from .contracts import terms, add_months
from .models import Enrollment, Charge, Payment, FinancialCatalogVersion
from .services import evaluate_eligibility


class ContractTests(TestCase):
    def setUp(self):
        from .tests import FinancialTests
        FinancialTests.setUp(self)
        modality = self.group.modality
        modality.price_category = 1
        modality.enrollment_fee_kind = 'standard'
        modality.save()
        self.group.capacity = 100
        self.group.save(update_fields=['capacity'])

    def enroll(self, start=None, plan='quarterly', installments=3, associated=False):
        response = self.client.post('/api/enrollments/', {
            'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': (start or self.today).isoformat(), 'plan': plan,
            'payment_method': 'card', 'installments': installments, 'associated': associated,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return Enrollment.objects.get(pk=response.data['id'])

    def settle(self, charge, on=None):
        return self.client.post(f'/api/charges/{charge.pk}/receive/', {
            'amount': str(charge.amount), 'paid_on': (on or self.today).isoformat(), 'method': 'card',
        }, format='json')

    def test_cancel_future_unpaid_installment_preserves_history(self):
        enrollment = self.enroll(self.today)
        charge = enrollment.charges.filter(category='tuition', due_date__gt=self.today).last()
        self.assertIsNotNone(charge)
        coordinator = User.objects.create_user(email='coord-cancel@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        payload = {'reason': 'Serviço não prestado', 'charge_ids': [charge.pk], 'service_unprovided_confirmed': True}
        response = self.client.post(f'/api/enrollments/{enrollment.pk}/cancel/', payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        charge.refresh_from_db()
        self.assertEqual(charge.status, 'cancelled')
        listed = self.client.get('/api/charges/?status=cancelled').data['results']
        self.assertIn(charge.pk, [item['id'] for item in listed])
        summary = self.client.get(f'/api/reports/summary/?start={charge.due_date.isoformat()}&end={charge.due_date.isoformat()}').data
        self.assertEqual(Decimal(summary['outstanding']), Decimal('0.00'))
        self.assertEqual(self.settle(charge).status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action='charge.cancelled', reason='Serviço não prestado').exists())

    def test_scheduled_cancellation_preserves_coverage_until_effective_date(self):
        from unittest.mock import patch
        enrollment = self.enroll(self.today)
        first = enrollment.charges.get(idempotency_key=f'contract:{enrollment.pk}:installment:1')
        self.assertEqual(self.settle(first).status_code, 201)
        self.assertEqual(self.settle(enrollment.charges.get(category='enrollment_fee')).status_code, 201)
        charge = enrollment.charges.filter(category='tuition').order_by('due_date').last()
        effective = self.today + timedelta(days=10)
        coordinator = User.objects.create_user(email='coord-schedule@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        response = self.client.post(f'/api/enrollments/{enrollment.pk}/cancel/', {
            'reason': 'Serviço futuro não prestado', 'effective_on': effective.isoformat(),
            'charge_ids': [charge.pk], 'service_unprovided_confirmed': True,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        enrollment.refresh_from_db()
        charge.refresh_from_db()
        self.assertEqual(response.data['administrative_status'], 'regular')
        self.assertTrue(evaluate_eligibility(enrollment, self.today)['eligible'])
        self.assertEqual(evaluate_eligibility(enrollment, effective)['status'], 'cancelled')
        self.assertEqual(charge.cancelled_on, effective)
        self.assertEqual(self.settle(charge).status_code, 400)
        self.assertIn(enrollment.pk, [item['id'] for item in self.client.get('/api/enrollments/?administrative_status=regular').data['results']])
        self.assertEqual(self.client.get('/api/reports/occupancy/').data['classes'][0]['regular'], 2)
        with patch('django.utils.timezone.localdate', return_value=effective):
            self.assertNotIn(enrollment.pk, [item['id'] for item in self.client.get('/api/enrollments/?administrative_status=regular').data['results']])
            self.assertEqual(self.client.get(f'/api/enrollments/{enrollment.pk}/').data['administrative_status'], 'cancelled')
            self.assertEqual(self.client.get('/api/reports/occupancy/').data['classes'][0]['regular'], 1)

    def test_scheduled_cancellation_rejects_installment_due_before_effect(self):
        enrollment = self.enroll(self.today)
        charge = enrollment.charges.filter(category='tuition').order_by('due_date').first()
        coordinator = User.objects.create_user(email='coord-date@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        response = self.client.post(f'/api/enrollments/{enrollment.pk}/cancel/', {
            'reason': 'Revisão', 'effective_on': (self.today + timedelta(days=10)).isoformat(),
            'charge_ids': [charge.pk], 'service_unprovided_confirmed': True,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.administrative_status, 'regular')

    def test_capacity_releases_on_scheduled_cancellation_and_ignores_empty_period(self):
        from rest_framework.exceptions import ValidationError
        from .services import ensure_class_capacity
        self.enrollment.administrative_status = 'cancelled'
        self.enrollment.cancelled_on = self.today
        self.enrollment.save(update_fields=['administrative_status', 'cancelled_on'])
        enrollment = self.enroll(self.today)
        self.group.capacity = 1
        self.group.save(update_fields=['capacity'])
        enrollment.administrative_status = 'cancelled'
        enrollment.cancelled_on = self.today + timedelta(days=10)
        enrollment.save(update_fields=['administrative_status', 'cancelled_on'])
        with self.assertRaises(ValidationError):
            ensure_class_capacity(self.group, self.today, self.today + timedelta(days=2))
        ensure_class_capacity(self.group, enrollment.cancelled_on, enrollment.cancelled_on + timedelta(days=2))
        enrollment.start_date = self.today + timedelta(days=20)
        enrollment.save(update_fields=['start_date'])
        ensure_class_capacity(self.group, self.today, self.today + timedelta(days=30))

    def test_void_first_installment_revokes_current_eligibility(self):
        enrollment = self.enroll(self.today)
        first = enrollment.charges.get(idempotency_key=f'contract:{enrollment.pk}:installment:1')
        fee = enrollment.charges.get(category='enrollment_fee')
        paid = self.settle(first)
        self.assertEqual(paid.status_code, 201)
        self.assertEqual(self.settle(fee).status_code, 201)
        self.assertTrue(evaluate_eligibility(enrollment)['eligible'])
        coordinator = User.objects.create_user(email='coord-void-contract@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        result = self.client.post(f"/api/payments/{paid.data['id']}/void/", {'reason': 'Registro incorreto'}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertFalse(evaluate_eligibility(enrollment)['eligible'])

    def test_cancel_installments_requires_coordination_and_does_not_cancel_paid_amounts(self):
        enrollment = self.enroll(self.today)
        charge = enrollment.charges.filter(category='tuition', due_date__gt=self.today).first()
        payload = {'reason': 'Revisão', 'charge_ids': [charge.pk], 'service_unprovided_confirmed': True}
        url = f'/api/enrollments/{enrollment.pk}/cancel/'
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord-check@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.settle(charge).status_code, 201)
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 400)
        enrollment.refresh_from_db()
        charge.refresh_from_db()
        self.assertEqual(enrollment.administrative_status, 'regular')
        self.assertIsNone(charge.cancelled_on)

    def test_cancel_installment_after_invalid_payment_was_corrected(self):
        enrollment = self.enroll(self.today)
        charge = enrollment.charges.filter(category='tuition', due_date__gt=self.today).last()
        coordinator = User.objects.create_user(email='coord-correct-before-cancel@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        payment = self.settle(charge)
        self.assertEqual(payment.status_code, 201)
        self.assertEqual(self.client.post(f"/api/payments/{payment.data['id']}/void/", {'reason': 'Lançamento incorreto'}, format='json').status_code, 200)
        response = self.client.post(f'/api/enrollments/{enrollment.pk}/cancel/', {
            'reason': 'Serviço não prestado', 'charge_ids': [charge.pk], 'service_unprovided_confirmed': True,
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        charge.refresh_from_db()
        self.assertEqual(charge.status, 'cancelled')

    def test_published_catalog_applies_only_to_new_contracts(self):
        previous = self.enroll(date(2026, 1, 5))
        config = {'plans': {'quarterly': {'months': 3, 'installments': [3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '300.00'}],
                  'fees': {'standard': {'associated': '0.00', 'non_associated': '0.00'}}}
        catalog = FinancialCatalogVersion.objects.create(version=1, status='published', effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31), configuration=config, created_by=self.admin,
            published_by=self.admin, published_at=timezone.now())
        new = self.enroll(date(2026, 2, 5))
        self.assertEqual(new.financial_catalog_id, catalog.pk)
        self.assertEqual(new.amount, Decimal('300.00'))
        self.assertEqual(new.charges.count(), 3)
        previous.refresh_from_db()
        self.assertIsNone(previous.financial_catalog_id)
        self.assertEqual(previous.amount, Decimal('1123.75'))

    def test_full_class_blocks_new_contract_without_creating_charges(self):
        self.group.capacity = 1
        self.group.save(update_fields=['capacity'])
        before = Charge.objects.count()
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly', 'payment_method': 'card',
            'installments': 3, 'associated': False}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('class_group', response.data)
        self.assertEqual(Charge.objects.count(), before)

    def test_capacity_exception_requires_coordinator_and_physical_limit(self):
        self.group.capacity, self.group.physical_capacity = 1, 2
        self.group.save(update_fields=['capacity', 'physical_capacity'])
        person = Person.objects.create(name='Vaga excepcional')
        data = {'student': person.pk, 'class_group': self.group.pk, 'start_date': self.today.isoformat(), 'plan': 'quarterly',
                'payment_method': 'card', 'installments': 3, 'associated': False, 'capacity_exception_reason': 'Autorização conferida'}
        self.assertEqual(self.client.post('/api/enrollments/', data, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        response = self.client.post('/api/enrollments/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(AuditEvent.objects.filter(action='enrollment.capacity_exception', reason='Autorização conferida').exists())
        data['student'] = Person.objects.create(name='Acima do limite físico').pk
        self.assertEqual(self.client.post('/api/enrollments/', data, format='json').status_code, 400)

    def test_contract_rejects_lead_linked_to_different_person(self):
        other = Person.objects.create(name='Outra pessoa')
        lead = Lead.objects.create(name='Lead', status='converted', student=other)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'source_lead': lead.pk, 'start_date': self.today.isoformat(), 'plan': 'quarterly',
            'payment_method': 'card', 'installments': 3, 'associated': False}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('source_lead', response.data)

    def test_full_scholarship_requires_institutional_reference_and_creates_no_fake_payment(self):
        payload = {'person': self.student.pk, 'starts_on': self.today.isoformat(), 'ends_on': (self.today + timedelta(days=30)).isoformat(),
                   'kind': 'percent', 'value': '100.00', 'fee_waiver': True, 'reason': 'Bolsa solicitada'}
        requested = self.client.post('/api/benefits/', payload, format='json')
        self.assertEqual(requested.status_code, 201, requested.data)
        url = f"/api/benefits/{requested.data['id']}/approve/"
        self.assertEqual(self.client.post(url, {'reason': 'Revisado'}, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord-benefit@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(url, {'reason': 'Revisado'}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'reason': 'Revisado', 'institutional_reference': 'Autorização 10'}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly', 'payment_method': 'card', 'installments': 3,
            'associated': False, 'benefit': requested.data['id']}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        enrollment = Enrollment.objects.get(pk=response.data['id'])
        self.assertEqual(enrollment.amount, Decimal('0.00'))
        self.assertEqual(enrollment.charges.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)
        self.assertTrue(evaluate_eligibility(enrollment)['eligible'])

    def test_fixed_discount_above_limit_requires_specific_authorization(self):
        payload = {'person': self.student.pk, 'starts_on': self.today.isoformat(), 'ends_on': (self.today + timedelta(days=30)).isoformat(),
                   'kind': 'fixed', 'value': '500.00', 'fee_waiver': False, 'reason': 'Desconto solicitado'}
        benefit = self.client.post('/api/benefits/', payload, format='json')
        self.assertEqual(benefit.status_code, 201, benefit.data)
        coordinator = User.objects.create_user(email='coord-fixed@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(f"/api/benefits/{benefit.data['id']}/approve/", {'reason': 'Revisado'}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly', 'payment_method': 'card', 'installments': 3,
            'associated': False, 'benefit': benefit.data['id']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('benefit', response.data)

    def test_partial_discount_preserves_exact_sum_and_fee(self):
        payload = {'person': self.student.pk, 'starts_on': self.today.isoformat(), 'ends_on': (self.today + timedelta(days=30)).isoformat(),
                   'kind': 'percent', 'value': '15.00', 'fee_waiver': False, 'reason': 'Desconto solicitado'}
        benefit = self.client.post('/api/benefits/', payload, format='json')
        coordinator = User.objects.create_user(email='coord-discount@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(f"/api/benefits/{benefit.data['id']}/approve/", {'reason': 'Revisado'}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly', 'payment_method': 'card', 'installments': 3,
            'associated': False, 'benefit': benefit.data['id']}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        enrollment = Enrollment.objects.get(pk=response.data['id'])
        self.assertEqual(sum(item.amount for item in enrollment.charges.filter(category='tuition')), enrollment.amount)
        self.assertEqual(enrollment.charges.filter(category='enrollment_fee').count(), 1)
        self.assertEqual(enrollment.benefit_snapshot['gross'], '1123.75')

    def test_fee_waiver_can_be_requested_without_tuition_discount(self):
        payload = {'person': self.student.pk, 'starts_on': self.today.isoformat(), 'ends_on': (self.today + timedelta(days=30)).isoformat(),
                   'kind': 'percent', 'value': '0.00', 'fee_waiver': True, 'reason': 'Isenção de taxa'}
        benefit = self.client.post('/api/benefits/', payload, format='json')
        self.assertEqual(benefit.status_code, 201, benefit.data)
        coordinator = User.objects.create_user(email='coord-fee@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(f"/api/benefits/{benefit.data['id']}/approve/", {'reason': 'Revisado'}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly', 'payment_method': 'card', 'installments': 3,
            'associated': False, 'benefit': benefit.data['id']}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        enrollment = Enrollment.objects.get(pk=response.data['id'])
        self.assertEqual(enrollment.amount, Decimal('1123.75'))
        self.assertFalse(enrollment.charges.filter(category='enrollment_fee').exists())

    def test_benefit_cannot_bypass_stricter_catalog_limit(self):
        config = {'plans': {'quarterly': {'months': 3, 'installments': [3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '300.00'}],
                  'fees': {'standard': {'associated': '0.00', 'non_associated': '0.00'}}}
        for version, start, end, limit in [(1, date(2026, 1, 1), date(2026, 6, 30), '20.00'), (2, date(2026, 7, 1), date(2026, 12, 31), '10.00')]:
            FinancialCatalogVersion.objects.create(version=version, status='published', effective_from=start, effective_until=end,
                configuration={**config, 'discount_limit_percent': limit}, created_by=self.admin, published_by=self.admin, published_at=timezone.now())
        requested = self.client.post('/api/benefits/', {'person': self.student.pk, 'starts_on': '2026-01-01', 'ends_on': '2026-12-31',
            'kind': 'percent', 'value': '15.00', 'fee_waiver': False, 'reason': 'Pedido'}, format='json')
        coordinator = User.objects.create_user(email='coord-limit@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(f"/api/benefits/{requested.data['id']}/approve/", {'reason': 'Aprovado'}, format='json').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/enrollments/', {'student': self.student.pk, 'class_group': self.group.pk, 'start_date': '2026-08-01',
            'plan': 'quarterly', 'payment_method': 'card', 'installments': 3, 'associated': False, 'benefit': requested.data['id']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('benefit', response.data)

    def test_waiting_list_priority_and_conversion_are_atomic(self):
        first = Person.objects.create(name='Primeira')
        second = Person.objects.create(name='Segunda')
        for person in (first, second):
            response = self.client.post('/api/waiting-list/', {'class_group': self.group.pk, 'person': person.pk}, format='json')
            self.assertEqual(response.status_code, 201, response.data)
        data = {'student': second.pk, 'class_group': self.group.pk, 'start_date': self.today.isoformat(),
                'plan': 'quarterly', 'payment_method': 'card', 'installments': 3, 'associated': False}
        self.assertEqual(self.client.post('/api/enrollments/', data, format='json').status_code, 400)
        data['student'] = first.pk
        created = self.client.post('/api/enrollments/', data, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        waiting = self.client.get(f'/api/waiting-list/?class_group={self.group.pk}&status=waiting').data['results']
        self.assertEqual([row['person'] for row in waiting], [second.pk])
        self.assertTrue(AuditEvent.objects.filter(action='waiting_list.enrolled').exists())

    def test_archiving_removes_person_from_active_waiting_list(self):
        person = Person.objects.create(name='Pessoa na fila')
        created = self.client.post('/api/waiting-list/', {'class_group': self.group.pk, 'person': person.pk}, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.client.patch(f'/api/people/{person.pk}/', {'archived': True}, format='json').status_code, 200)
        waiting = self.client.get(f'/api/waiting-list/?class_group={self.group.pk}&status=waiting').data['results']
        self.assertEqual(waiting, [])
        self.assertTrue(AuditEvent.objects.filter(action='waiting_list.cancelled', reason='Pessoa arquivada.').exists())

    def test_catalog_fixed_due_day_preserves_reference_after_short_month(self):
        config = {'plans': {'quarterly': {'months': 3, 'installments': [3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '300.00'}],
                  'fees': {'standard': {'associated': '0.00', 'non_associated': '0.00'}},
                  'due_rule': 'fixed', 'due_day': 31, 'due_reference': 'first_due'}
        FinancialCatalogVersion.objects.create(version=1, status='published', effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31), configuration=config, created_by=self.admin,
            published_by=self.admin, published_at=timezone.now())
        enrollment = self.enroll(date(2026, 1, 20))
        self.assertEqual([charge.due_date for charge in enrollment.charges.all()],
                         [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)])

    def test_custom_catalog_plan_is_available_and_stored(self):
        config = {'plans': {'p_semestral': {'name': 'Plano semestral', 'months': 6, 'installments': [6]}},
                  'prices': [{'category': 1, 'plan': 'p_semestral', 'method': 'card', 'associated': False, 'amount': '600.00'}],
                  'fees': {'standard': {'associated': '0.00', 'non_associated': '0.00'}}}
        FinancialCatalogVersion.objects.create(version=1, status='published', effective_from=date(2026, 1, 1),
            effective_until=date(2026, 12, 31), configuration=config, created_by=self.admin,
            published_by=self.admin, published_at=timezone.now())
        options = self.client.get('/api/financial-options/?on=2026-02-01').data
        self.assertEqual(options['plans'][0]['name'], 'Plano semestral')
        enrollment = self.enroll(date(2026, 2, 1), 'p_semestral', 6)
        self.assertEqual(enrollment.amount, Decimal('600.00'))
        self.assertEqual(enrollment.charges.count(), 6)
        self.assertEqual(self.client.get(f'/api/enrollments/{enrollment.pk}/').data['plan_name'], 'Plano semestral')

    def test_cannot_end_catalog_before_already_scheduled_contract(self):
        config = {'plans': {'quarterly': {'months': 3, 'installments': [3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '300.00'}],
                  'fees': {'standard': {'associated': '0.00', 'non_associated': '0.00'}}}
        catalog = FinancialCatalogVersion.objects.create(version=1, status='published', effective_from=self.today,
            configuration=config, created_by=self.admin, published_by=self.admin, published_at=timezone.now())
        self.enroll(self.today + timedelta(days=1))
        coordinator = User.objects.create_user(email='coord-end@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        response = self.client.post(f'/api/financial-catalogs/{catalog.pk}/end/', {'effective_until': self.today.isoformat(), 'reason': 'Nova tabela'}, format='json')
        self.assertEqual(response.status_code, 400)
        catalog.refresh_from_db()
        self.assertIsNone(catalog.effective_until)

    def test_quarterly_annual_and_exact_installment_totals(self):
        for plan, months, counts in [('quarterly', 3, [1, 2, 3]), ('yearly', 12, [3, 6, 10, 12])]:
            for count in counts:
                with self.subTest(plan=plan, count=count):
                    enrollment = self.enroll(date(2026, 1, 10), plan, count)
                    self.assertEqual(enrollment.end_date, add_months(enrollment.start_date, months) - timedelta(days=1))
                    charges = enrollment.charges.filter(category='tuition')
                    self.assertEqual(charges.count(), count)
                    self.assertEqual(sum(c.amount for c in charges), enrollment.amount)
                    self.assertEqual(enrollment.charges.filter(category='enrollment_fee').count(), 1)

    def test_due_dates_clamp_without_drift_and_after_fifteenth(self):
        for day in [29, 30, 31]:
            enrollment = self.enroll(date(2026, 1, day))
            self.assertEqual([c.due_date for c in enrollment.charges.filter(category='tuition')],
                             [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, day)])
        self.assertEqual(self.enroll(date(2026, 1, 15)).charges.first().due_date, date(2026, 1, 15))

    def test_prices_association_and_specific_fees(self):
        for associated, total, fee in [(False, '1123.75', '35'), (True, '998.89', '25')]:
            enrollment = self.enroll(associated=associated)
            self.assertEqual(enrollment.amount, Decimal(total))
            self.assertEqual(enrollment.fee_amount, Decimal(fee))
        modality = self.group.modality
        modality.enrollment_fee_kind = 'rhythmic'
        modality.save()
        self.assertEqual(self.enroll(associated=True).fee_amount, Decimal('35'))
        self.assertEqual(self.enroll().fee_amount, Decimal('70'))

    def test_unknown_prices_rejected_without_writes(self):
        before = Enrollment.objects.count()
        for method, category in [('boleto', 1), ('card', 7), ('card', None)]:
            modality = self.group.modality
            modality.price_category = category
            with self.assertRaises(APIException):
                terms(self.group, self.today, 'quarterly', False, method, 3)
        self.assertEqual(before, Enrollment.objects.count())

    def test_late_payment_restores_without_extending_contract_and_idempotent(self):
        enrollment = self.enroll(self.today - timedelta(days=35))
        original_end = enrollment.end_date
        self.assertFalse(evaluate_eligibility(enrollment)['eligible'])
        for charge in enrollment.charges.filter(due_date__lte=self.today):
            self.assertEqual(self.settle(charge).status_code, 201)
            self.assertEqual(self.settle(charge).status_code, 200)
        self.assertTrue(evaluate_eligibility(enrollment)['eligible'])
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.end_date, original_end)
        self.assertFalse(evaluate_eligibility(enrollment, original_end + timedelta(days=1))['eligible'])

    def test_missing_charge_repair_and_duplicates(self):
        enrollment = self.enroll()
        first = enrollment.charges.filter(category='tuition').first()
        self.settle(first)
        self.settle(enrollment.charges.get(category='enrollment_fee'))
        missing = enrollment.charges.filter(category='tuition').last()
        missing.delete()  # Simulate an incomplete import; API has no DELETE.
        self.assertFalse(evaluate_eligibility(enrollment)['eligible'])
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/enrollments/{enrollment.pk}/repair_charges/').status_code, 200)
        self.assertEqual(enrollment.charges.count(), 4)
        self.assertTrue(evaluate_eligibility(enrollment)['eligible'])

    def test_activation_requires_fee_and_first_installment_but_not_future_installments(self):
        enrollment = self.enroll()
        self.settle(enrollment.charges.filter(category='tuition').first())
        self.assertFalse(evaluate_eligibility(enrollment)['eligible'])
        self.settle(enrollment.charges.get(category='enrollment_fee'))
        self.assertTrue(evaluate_eligibility(enrollment)['eligible'])
        self.assertEqual(enrollment.charges.filter(category='tuition', payments__isnull=True).count(), 2)

    def test_renewal_preserves_old_contract_and_retries(self):
        enrollment = self.enroll(date(2026, 1, 10))
        payload = {'start_date': '2026-04-10', 'plan': 'quarterly', 'payment_method': 'card', 'installments': 3}
        url = f'/api/enrollments/{enrollment.pk}/renew/'
        first = self.client.post(url, payload, format='json')
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(self.client.post(url, payload, format='json').data['id'], first.data['id'])
        self.assertFalse(Enrollment.objects.get(pk=first.data['id']).charges.filter(category='enrollment_fee').exists())
        self.assertEqual(enrollment.charges.count(), 4)

    def test_attendance_all_absent_correction_and_scope(self):
        enrollment = self.enroll()
        self.settle(enrollment.charges.filter(category='tuition').first())
        self.settle(enrollment.charges.get(category='enrollment_fee'))
        # Remove the legacy fixture from this class's current roster.
        self.enrollment.administrative_status = 'cancelled'
        self.enrollment.save()
        lesson = Lesson.objects.create(class_group=self.group, date=self.today)
        payload = roster(self.admin.pk, lesson.pk)
        submit_attendance(self.admin.pk, lesson.pk, payload['version'], [{'enrollment': enrollment.pk, 'present': False}])
        lesson.date = self.today - timedelta(days=1)
        lesson.save(update_fields=['date'])
        correct_attendance(self.admin.pk, lesson.pk, [{'enrollment': enrollment.pk, 'present': True}], 'Correção conferida')
        event = AuditEvent.objects.get(action='attendance.corrected')
        self.assertEqual(event.metadata['before'], False)
        self.assertEqual(event.metadata['after'], True)
        stranger = User.objects.create_user(email='stranger@example.test', roles=['instructor'], access_status='approved')
        with self.assertRaises(APIException):
            correct_attendance(stranger.pk, lesson.pk, [{'enrollment': enrollment.pk, 'present': False}], 'Tentativa')
        self.client.force_authenticate(stranger)
        response = self.client.post(f'/api/lessons/{lesson.pk}/correct_attendance/',
                                    {'marks': [{'enrollment': enrollment.pk, 'present': False}], 'reason': 'Tentativa'}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_empty_attendance_and_no_new_retroactive_diary(self):
        self.enrollment.administrative_status = 'cancelled'
        self.enrollment.save()
        lesson = Lesson.objects.create(class_group=self.group, date=self.today)
        submit_attendance(self.admin.pk, lesson.pk, roster(self.admin.pk, lesson.pk)['version'], [])
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, 'completed')
        past = Lesson.objects.create(class_group=self.group, date=self.today - timedelta(days=1))
        with self.assertRaises(APIException):
            submit_attendance(self.admin.pk, past.pk, roster(self.admin.pk, past.pk)['version'], [])
        self.assertFalse(Attendance.objects.filter(lesson=past).exists())

    def test_whatsapp_requires_manual_confirmation_and_preserves_snapshot(self):
        charge = self.enroll().charges.first()
        url = f'/api/charges/{charge.pk}/messages/'
        response = self.client.post(url, {'recipient': 'Responsável de teste', 'phone': '5511999999999'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        message = response.data[0]
        self.assertIsNone(message['sent_at'])
        self.assertIn(self.student.name, message['text'])
        self.assertIn('https://wa.me/', message['url'])
        confirm = f'/api/charges/{charge.pk}/confirm_message/'
        for _ in range(2):
            self.assertEqual(self.client.post(confirm, {'message': message['id']}, format='json').status_code, 200)
        self.assertEqual(AuditEvent.objects.filter(action='collection.sent_manually').count(), 1)
        self.assertEqual(self.client.get(url).data[0]['text'], message['text'])
