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
