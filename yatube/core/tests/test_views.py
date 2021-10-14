from django.test import TestCase, Client


class PostViewTests(TestCase):

    def setUp(self):
        self.user = Client()

    def test_correct_404_template(self):
        """Несуществующая страница использует правильный шаблон."""
        response = self.user.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')
