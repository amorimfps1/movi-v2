from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from billing.services import ensure_class_capacity
from core.models import AuditEvent, ClassGroup, Instructor, Lead, Modality, Person, User
from .models import Lesson, TrialParticipation


class TrialTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.admin = User.objects.create_user(email='secretary@example.test', password='password', access_status='approved', roles=['secretary'])
        self.teacher = User.objects.create_user(email='teacher@example.test', password='password', access_status='approved', roles=['instructor'])
        modality = Modality.objects.create(name='Dança', default_price='100.00')
        instructor = Instructor.objects.create(name='Instrutor', user=self.teacher)
        self.group = ClassGroup.objects.create(name='Turma', modality=modality, instructor=instructor, weekdays=[0], start_time='09:00', end_time='10:00', room='Sala', capacity=1, allows_trial=True)
        self.lesson = Lesson.objects.create(class_group=self.group, date=self.today)
        self.person = Person.objects.create(name='Menor', birth_date=self.today.replace(year=self.today.year - 10))
        self.client.force_authenticate(self.admin)

    def schedule(self, guardian=True):
        return self.client.post('/api/trials/', {'person': self.person.pk, 'lesson': self.lesson.pk, 'guardian_authorization': guardian}, format='json')

    def test_minor_authorization_uniqueness_capacity_and_attendance(self):
        self.assertEqual(self.schedule(False).status_code, 400)
        created = self.schedule()
        self.assertEqual(created.status_code, 201, created.data)
        occupancy = self.client.get('/api/reports/occupancy/').data['classes'][0]
        self.assertEqual(occupancy['experimental'], 1)
        self.assertEqual(occupancy['regular'], 0)
        self.assertEqual(self.schedule().status_code, 400)
        other = Person.objects.create(name='Outra')
        with self.assertRaises(ValidationError):
            ensure_class_capacity(self.group, self.today, self.today + timedelta(days=10), other.pk)
        ensure_class_capacity(self.group, self.today, self.today + timedelta(days=10), self.person.pk)
        self.lesson.status = 'completed'
        self.lesson.save(update_fields=['status'])
        self.client.force_authenticate(self.teacher)
        marked = self.client.post(f"/api/trials/{created.data['id']}/mark/", {'present': True}, format='json')
        self.assertEqual(marked.status_code, 200, marked.data)
        self.assertTrue(marked.data['present'])
        self.assertTrue(AuditEvent.objects.filter(action='trial.marked').exists())
        corrected = self.client.post(f"/api/trials/{created.data['id']}/correct/", {'present': False, 'reason': 'Correção conferida'}, format='json')
        self.assertEqual(corrected.status_code, 200)
        event = AuditEvent.objects.get(action='trial.corrected')
        self.assertEqual((event.metadata['before'], event.metadata['after']), (True, False))

    def test_cancelled_lesson_preserves_trial_and_allows_rescheduling(self):
        created = self.schedule()
        self.assertEqual(created.status_code, 201, created.data)
        response = self.client.patch(f'/api/lessons/{self.lesson.pk}/', {'status': 'cancelled'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        trial = TrialParticipation.objects.get(pk=created.data['id'])
        self.assertEqual(trial.status, 'cancelled')
        self.assertTrue(AuditEvent.objects.filter(action='trial.cancelled', reason='Aula cancelada.').exists())

    def test_archiving_person_cancels_scheduled_trial_with_history(self):
        created = self.schedule()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.client.patch(f'/api/people/{self.person.pk}/', {'archived': True}, format='json').status_code, 200)
        self.assertEqual(TrialParticipation.objects.get(pk=created.data['id']).status, 'cancelled')
        self.assertTrue(AuditEvent.objects.filter(action='trial.cancelled', reason='Pessoa arquivada.').exists())

    def test_lead_and_trial_are_created_atomically_and_conversion_keeps_person(self):
        payload = {'name': 'Menor', 'trial': {'lesson': self.lesson.pk, 'person': self.person.pk,
            'birth_date': self.person.birth_date.isoformat(), 'guardian_authorization': False}}
        self.assertEqual(self.client.post('/api/leads/', payload, format='json').status_code, 400)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(TrialParticipation.objects.exists())
        payload['trial']['guardian_authorization'] = True
        created = self.client.post('/api/leads/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        lead = Lead.objects.get(pk=created.data['id'])
        self.assertEqual(lead.lead_trials.get().person, self.person)
        self.assertEqual(created.data['trial_info']['lesson'], self.lesson.pk)
        filtered = self.client.get('/api/leads/', {'trial_status': 'scheduled'})
        self.assertEqual([row['id'] for row in filtered.data['results']], [lead.pk])
        self.assertEqual(self.client.get('/api/leads/', {'trial_status': 'none'}).data['count'], 0)
        converted = self.client.post(f'/api/leads/{lead.pk}/convert/', {}, format='json')
        self.assertEqual(converted.status_code, 200, converted.data)
        self.assertEqual(converted.data['student'], self.person.pk)

    def test_lead_trial_rejects_implicit_duplicate_and_rolls_back(self):
        self.person.email = 'menor@example.test'
        self.person.save()
        payload = {'name': 'Menor', 'email': self.person.email, 'trial': {'lesson': self.lesson.pk,
            'birth_date': self.person.birth_date.isoformat(), 'guardian_authorization': True}}
        response = self.client.post('/api/leads/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(Person.objects.count(), 1)

    def test_new_person_created_for_trial_is_reused_and_capacity_failure_rolls_back(self):
        payload = {'name': 'Nova pessoa', 'trial': {'lesson': self.lesson.pk,
            'birth_date': '2000-01-01', 'guardian_authorization': False}}
        created = self.client.post('/api/leads/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        lead = Lead.objects.get(pk=created.data['id'])
        person_id = lead.lead_trials.get().person_id
        converted = self.client.post(f'/api/leads/{lead.pk}/convert/', {}, format='json')
        self.assertEqual(converted.status_code, 200, converted.data)
        self.assertEqual(converted.data['student'], person_id)
        payload['name'] = 'Sem vaga'
        response = self.client.post('/api/leads/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Lead.objects.filter(name='Sem vaga').exists())
        self.assertFalse(Person.objects.filter(name='Sem vaga').exists())

    def test_trial_lesson_options_exclude_inactive_or_ineligible_groups(self):
        response = self.client.get('/api/lessons/', {'trial_available': 'true'})
        self.assertEqual([row['id'] for row in response.data['results']], [self.lesson.pk])
        self.group.allows_trial = False
        self.group.save(update_fields=['allows_trial'])
        self.assertEqual(self.client.get('/api/lessons/', {'trial_available': 'true'}).data['count'], 0)
