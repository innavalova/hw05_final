from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from http import HTTPStatus

User = get_user_model()


class UserURLTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_user')
        cls.uid = 'test-uid'
        cls.token = 'test-token'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_urls_exists(self):
        """Страницы доступны."""
        open_urls_names = [
            '/auth/signup/',
            '/auth/login/',
            '/auth/password_reset/',
            '/auth/password_reset/done/',
            f'/auth/reset/{self.uid}/{self.token}/',
            '/auth/reset/done/',
            '/auth/logout/',
        ]
        for adress in open_urls_names:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)
        closed_urls_names = [
            '/auth/password_change/',
            '/auth/password_change/done/',
        ]
        for adress in closed_urls_names:
            with self.subTest(adress=adress):
                response = self.authorized_user.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_404(self):
        """Несуществующая страница отвечает 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_redirect(self):
        """Страницы правильно перенаправляют."""
        closed_urls_names = [
            '/auth/password_change/',
            '/auth/password_change/done/',
        ]
        for adress in closed_urls_names:
            with self.subTest(adress=adress):
                response = self.guest_client.get(adress, follow=True)
                self.assertRedirects(
                    response, (f'/auth/login/?next={adress}'))

    def test_correct_template(self):
        """URL-адреса используют правильные шаблоны."""
        url_templates_names = {
            reverse('users:signup'): 'users/signup.html',
            reverse('users:login'): 'users/login.html',
            reverse('users:password_reset_form'):
                'users/password_reset_form.html',
            reverse('users:password_reset_done'):
                'users/password_reset_done.html',
            # f'/auth/reset/{self.uid}/{self.token}/':
            # 'users/password_reset_confirm.html',
            reverse('users:password_reset_confirm',
                    kwargs={'uidb64': self.uid, 'token': self.token}):
                'users/password_reset_confirm.html',
            reverse('users:password_reset_complete'):
                'users/password_reset_complete.html',
            reverse('users:password_change_form'):
                'users/password_change_form.html',
            reverse('users:password_change_done'):
                'users/password_change_done.html',
            reverse('users:logout'): 'users/logged_out.html',
        }
        for adress, template in url_templates_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_user.get(adress)
                self.assertTemplateUsed(response, template)
