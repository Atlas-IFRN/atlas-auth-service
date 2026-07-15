from django.test import TestCase
from rest_framework.test import APIClient

from .audit import clear_current_actor_id, set_current_actor_id
from .models import AuditLog, User


class AuthenticationAuditSignalsTests(TestCase):
    def tearDown(self):
        clear_current_actor_id()

    def test_user_changes_are_audited_without_sensitive_fields(self):
        user = User.objects.create_user(
            username='audit-user',
            cpf='00000000000',
            registration_number='202600000001',
            full_name='Usuário auditado',
            password='secret-password',
        )
        set_current_actor_id(user.id)
        user.about_me = 'Perfil atualizado'
        user.save()
        user_id = user.id
        user.delete()

        logs = AuditLog.objects.filter(table_name='user', record_id=user_id)
        self.assertEqual(
            set(logs.values_list('action', flat=True)),
            {'CREATE', 'UPDATE', 'DELETE'},
        )
        update_payload = logs.get(action='UPDATE').payload
        self.assertNotIn('password', update_payload['after'])
        self.assertNotIn('cpf', update_payload['after'])


class AuditIdentityBatchTests(TestCase):
    def setUp(self):
        self.request_user = User.objects.create_user(
            username='audit-viewer',
            cpf='00000000001',
            registration_number='202600000010',
            full_name='Responsável pela auditoria',
        )
        self.other_user = User.objects.create_user(
            username='audited-actor',
            cpf='00000000002',
            registration_number='202600000011',
            full_name='Responsável auditado',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.request_user)

    def test_resolves_multiple_registrations_with_one_query(self):
        with self.assertNumQueries(1):
            response = self.client.post(
                '/api/auth/users/audit-identities/',
                {
                    'ids': [
                        str(self.request_user.id),
                        str(self.other_user.id),
                        str(self.other_user.id),
                    ],
                },
                format='json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {tuple(item.keys()) for item in response.data},
            {('id', 'registration_number')},
        )
        self.assertEqual(
            {item['registration_number'] for item in response.data},
            {'202600000010', '202600000011'},
        )
