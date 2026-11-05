from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PersonMigrationTests(TransactionTestCase):
    def test_existing_identity_relations_audit_and_permission_grants_survive(self):
        call_command('migrate', 'ecowork', '0001_initial', verbosity=0)
        call_command('migrate', 'core', '0003_ecowork_residence_foundation', verbosity=0)
        try:
            executor = MigrationExecutor(connection)
            state = executor.loader.project_state([
                ('core', '0003_ecowork_residence_foundation'),
                ('billing', '0004_collectionmessage'), ('ecowork', '0001_initial'),
                ('academic', '0001_initial'),
            ]).apps
            person = state.get_model('core', 'Student').objects.create(name='Cadastro preservado', phone='11999999999')
            lead = state.get_model('core', 'Lead').objects.create(name='Lead convertido', status='converted', student_id=person.pk)
            user = state.get_model('core', 'User').objects.create(username='migration', email='migration@example.test')
            content_type = state.get_model('contenttypes', 'ContentType').objects.get(app_label='core', model='student')
            permission = state.get_model('auth', 'Permission').objects.get(content_type=content_type, codename='view_student')
            user.user_permissions.add(permission)
            event = state.get_model('core', 'AuditEvent').objects.create(action='student.create', target_type='core.student', target_id=str(person.pk))
            order = state.get_model('ecowork', 'Order').objects.create(
                person_id=person.pk, product='monthly', product_name='Mensal', months=1, quantity=1,
                base_price='169', discount_percent=0, total='169', billing_mode='cash', installments=1,
                first_due='2026-11-05', actor_id=user.pk, request_key='680dc77f-aef9-4605-913b-a8cd4255c641', request_hash='migration',
            )
            charge = state.get_model('ecowork', 'Charge').objects.create(order_id=order.pk, number=1, amount='169', due_date='2026-11-05')
            payment = state.get_model('ecowork', 'Payment').objects.create(charge_id=charge.pk, amount='169', paid_on='2026-11-05', method='pix', actor_id=user.pk, request_key='680dc77f-aef9-4605-913b-a8cd4255c642')
            call_command('migrate', verbosity=0)
            from core.models import AuditEvent, Lead, Person, User
            from ecowork.models import Order, Charge, Payment
            from django.contrib.auth.models import Permission
            from django.contrib.contenttypes.models import ContentType
            self.assertEqual(Person.objects.get(pk=person.pk).phone, '11999999999')
            self.assertEqual(Lead.objects.get(pk=lead.pk).student_id, person.pk)
            self.assertEqual(Order.objects.get(pk=order.pk).person_id, person.pk)
            self.assertEqual(Charge.objects.get(pk=charge.pk).payment.pk, payment.pk)
            self.assertEqual(str(Payment.objects.get(pk=payment.pk).amount), '169.00')
            self.assertIsNone(Payment.objects.get(pk=payment.pk).voided_at)
            self.assertIsNone(Order.objects.get(pk=order.pk).cancelled_at)
            self.assertEqual(AuditEvent.objects.get(pk=event.pk).target_type, 'core.student')
            self.assertEqual(ContentType.objects.get(pk=content_type.pk).model, 'person')
            self.assertEqual(Permission.objects.get(pk=permission.pk).codename, 'view_person')
            self.assertTrue(User.objects.get(pk=user.pk).user_permissions.filter(pk=permission.pk).exists())
            self.assertEqual(Person._meta.db_table, 'core_student')
        finally:
            call_command('migrate', verbosity=0)
