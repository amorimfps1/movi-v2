from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import User, Student, Modality, Instructor, ClassGroup, AuditEvent
from .models import Enrollment, Charge, Payment
from .services import evaluate_eligibility

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection, close_old_connections, connections
from django.test import TransactionTestCase


class FinancialTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='finance@example.test',password='Movi-test-2026!',access_status='approved',roles=['secretary'])
        self.student = Student.objects.create(name='Aluno de teste')
        modality = Modality.objects.create(name='Música',default_price='100.00')
        instructor = Instructor.objects.create(name='Instrutor de teste')
        self.group = ClassGroup.objects.create(name='Grupo de teste',modality=modality,instructor=instructor,
            weekdays=[0],start_time='09:00',end_time='10:00',room='Sala',capacity=10)
        self.today = timezone.localdate()
        self.enrollment = Enrollment.objects.create(student=self.student,class_group=self.group,start_date=self.today,
            plan='monthly',amount='100.00')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def charge(self,category='tuition',due=None):
        return Charge.objects.create(enrollment=self.enrollment,category=category,
            competence=self.today.replace(day=1) if category == 'tuition' else None,
            due_date=due or self.today,amount=Decimal('100.00'))

    def receive(self,charge,amount='100.00'):
        return self.client.post(f'/api/charges/{charge.pk}/receive/',
            {'amount':amount,'paid_on':self.today.isoformat(),'method':'pix'},format='json')

    def test_new_enrollment_pending(self):
        response = self.client.post('/api/enrollments/',{'student':self.student.pk,'class_group':self.group.pk,
            'start_date':self.today.isoformat(),'plan':'monthly','amount':'100.00'},format='json')
        self.assertEqual(response.status_code,201,response.data)
        self.assertIsNot(response.data['eligibility']['eligible'],True)
        self.assertEqual(response.data['administrative_status'],'regular')

    def test_enrollment_fee_does_not_release(self):
        self.assertEqual(self.receive(self.charge('enrollment_fee')).status_code,201)
        self.assertIsNot(evaluate_eligibility(self.enrollment)['eligible'],True)

    def test_underpaid_not_settled_and_no_partial_write(self):
        charge = self.charge()
        self.assertEqual(self.receive(charge,'60.00').status_code,409)
        self.assertFalse(charge.is_paid)
        self.assertEqual(Payment.objects.count(),0)

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
        student = Student.objects.create(name='Concorrência sintética')
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
