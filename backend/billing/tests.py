from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import User, Person, Modality, Instructor, ClassGroup, AuditEvent, Lead
from .models import Enrollment, Charge, Payment, WaitingListEntry
from .services import ensure_class_capacity, evaluate_eligibility

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, close_old_connections, connections
from django.test import TransactionTestCase


class FinancialTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='finance@example.test',password='Movi-test-2026!',access_status='approved',roles=['secretary'])
        self.student = Person.objects.create(name='Aluno de teste')
        modality = Modality.objects.create(name='Música',default_price='100.00')
        instructor = Instructor.objects.create(name='Instrutor de teste')
        self.group = ClassGroup.objects.create(name='Grupo de teste',modality=modality,instructor=instructor,
            weekdays=[0],start_time='09:00',end_time='10:00',room='Sala',capacity=10)
        self.today = timezone.localdate()
        self.enrollment = Enrollment.objects.create(student=self.student,class_group=self.group,start_date=self.today,
            plan='monthly',amount='100.00')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_capacity_checks_overlaps_throughout_contract(self):
        from rest_framework.exceptions import ValidationError
        self.group.capacity = 1
        self.group.save(update_fields=['capacity'])
        self.enrollment.start_date = self.today + timedelta(days=10)
        self.enrollment.end_date = self.today + timedelta(days=20)
        self.enrollment.save(update_fields=['start_date', 'end_date'])
        with self.assertRaises(ValidationError):
            ensure_class_capacity(self.group, self.today, self.today + timedelta(days=15))
        ensure_class_capacity(self.group, self.today, self.today + timedelta(days=9))
        ensure_class_capacity(self.group, self.today + timedelta(days=21), None)

    def test_suspension_requires_coordinator_and_blocks_participation_by_date(self):
        url = f'/api/enrollments/{self.enrollment.pk}/suspensions/'
        payload = {'starts_on': self.today.isoformat(), 'ends_on': (self.today + timedelta(days=2)).isoformat(), 'reason': 'Solicitação'}
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord@example.test', password='Movi-test-2026!', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 201)
        self.assertEqual(evaluate_eligibility(self.enrollment, self.today)['status'], 'suspended')
        self.assertNotEqual(evaluate_eligibility(self.enrollment, self.today + timedelta(days=3))['status'], 'suspended')
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action='enrollment.suspended', reason='Solicitação').exists())

    def test_suspension_rejects_retroactive_and_overlong_periods(self):
        coordinator = User.objects.create_user(email='coord@example.test', password='Movi-test-2026!', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        url = f'/api/enrollments/{self.enrollment.pk}/suspensions/'
        for start, end in [(self.today - timedelta(days=1), self.today), (self.today, self.today + timedelta(days=30))]:
            self.assertEqual(self.client.post(url, {'starts_on': start.isoformat(), 'ends_on': end.isoformat(), 'reason': 'Pedido'}, format='json').status_code, 400)

    def test_academic_count_and_list_exclude_people_without_enrollment(self):
        Person.objects.create(name='Frequentador sem matrícula')
        Enrollment.objects.create(student=self.student, class_group=self.group, start_date=self.today, plan='monthly', amount='100.00')
        result = self.client.get('/api/reports/summary/')
        self.assertEqual(result.data['students'], 1)
        result = self.client.get('/api/students/?has_enrollments=true')
        self.assertEqual([row['id'] for row in result.data['results']], [self.student.pk])

    def test_occupancy_separates_regular_experimental_and_waiting(self):
        trial = Person.objects.create(name='Experimental')
        Enrollment.objects.create(student=trial, class_group=self.group, start_date=self.today, plan='monthly', amount='100.00', kind='trial')
        for name in ('Espera A', 'Espera B'):
            WaitingListEntry.objects.create(person=Person.objects.create(name=name), class_group=self.group, actor=self.admin)
        response = self.client.get('/api/reports/occupancy/')
        self.assertEqual(response.status_code, 200)
        row = response.data['classes'][0]
        self.assertEqual((row['regular'], row['experimental'], row['waiting']), (1, 1, 2))
        self.assertEqual(row['percent'], Decimal('10.00'))

    def test_frequency_uses_completed_lessons_and_consecutive_marks(self):
        from academic.models import Attendance, Lesson
        self.enrollment.start_date = self.today - timedelta(days=100)
        self.enrollment.save(update_fields=['start_date'])
        for days_ago, present, status in [(1, False, 'completed'), (2, False, 'completed'),
                                           (3, False, 'completed'), (4, True, 'cancelled'),
                                           (45, True, 'completed')]:
            lesson = Lesson.objects.create(class_group=self.group, date=self.today - timedelta(days=days_ago), status=status)
            Attendance.objects.create(lesson=lesson, enrollment=self.enrollment, actor=self.admin, present=present)
        result = self.client.get('/api/reports/frequency/')
        self.assertEqual(result.status_code, 200)
        row = result.data['enrollments'][0]
        self.assertEqual(row['short_window']['percent'], Decimal('0.00'))
        self.assertEqual(row['long_window']['percent'], Decimal('25.00'))
        self.assertEqual(row['consecutive_absences'], 3)
        self.assertTrue(row['alert'])

    def test_frequency_settings_require_coordinator_and_are_audited(self):
        url = '/api/reports/frequency-policy/'
        payload = {'short_days': 7, 'long_days': 14, 'absence_threshold': 2, 'reason': 'Ajuste aprovado'}
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord@example.test', password='Movi-test-2026!', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 200)
        result = self.client.get('/api/reports/frequency/').data
        self.assertEqual((result['short_days'], result['long_days'], result['absence_threshold']), (7, 14, 2))
        self.assertTrue(AuditEvent.objects.filter(action='frequency_policy.updated', reason='Ajuste aprovado').exists())

    def test_conversion_counts_cohort_and_only_explicit_enrollment_origin(self):
        lead = Lead.objects.create(name='Convertido', status='converted', student=self.student)
        Lead.objects.create(name='Novo')
        url = f'/api/reports/conversion/?start={self.today.isoformat()}&end={self.today.isoformat()}'
        before = self.client.get(url).data
        self.assertEqual((before['leads'], before['converted_people'], before['converted_enrollments']), (2, 1, 0))
        self.enrollment.source_lead = lead
        self.enrollment.save(update_fields=['source_lead'])
        Enrollment.objects.create(student=self.student, class_group=self.group, start_date=self.today, plan='monthly', amount='100.00', source_lead=lead)
        after = self.client.get(url).data
        self.assertEqual((after['converted_enrollments'], after['enrollment_percent']), (1, Decimal('50.00')))
        communicator = User.objects.create_user(email='com@example.test', password='Movi-test-2026!', access_status='approved', roles=['communication'])
        self.client.force_authenticate(communicator)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_attrition_excludes_unknown_history_and_separates_completed(self):
        start = self.today - timedelta(days=20)
        self.enrollment.start_date = self.today - timedelta(days=40)
        self.enrollment.end_date = self.today + timedelta(days=10)
        self.enrollment.administrative_status = 'cancelled'
        self.enrollment.cancelled_on = self.today - timedelta(days=5)
        self.enrollment.save()
        Enrollment.objects.create(student=self.student, class_group=self.group, start_date=start - timedelta(days=1),
            end_date=self.today - timedelta(days=1), plan='monthly', amount='100.00')
        Enrollment.objects.create(student=self.student, class_group=self.group, start_date=start - timedelta(days=1),
            plan='monthly', amount='100.00')
        Enrollment.objects.create(student=self.student, class_group=self.group, start_date=start - timedelta(days=1),
            end_date=self.today + timedelta(days=10), administrative_status='cancelled', plan='monthly', amount='100.00')
        result = self.client.get(f'/api/reports/attrition/?start={start.isoformat()}&end={self.today.isoformat()}')
        self.assertEqual(result.status_code, 200)
        self.assertEqual((result.data['active_at_start'], result.data['early_cancellations'], result.data['normal_completions']), (2, 1, 1))
        self.assertEqual((result.data['unknown_end'], result.data['unknown_cancellation']), (1, 1))
        self.assertEqual(result.data['percent'], Decimal('50.00'))

    def test_cancellation_date_backfill_uses_only_explicit_audit_date(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        self.enrollment.administrative_status = 'cancelled'
        self.enrollment.save(update_fields=['administrative_status'])
        AuditEvent.objects.create(actor=self.admin, action='enrollment.cancelled', target_type='billing.enrollment',
                                  target_id=str(self.enrollment.pk), metadata={'effective_on': self.today.isoformat()})
        migration = import_module('billing.migrations.0012_enrollment_cancelled_on')
        migration.restore_cancellation_dates(apps, SimpleNamespace(connection=connection))
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.cancelled_on, self.today)

    def charge(self,category='tuition',due=None):
        return Charge.objects.create(enrollment=self.enrollment,category=category,
            competence=self.today.replace(day=1) if category == 'tuition' else None,
            due_date=due or self.today,amount=Decimal('100.00'))

    def receive(self,charge,amount='100.00'):
        return self.client.post(f'/api/charges/{charge.pk}/receive/',
            {'amount':amount,'paid_on':self.today.isoformat(),'method':'pix'},format='json')

    def test_legacy_enrollment_creation_requires_configured_contract(self):
        response = self.client.post('/api/enrollments/',{'student':self.student.pk,'class_group':self.group.pk,
            'start_date':self.today.isoformat(),'plan':'monthly','amount':'100.00'},format='json')
        self.assertEqual(response.status_code,400,response.data)
        self.assertIn('payment_method', response.data)

    def test_enrollment_fee_does_not_release(self):
        self.assertEqual(self.receive(self.charge('enrollment_fee')).status_code,201)
        self.assertIsNot(evaluate_eligibility(self.enrollment)['eligible'],True)

    def test_partial_requires_unique_key_and_preserves_balance(self):
        charge = self.charge()
        self.assertEqual(self.receive(charge,'60.00').status_code,400)
        data = {'amount': '60.00', 'paid_on': self.today.isoformat(), 'method': 'pix', 'request_key': '132bff7d-775a-4482-966a-a77c5bde0172'}
        url = f'/api/charges/{charge.pk}/receive/'
        self.assertEqual(self.client.post(url, data, format='json').status_code, 201)
        self.assertEqual(self.client.post(url, data, format='json').status_code, 200)
        self.assertEqual(self.client.post(url, {**data, 'amount': '50.00'}, format='json').status_code, 400)
        self.assertFalse(charge.is_paid)
        self.assertEqual(charge.received, Decimal('60.00'))
        data.update(amount='40.00', request_key='1b4e99bd-e7ea-4c39-a459-4c4a26a2c001')
        self.assertEqual(self.client.post(url, data, format='json').status_code, 201)
        self.assertTrue(charge.is_paid)
        self.assertEqual(Payment.objects.count(), 2)

    def test_void_payment_requires_coordinator_reopens_balance_and_keeps_audit(self):
        charge = self.charge()
        payload = {'amount': '60.00', 'paid_on': self.today.isoformat(), 'method': 'pix', 'request_key': '132bff7d-775a-4482-966a-a77c5bde0172'}
        payment = self.client.post(f'/api/charges/{charge.pk}/receive/', payload, format='json')
        self.assertEqual(payment.status_code, 201)
        url = f"/api/payments/{payment.data['id']}/void/"
        self.assertEqual(self.client.post(url, {'reason': 'Lançamento incorreto'}, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord-void@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(url, {'reason': 'Lançamento incorreto'}, format='json').status_code, 200)
        self.assertEqual(charge.received, Decimal('0.00'))
        self.assertEqual(self.client.post(f'/api/charges/{charge.pk}/receive/', payload, format='json').status_code, 400)
        self.assertEqual(Decimal(self.client.get('/api/reports/summary/').data['received']), Decimal('0.00'))
        self.assertTrue(AuditEvent.objects.filter(action='payment.voided', reason='Lançamento incorreto').exists())

    def test_refund_is_separate_idempotent_and_does_not_reopen_charge(self):
        charge = self.charge()
        payment = self.receive(charge)
        self.assertEqual(payment.status_code, 201)
        url = f"/api/payments/{payment.data['id']}/refund/"
        payload = {'amount': '40.00', 'refunded_on': self.today.isoformat(), 'method': 'pix', 'reason': 'Devolução aprovada',
                   'request_key': '7a358d45-7289-42a0-966a-5731f47d203e'}
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 403)
        coordinator = User.objects.create_user(email='coord-refund@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.client.force_authenticate(coordinator)
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 201)
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 200)
        self.assertEqual(self.client.post(url, {**payload, 'amount': '61.00', 'request_key': '42723aef-b522-4b43-b4e3-cb0e149da5b5'}, format='json').status_code, 400)
        self.assertTrue(charge.is_paid)
        summary = self.client.get('/api/reports/summary/').data
        self.assertEqual((Decimal(summary['received']), Decimal(summary['refunded'])), (Decimal('60.00'), Decimal('40.00')))
        self.assertEqual(self.client.post(f"/api/payments/{payment.data['id']}/void/", {'reason': 'Tentativa'}, format='json').status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action='payment.refunded', reason='Devolução aprovada').exists())

    def test_excess_not_recorded_without_policy(self):
        charge = self.charge()
        self.assertEqual(self.receive(charge,'101.00').status_code,409)
        self.assertEqual(Payment.objects.count(),0)

    def test_local_date_rollover_changes_eligibility_without_write(self):
        self.charge(due=self.today)
        before = evaluate_eligibility(self.enrollment,on=self.today)
        after = evaluate_eligibility(self.enrollment,on=self.today+timedelta(days=1))
        self.assertEqual(before['status'],'pending')
        self.assertEqual(after['status'],'blocked')

    def test_paid_month_does_not_imply_eternal_coverage(self):
        self.assertEqual(self.receive(self.charge()).status_code,201)
        result = evaluate_eligibility(self.enrollment)
        self.assertIsNone(result['eligible'])
        self.assertIn('DN-004',result['decisions'])

    def test_payment_preserves_cancelled_enrollment(self):
        charge = self.charge()
        response = self.client.post(f'/api/enrollments/{self.enrollment.pk}/cancel/',{'reason':'Encerramento solicitado'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.receive(charge).status_code,201)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.administrative_status,'cancelled')
        self.assertEqual(evaluate_eligibility(self.enrollment)['status'],'cancelled')

    def test_cancel_requires_reason(self):
        for payload in [{},{'reason':None},{'reason':{}},{'reason':'   '}]:
            response = self.client.post(f'/api/enrollments/{self.enrollment.pk}/cancel/',payload,format='json')
            self.assertEqual(response.status_code,400)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.administrative_status,'regular')

    def test_expected_absence_is_explicit_not_adimplente(self):
        result = evaluate_eligibility(self.enrollment)
        self.assertIsNone(result['eligible'])
        self.assertIn('DN-006',result['decisions'])

    @override_settings(BUSINESS_APPROVALS=['DN-013'])
    def test_trial_id_alone_never_grants_unlimited_participation(self):
        self.enrollment.kind = 'trial'
        self.group.allows_trial = True
        self.group.save()
        result = evaluate_eligibility(self.enrollment)
        self.assertIsNone(result['eligible'])
        self.assertIn('DN-013',result['decisions'])
        response = self.client.post('/api/enrollments/',{'student':self.student.pk,'class_group':self.group.pk,
            'start_date':str(self.today),'plan':'monthly','amount':'100.00','kind':'trial'},format='json')
        self.assertEqual(response.status_code,409)

    def test_generation_repeated_is_blocked_without_arbitrary_obligations(self):
        for _ in range(2):
            response = self.client.post('/api/charges/generate/',{},format='json')
            self.assertEqual(response.status_code,409)
        self.assertEqual(Charge.objects.count(),0)

    @override_settings(BUSINESS_APPROVALS=['RN-037'])
    def test_duplicate_manual_competence_under_proposed_uniqueness(self):
        payload = {'enrollment':self.enrollment.pk,'category':'tuition','competence':self.today.replace(day=1).isoformat(),
                   'due_date':self.today.isoformat(),'amount':'100.00'}
        first = self.client.post('/api/charges/',payload,format='json')
        second = self.client.post('/api/charges/',payload,format='json')
        self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(second.status_code,400,second.data)
        self.assertEqual(Charge.objects.count(),1)

    def test_receipt_retry_cannot_duplicate(self):
        charge = self.charge()
        self.assertEqual(self.receive(charge).status_code,201)
        self.assertEqual(self.receive(charge).status_code,409)
        self.assertEqual(Payment.objects.count(),1)

    def test_audit_failure_rolls_back_receipt(self):
        charge = self.charge()
        with patch('billing.views.record',side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                self.receive(charge)
        self.assertEqual(Payment.objects.count(),0)
        self.assertFalse(charge.is_paid)

    def test_reports_conciliate_receipts_categories_and_charge_totals(self):
        for category,amount in [('tuition','100.00'),('enrollment_fee','20.00'),('extra','10.00')]:
            charge = self.charge(category)
            charge.amount = Decimal(amount)
            charge.save()
            self.assertEqual(self.receive(charge,amount).status_code,201)
        response = self.client.get('/api/reports/summary/',{'start':self.today.isoformat(),'end':self.today.isoformat()})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(Decimal(response.data['received']),Decimal('130.00'))
        self.assertEqual(Decimal(response.data['categories']['tuition']),Decimal('100.00'))
        self.assertEqual(Decimal(response.data['expected']),Decimal('130.00'))
        self.assertEqual(Decimal(response.data['outstanding']),Decimal('0.00'))
        self.assertIsNone(response.data['final_payout'])
        self.assertIsNone(response.data['base'])

    def test_charge_status_filters_include_rows_without_payments(self):
        open_charge = self.charge(due=self.today)
        overdue_charge = self.charge(due=self.today-timedelta(days=1))
        paid_charge = self.charge(due=self.today)
        self.assertEqual(self.receive(paid_charge).status_code,201)
        expected = {'open':open_charge.pk,'overdue':overdue_charge.pk,'paid':paid_charge.pk}
        for state,pk in expected.items():
            response = self.client.get('/api/charges/',{'status':state})
            self.assertEqual(response.status_code,200,response.data)
            self.assertEqual([row['id'] for row in response.data['results']],[pk])

    def test_report_filters_and_export_safe_csv(self):
        self.student.name = '=HYPERLINK("example")'
        self.student.save()
        response = self.client.get('/api/reports/export/',{'resource':'students','search':'HYPERLINK'})
        self.assertEqual(response.status_code,200)
        self.assertIn("'=HYPERLINK",response.content.decode('utf-8'))
        response = self.client.get('/api/reports/summary/',{'start':'bad-date'})
        self.assertEqual(response.status_code,400)

    def test_instructor_no_financial_access_even_direct(self):
        user = User.objects.create_user(email='instructor@example.test',password='Movi-test-2026!',access_status='approved',roles=['instructor'])
        self.client.force_authenticate(user)
        for path in ['charges/','payments/','enrollments/','reports/export/']:
            self.assertEqual(self.client.get('/api/'+path).status_code,403)
        summary = self.client.get('/api/reports/summary/').data
        self.assertNotIn('received',summary)
        self.assertNotIn('students',summary)

    def test_communication_summary_does_not_leak_finance(self):
        user = User.objects.create_user(email='communication@example.test',password='Movi-test-2026!',access_status='approved',roles=['communication'])
        self.client.force_authenticate(user)
        summary = self.client.get('/api/reports/summary/').data
        self.assertNotIn('received',summary)
        self.assertIn('leads',summary)

    def test_revoked_role_rechecked(self):
        User.objects.filter(pk=self.admin.pk).update(roles=[],access_status='pending')
        self.assertEqual(self.client.get('/api/charges/').status_code,403)


@skipUnless(connection.vendor == 'postgresql', 'Exige PostgreSQL real e locks de linha.')
@override_settings(BUSINESS_APPROVALS=['RN-037'], PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FinancialConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.users = [User.objects.create_user(email=f'finance{i}@example.test',password='test-only',access_status='approved',roles=['secretary']) for i in range(2)]
        student = Person.objects.create(name='Concorrência sintética')
        modality = Modality.objects.create(name='Atividade',default_price='100.00')
        instructor = Instructor.objects.create(name='Equipe')
        group = ClassGroup.objects.create(name='Oferta',modality=modality,instructor=instructor,
            weekdays=[0],start_time='09:00',end_time='10:00',room='Sala',capacity=10)
        self.today = timezone.localdate()
        self.enrollment = Enrollment.objects.create(student=student,class_group=group,start_date=self.today,plan='monthly',amount='100.00')

    def concurrent_posts(self,path,payload):
        barrier = Barrier(2)
        def worker(user_id):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=user_id))
                barrier.wait(timeout=10)
                return client.post(path,payload,format='json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker,user.pk) for user in self.users]
            return sorted(future.result(timeout=20) for future in futures)

    def test_simultaneous_receipts_record_once(self):
        charge = Charge.objects.create(enrollment=self.enrollment,category='tuition',competence=self.today.replace(day=1),due_date=self.today,amount='100.00')
        statuses = self.concurrent_posts(f'/api/charges/{charge.pk}/receive/',
            {'amount':'100.00','paid_on':str(self.today),'method':'pix'})
        self.assertEqual(statuses,[201,409])
        self.assertEqual(Payment.objects.count(),1)

    def test_simultaneous_proposed_competence_is_not_duplicated(self):
        statuses = self.concurrent_posts('/api/charges/',{'enrollment':self.enrollment.pk,'category':'tuition',
            'competence':str(self.today.replace(day=1)),'due_date':str(self.today),'amount':'100.00'})
        self.assertEqual(statuses,[201,400])
        self.assertEqual(Charge.objects.count(),1)
