from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from academic.models import Lesson
from academic.services import roster
from billing.models import Charge, CommercialCondition, Enrollment, Payment
from billing.services import evaluate_eligibility
from core.models import AuditEvent, ClassGroup, Instructor, Lead, Modality, OperationLock, Student, User


@override_settings(DEBUG=True, DEMO_MODE=True, ATTENDANCE_POLICY=None, BUSINESS_APPROVALS=[],
                   PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SeedDemoTests(TestCase):
    today = date(2026, 11, 4)
    password = 'Synthetic-demo-2026!'
    models = (User, Student, Modality, Instructor, ClassGroup, Lead, Enrollment,
              CommercialCondition, Charge, Payment, Lesson, AuditEvent, OperationLock)

    def seed(self, **options):
        with patch('billing.management.commands.seed_demo.timezone.localdate', return_value=self.today):
            call_command('seed_demo', password=self.password, stdout=StringIO(), **options)

    def test_contracts_accounts_and_roster_are_usable(self):
        self.seed()
        for role, email in [('coordinator', 'coordenacao'), ('secretary', 'secretaria'),
                            ('instructor', 'instrutor'), ('communication', 'comunicacao')]:
            user = User.objects.get(email=f'{email}@example.test')
            self.assertEqual(user.roles, [role])
            self.assertEqual(user.access_status, 'approved')
            self.assertTrue(user.check_password(self.password))
        self.assertFalse(User.objects.get(email='solicitante@example.test').has_usable_password())
        self.assertEqual(Student.objects.count(), 14)
        self.assertFalse(Student.objects.exclude(cpf='').exists())
        self.assertEqual(set(Lead.objects.values_list('status', flat=True)), set(Lead.Status.values))
        expected = {
            'Regular trimestral': 'regular', 'Aguardando ativação': 'pending',
            'Parcela em atraso': 'blocked', 'Cancelado': 'cancelled',
            'Regular anual associado': 'regular', 'Somente taxa paga': 'pending',
        }
        for prefix, status in expected.items():
            enrollment = Enrollment.objects.get(student__name=f'{prefix} • demonstração')
            self.assertEqual(enrollment.contract_version, 1)
            self.assertEqual(evaluate_eligibility(enrollment, self.today)['status'], status)
            tuition = enrollment.charges.filter(category='tuition')
            self.assertEqual(tuition.count(), enrollment.installments)
            self.assertEqual(sum(charge.amount for charge in tuition), enrollment.amount)
            self.assertEqual(enrollment.charges.get(category='enrollment_fee').amount, enrollment.fee_amount)
            self.assertEqual(enrollment.conditions.count(), 1)
        lesson = Lesson.objects.get(class_group__name='Contratos 1 • turma de demonstração', date=self.today)
        instructor = User.objects.get(email='instrutor@example.test')
        result = roster(instructor.pk, lesson.pk)
        self.assertEqual(len(result['participants']), 2)
        self.assertEqual(len(result['excluded']), 1)
        self.assertEqual(result['decisions'], [])

    def test_rerun_preserves_manual_changes_and_passwords_even_on_another_day(self):
        self.seed()
        student = Student.objects.first()
        student.name = 'Nome editado manualmente'
        student.save()
        user = User.objects.get(email='secretaria@example.test')
        user.set_password('Changed-password-2026!')
        user.save()
        before = {model: list(model.objects.order_by('pk').values()) for model in self.models}
        self.today = date(2026, 12, 4)
        self.seed()
        self.assertEqual(before, {model: list(model.objects.order_by('pk').values()) for model in self.models})
        with self.assertRaisesMessage(CommandError, 'outra data'):
            self.seed(date=self.today)

    def test_requires_both_demo_flags(self):
        for flags in [{'DEBUG': False}, {'DEMO_MODE': False}]:
            with self.subTest(flags=flags), override_settings(**flags):
                with self.assertRaisesMessage(CommandError, 'DEBUG=true e DEMO_MODE=true'):
                    self.seed()
        self.assertFalse(OperationLock.objects.exists())
        self.assertFalse(User.objects.exists())

    def test_refuses_populated_database_even_without_students_or_users(self):
        modality = Modality.objects.create(name='Existing', default_price='10.00')
        with self.assertRaisesMessage(CommandError, 'banco vazio'):
            self.seed()
        self.assertEqual(list(Modality.objects.values_list('pk', flat=True)), [modality.pk])
        self.assertFalse(OperationLock.objects.exists())
        self.assertFalse(User.objects.exists())

    def test_invalid_password_and_dates_do_not_write(self):
        self.password = 'short'
        with self.assertRaisesMessage(CommandError, '12 caracteres'):
            self.seed()
        self.password = 'Synthetic-demo-2026!'
        for reference, message in [(date(2025, 11, 4), 'tabela contratual'),
                                   (date(2026, 12, 31), 'futuro')]:
            with self.subTest(reference=reference), self.assertRaisesMessage(CommandError, message):
                self.seed(date=reference)
        self.assertFalse(OperationLock.objects.exists())
        self.assertFalse(User.objects.exists())

    def test_failure_rolls_back_entire_seed_and_can_be_retried(self):
        with patch('billing.management.commands.seed_demo.generate', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesMessage(RuntimeError, 'interrupted'):
                self.seed()
        for model in self.models:
            self.assertFalse(model.objects.exists(), model.__name__)
        self.seed()
        self.assertEqual(Enrollment.objects.filter(contract_version=1).count(), 6)

    def test_upgrades_legacy_demo_without_changing_legacy_records(self):
        from billing.management.commands.seed_demo import Command

        instructor = User.objects.create_user(email='instrutor@example.test', password=self.password,
                                               roles=['instructor'], access_status='approved')
        secretary = User.objects.create_user(email='secretaria@example.test', password=self.password,
                                              roles=['secretary'], access_status='approved')
        Command().seed_legacy(self.today, {'instructor': instructor}, secretary)
        OperationLock.objects.create(key='demo-seeded')
        legacy = list(Enrollment.objects.order_by('pk').values())
        self.seed()
        self.assertEqual(list(Enrollment.objects.filter(contract_version=0).order_by('pk').values()), legacy)
        self.assertEqual(Enrollment.objects.count(), 14)

    def test_january_reference_does_not_require_unavailable_previous_year_prices(self):
        self.seed(date=date(2026, 1, 1))
        self.assertEqual(Enrollment.objects.filter(contract_version=1).count(), 6)
        self.assertTrue(Student.objects.filter(name='Aguardando vencimento • demonstração').exists())
