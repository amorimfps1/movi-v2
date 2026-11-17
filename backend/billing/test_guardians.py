from django.test import TestCase
from core.models import Lead, Person, User
from .models import Enrollment


class GuardianEnrollmentTests(TestCase):
    def setUp(self):
        from .tests import FinancialTests
        FinancialTests.setUp(self)
        modality = self.group.modality
        modality.price_category = 1
        modality.enrollment_fee_kind = 'standard'
        modality.save()
        self.group.capacity = 100
        self.group.save(update_fields=['capacity'])
        self.payload = {'student': self.student.pk, 'class_group': self.group.pk,
            'start_date': self.today.isoformat(), 'plan': 'quarterly',
            'payment_method': 'card', 'installments': 3, 'is_minor': True}

    def test_new_guardian_is_a_person_and_filterable(self):
        self.payload['guardian_data'] = {'name': 'Responsável de teste', 'email': 'responsavel@example.test', 'phone': '11999999999'}
        response = self.client.post('/api/enrollments/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        enrollment = Enrollment.objects.get(pk=response.data['id'])
        self.assertTrue(enrollment.is_minor)
        self.assertEqual(enrollment.guardian.name, 'Responsável de teste')
        person = self.client.get(f'/api/people/{enrollment.guardian_id}/')
        self.assertTrue(person.data['has_guardianships'])
        people = self.client.get('/api/people/?has_guardianships=true')
        self.assertIn(enrollment.guardian_id, [row['id'] for row in people.data['results']])

    def test_existing_guardian_can_be_reused_without_overwrite(self):
        guardian = Person.objects.create(name='Pessoa existente', email='responsavel@example.test')
        self.payload['guardian_data'] = {'id': guardian.pk}
        response = self.client.post('/api/enrollments/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['guardian'], guardian.pk)
        self.assertEqual(Person.objects.filter(email=guardian.email).count(), 1)

    def test_rejects_missing_or_duplicate_guardian_without_creating_enrollment(self):
        self.assertEqual(self.client.post('/api/enrollments/', self.payload, format='json').status_code, 400)
        self.payload['guardian_data'] = {'id': self.student.pk}
        self.assertEqual(self.client.post('/api/enrollments/', self.payload, format='json').status_code, 400)
        Person.objects.create(name='Existente', email='igual@example.test')
        self.payload['guardian_data'] = {'name': 'Outro', 'email': 'igual@example.test'}
        self.assertEqual(self.client.post('/api/enrollments/', self.payload, format='json').status_code, 400)
        self.assertFalse(Enrollment.objects.filter(is_minor=True).exists())

    def test_converted_lead_filter_uses_student_and_keeps_permissions(self):
        other = Person.objects.create(name='Outra pessoa')
        own = Lead.objects.create(name='Lead correto', status='converted', student=self.student)
        Lead.objects.create(name='Lead de outra pessoa', status='converted', student=other)
        Lead.objects.create(name='Lead ainda não convertido')
        result = self.client.get('/api/leads/', {'status': 'converted', 'student': self.student.pk})
        self.assertEqual([row['id'] for row in result.data['results']], [own.pk])
        user = User.objects.create_user(email='comunicacao@example.test', password='password', access_status='approved', roles=['communication'])
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get('/api/leads/', {'student': self.student.pk}).status_code, 403)
