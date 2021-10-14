import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        test_image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='test.gif',
            content=test_image,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Новый пост',
            'author': self.author,
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', args={self.author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, form_data['author'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertTrue(
            Post.objects.filter(image='posts/test.gif').exists()
        )

    def test_edit_post(self):
        """Валидная форма изменяет запись в Post."""
        posts_count = Post.objects.count()
        post_id = self.post.pk
        form_data = {
            'text': 'Измененный пост',
        }
        response = self.authorized_author.post(
            reverse('posts:post_edit', args={self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args={self.post.pk})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(post_id, self.post.pk)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
            ).exists()
        )

    def test_guest_cant_create_post(self):
        """Неавторизированный пользователь не создаёт пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Пост гостя',
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create')
        )
        self.assertFalse(
            Post.objects.filter(text=form_data['text'],).exists()
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        post = self.post
        comments_count = post.comments.count()
        form_data = {
            'text': 'Новый комментарий',
            'author': self.author,
        }
        response = self.authorized_author.post(
            reverse('posts:add_comment', args={self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', args={self.post.pk})
        )
        self.assertEqual(self.post.comments.count(), comments_count + 1)

        comment = Comment.objects.first()
        print(comment)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, form_data['author'])

    def test_guest_cant_create_comment(self):
        """Неавторизированный пользователь не создаёт комментарий."""
        post = self.post
        comments_count = post.comments.count()
        form_data = {
            'text': 'Комментарий гостя',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', args={self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(self.post.comments.count(), comments_count)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse(
                'posts:add_comment',
                args={self.post.pk}
            )
        )
        self.assertFalse(
            Post.objects.filter(text=form_data['text'],).exists()
        )
