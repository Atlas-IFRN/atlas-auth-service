from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, UserRole


class UserDetailPrivacyTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username='student-one',
            password='test-password',
            cpf='11111111111',
            registration_number='20260001',
            first_name='Ana',
            full_name='Ana Student',
            email='ana@example.com',
            role=UserRole.STUDENT,
            ira=88.4,
            period=3,
        )
        cls.other_student = User.objects.create_user(
            username='student-two',
            password='test-password',
            cpf='22222222222',
            registration_number='20260002',
            first_name='Bruno',
            full_name='Bruno Student',
            email='bruno@example.com',
            role=UserRole.STUDENT,
            ira=91.2,
            period=5,
        )
        cls.teacher = User.objects.create_user(
            username='teacher-one',
            password='test-password',
            cpf='33333333333',
            registration_number='19860001',
            first_name='Carla',
            full_name='Carla Teacher',
            email='carla@example.com',
            role=UserRole.TEACHER,
        )

    def get_profile(self, viewer, target):
        self.client.force_authenticate(user=viewer)
        return self.client.get(
            f'/api/auth/users/{target.registration_number}/',
        )

    def test_student_can_see_another_students_registration_but_not_ira(self):
        response = self.get_profile(self.student, self.other_student)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], self.other_student.full_name)
        self.assertEqual(
            response.data['registration_number'],
            self.other_student.registration_number,
        )
        self.assertNotIn('ira', response.data)

    def test_student_can_see_own_registration_and_ira(self):
        response = self.get_profile(self.student, self.student)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['registration_number'],
            self.student.registration_number,
        )
        self.assertEqual(response.data['ira'], self.student.ira)

    def test_teacher_can_see_students_academic_data(self):
        response = self.get_profile(self.teacher, self.other_student)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['registration_number'],
            self.other_student.registration_number,
        )
        self.assertEqual(response.data['ira'], self.other_student.ira)


class UserProfileSocialLinksTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username='social-student',
            password='test-password',
            cpf='44444444444',
            registration_number='20260004',
            first_name='Diego',
            full_name='Diego Student',
            email='diego@example.com',
            role=UserRole.STUDENT,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.student)

    def update_profile(self, **data):
        return self.client.patch('/api/auth/users/me/', data, format='json')

    def test_accepts_and_canonicalizes_supported_profile_urls(self):
        response = self.update_profile(
            github='https://www.github.com/diego-dev',
            linkedin='https://linkedin.com/in/diego-profissional',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['github'], 'https://github.com/diego-dev')
        self.assertEqual(
            response.data['linkedin'],
            'https://www.linkedin.com/in/diego-profissional',
        )

    def test_rejects_external_domains(self):
        response = self.update_profile(
            github='https://example.com/diego-dev',
            linkedin='https://example.com/in/diego-profissional',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('github', response.data)
        self.assertIn('linkedin', response.data)

    def test_rejects_extra_paths_and_url_parameters(self):
        response = self.update_profile(
            github='https://github.com/diego-dev/repositories',
            linkedin='https://www.linkedin.com/in/diego-profissional?ref=atlas',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('github', response.data)
        self.assertIn('linkedin', response.data)

    def test_rejects_insecure_http_profile_urls(self):
        response = self.update_profile(
            github='http://github.com/diego-dev',
            linkedin='http://www.linkedin.com/in/diego-profissional',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('github', response.data)
        self.assertIn('linkedin', response.data)

    def test_does_not_expose_legacy_unsafe_links(self):
        self.student.github = 'https://example.com/diego-dev'
        self.student.linkedin = 'https://example.com/in/diego-profissional'
        self.student.save(update_fields=['github', 'linkedin'])

        response = self.client.get('/api/auth/users/me/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['github'])
        self.assertIsNone(response.data['linkedin'])

    def test_allows_removing_social_profiles(self):
        self.student.github = 'https://github.com/diego-dev'
        self.student.linkedin = 'https://www.linkedin.com/in/diego-profissional'
        self.student.save(update_fields=['github', 'linkedin'])

        response = self.update_profile(github='', linkedin='')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['github'], '')
        self.assertEqual(response.data['linkedin'], '')
