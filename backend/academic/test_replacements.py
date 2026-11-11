from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import AuditEvent, ClassGroup, Instructor, Modality, User
from .models import Lesson


class ReplacementTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='secretary@example.test', password='password', access_status='approved', roles=['secretary'])
        self.client.force_authenticate(self.user)
        self.modality = Modality.objects.create(name='Dança', default_price='100.00')
        self.instructor = Instructor.objects.create(name='Instrutor')
        self.instructor.specialties.add(self.modality)
        self.group = ClassGroup.objects.create(name='Turma', modality=self.modality, instructor=self.instructor,
            weekdays=[0], start_time='09:00', end_time='10:00', room='Sala', capacity=10)
        self.today = timezone.localdate()
        self.original = Lesson.objects.create(class_group=self.group, date=self.today, status='cancelled')
        self.target = self.today + timedelta(days=1)

    def request_replacement(self):
        return self.client.post(f'/api/lessons/{self.original.pk}/replacement/', {'date': self.target.isoformat(),
            'start_time': '09:00', 'end_time': '10:00', 'instructor': self.instructor.pk, 'reason': 'Reposição autorizada'}, format='json')

    def test_replacement_preserves_original_and_audit(self):
        response = self.request_replacement()
        self.assertEqual(response.status_code, 201, response.data)
        replacement = Lesson.objects.get(pk=response.data['id'])
        self.assertEqual(replacement.replacement_for_id, self.original.pk)
        self.assertEqual(self.original.status, 'cancelled')
        self.assertTrue(AuditEvent.objects.filter(action='lesson.replacement_created', reason='Reposição autorizada').exists())
        self.assertEqual(self.client.patch(f'/api/lessons/{replacement.pk}/', {'date': (self.target + timedelta(days=1)).isoformat()}, format='json').status_code, 400)

    def test_conflicting_recurring_class_blocks_replacement(self):
        ClassGroup.objects.create(name='Outra', modality=self.modality, instructor=self.instructor,
            weekdays=[self.target.weekday()], start_time='09:30', end_time='10:30', room='Outra sala', capacity=10)
        response = self.request_replacement()
        self.assertEqual(response.status_code, 400)
        self.assertIn('instructor', response.data)
        self.assertEqual(Lesson.objects.count(), 1)
