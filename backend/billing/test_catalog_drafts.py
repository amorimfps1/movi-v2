from rest_framework.test import APITestCase
from django.utils import timezone

from core.models import AuditEvent, User
from .models import FinancialCatalogVersion


class CatalogDraftTests(APITestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(email='coord@example.test', password='password', access_status='approved', roles=['coordinator'])
        self.secretary = User.objects.create_user(email='secretary@example.test', password='password', access_status='approved', roles=['secretary'])
        self.client.force_authenticate(self.coordinator)

    def test_invalid_draft_is_audited_and_cannot_be_published(self):
        response = self.client.post('/api/financial-catalogs/', {'effective_from': '2026-01-01', 'configuration': {'example': 'draft'}}, format='json')
        self.assertEqual(response.status_code, 201)
        catalog_id = response.data['id']
        self.assertEqual(response.data['version'], 1)
        response = self.client.patch(f'/api/financial-catalogs/{catalog_id}/', {'configuration': {'example': 'updated'}}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AuditEvent.objects.filter(action='financial_catalog.update', target_id=str(catalog_id)).exists())
        self.assertEqual(self.client.post(f'/api/financial-catalogs/{catalog_id}/publish/', {}, format='json').status_code, 400)
        self.assertEqual(FinancialCatalogVersion.objects.get(pk=catalog_id).status, 'draft')

    def test_valid_catalog_can_be_published_once_and_is_immutable(self):
        config = {'plans': {'quarterly': {'months': 3, 'installments': [1, 2, 3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '99.90'}],
                  'fees': {'standard': {'associated': '25.00', 'non_associated': '35.00'}}}
        response = self.client.post('/api/financial-catalogs/', {'effective_from': '2026-01-01', 'configuration': config}, format='json')
        url = f"/api/financial-catalogs/{response.data['id']}/"
        revision = self.client.post(url + 'preview/', {}, format='json').data['revision']
        self.assertEqual(self.client.post(url + 'publish/', {'reason': 'Tabela aprovada', 'revision': revision}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'configuration': {}}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url + 'publish/', {'reason': 'Novamente'}, format='json').status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action='financial_catalog.publish', reason='Tabela aprovada').exists())

    def test_secretary_cannot_create_or_list_catalogs(self):
        self.client.force_authenticate(self.secretary)
        self.assertEqual(self.client.get('/api/financial-catalogs/').status_code, 403)
        self.assertEqual(self.client.post('/api/financial-catalogs/', {'effective_from': '2026-01-01', 'configuration': {}}, format='json').status_code, 403)

    def test_preview_validates_and_rejects_duplicate_prices(self):
        config = {'plans': {'quarterly': {'months': 3, 'installments': [1, 2, 3]}},
                  'prices': [{'category': 1, 'plan': 'quarterly', 'method': 'card', 'associated': False, 'amount': '99.90'}],
                  'fees': {'standard': {'associated': '25.00', 'non_associated': '35.00'}}}
        created = self.client.post('/api/financial-catalogs/', {'effective_from': '2026-01-01', 'configuration': config}, format='json')
        url = f"/api/financial-catalogs/{created.data['id']}/"
        self.assertTrue(self.client.post(url + 'preview/', {}, format='json').data['valid'])
        config['prices'].append(config['prices'][0].copy())
        self.client.patch(url, {'configuration': config}, format='json')
        self.assertFalse(self.client.post(url + 'preview/', {}, format='json').data['valid'])

    def test_preview_detects_overlapping_published_period(self):
        FinancialCatalogVersion.objects.create(version=1, status='published', effective_from='2026-01-01',
            effective_until='2026-12-31', configuration={}, created_by=self.coordinator,
            published_by=self.coordinator, published_at=timezone.now())
        draft = self.client.post('/api/financial-catalogs/', {'effective_from': '2026-12-31', 'configuration': {}}, format='json')
        preview = self.client.post(f"/api/financial-catalogs/{draft.data['id']}/preview/", {}, format='json')
        self.assertEqual(preview.data['conflicting_versions'], [1])
        self.assertFalse(preview.data['valid'])

    def test_publication_refuses_stale_preview(self):
        draft = self.client.post('/api/financial-catalogs/', {'effective_from': '2026-01-01', 'configuration': {}}, format='json')
        url = f"/api/financial-catalogs/{draft.data['id']}/"
        revision = self.client.post(url + 'preview/', {}, format='json').data['revision']
        self.client.patch(url, {'effective_from': '2026-02-01'}, format='json')
        result = self.client.post(url + 'publish/', {'reason': 'Aprovação', 'revision': revision}, format='json')
        self.assertEqual(result.status_code, 400)
        self.assertIn('revision', result.data)
