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

    def test_student_cannot_see_another_students_registration_or_ira(self):
        response = self.get_profile(self.student, self.other_student)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], self.other_student.full_name)
        self.assertNotIn('registration_number', response.data)
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
