import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django import forms

from ..models import Group, Post, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author = User.objects.create_user(username='test_author')
        cls.groups = [
            Group.objects.create(
                title='Тестовая группа',
                slug='first',
                description='Тестовая группа',
            ),
        ]
        cls.group = cls.groups[0]
        cls.posts = [
            Post.objects.create(
                text='Тестовый пост',
                author=cls.author,
                group=cls.group,
                image=cls.uploaded,
            ),
        ]
        cls.post = cls.posts[0]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        cache.clear()

    def test_correct_template(self):
        """URL-адреса используют правильные шаблоны."""
        url_templates_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:profile', args={self.author.username}):
                'posts/profile.html',
            reverse('posts:post_edit', args={self.post.pk}):
                'posts/create_post.html',
            reverse('posts:post_detail', args={self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:group_list', args={self.group.slug}):
                'posts/group_list.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in url_templates_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_list_context(self):
        """Шаблон получает правильное количество постов."""
        urls_posts = {
            reverse('posts:index'): len(self.posts),
            reverse('posts:profile', args={self.author.username}):
                self.author.posts.count(),
            # урлы страниц групп сюда добавит цикл ниже
        }
        for group in self.groups:
            arg = group.slug
            key = reverse('posts:group_list', args={arg})
            value = group.posts.count()
            urls_posts[key] = value
        for reverse_name, object in urls_posts.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertIn('posts', response.context)
                self.assertEqual(len(response.context['posts']), object)

    def test_post_context(self):
        """Шаблон получает посты с корректным содержимым."""
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', args={self.author.username}),
            reverse('posts:group_list', args={self.group.slug}),
        ]
        for reverse_name in urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                first_object = response.context['posts'][0]
                post_text_0 = first_object.text
                post_author_0 = first_object.author.username
                post_group_0 = first_object.group.title
                self.assertEqual(post_text_0, self.post.text)
                self.assertEqual(post_author_0, self.author.username)
                self.assertEqual(post_group_0, self.group.title)

    def test_post_id_context(self):
        """Шаблон получает пост с корректным id."""
        response = self.authorized_author.get(
            reverse('posts:post_detail', args={self.post.pk})
        )
        post = response.context['post']
        self.assertEqual(post.pk, self.post.pk)

    def test_group_context(self):
        """Пост попадает в корректную группу."""
        response = self.authorized_author.get(
            reverse('posts:group_list', args={self.group.slug})
        )
        post = response.context['posts'][0]
        self.assertEqual(post.pk, self.post.pk)

    def test_form_context(self):
        """Шаблон получает корректные поля формы."""
        urls = [
            reverse('posts:post_edit', args={self.post.pk}),
            reverse('posts:post_create'),
        ]
        for reverse_name in urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                form_fields = {
                    'text': forms.fields.CharField,
                    'group': forms.fields.ChoiceField,
                }
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get('form').fields.get(
                            value)
                        self.assertIsInstance(form_field, expected)

    def test_image_context(self):
        """Шаблон получает посты с изображениями."""
        urls = [
            reverse('posts:index'),
            reverse('posts:profile', args={self.author.username}),
            reverse('posts:group_list', args={self.group.slug}),
        ]
        for reverse_name in urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                first_object = response.context['posts'][0]
                post_image_0 = first_object.image
                self.assertEqual(post_image_0, self.post.image)
        response = self.authorized_author.get(
            reverse('posts:post_detail', args={self.post.pk})
        )
        post = response.context['post']
        self.assertEqual(post.image, self.post.image)


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Описание группы',
        )
        number_of_posts = 13
        cls.posts = []
        for post_id in range(number_of_posts):
            post = Post.objects.create(
                text=f'Тестовый пост {post_id}',
                author=cls.author,
                group=cls.group,
            )
            cls.posts.append(post)
        cls.urls_with_paginator = [
            reverse('posts:index'),
            reverse('posts:profile', args={cls.author.username}),
            reverse('posts:group_list', args={cls.group.slug}),
        ]

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице."""
        for reverse_name in self.urls_with_paginator:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Количество постов на второ странице."""
        for reverse_name in self.urls_with_paginator:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        cache.clear()

    def test_cache_index_page(self):
        """Запись остаётся на странице до принудительной очистки кэша"""
        response = self.authorized_author.get(reverse('posts:index'))
        content = response.content
        Post.objects.create(
            text='Тестовый пост',
            author=self.author,
        )
        response = self.authorized_author.get(reverse('posts:index'))
        self.assertEqual(content, response.content)
        cache.clear()
        response = self.authorized_author.get(reverse('posts:index'))
        self.assertNotEqual(content, response.content)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.follower = User.objects.create_user(username='test_follower')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)

    def test_follow(self):
        """Авторизованный пользователь может подписываться на авторов."""
        self.authorized_follower.get(
            reverse(
                'posts:profile_follow',
                args={self.author.username}
            )
        )
        follow_count = Follow.objects.filter(
            user=self.follower.id,
            author=self.author.id
        ).count()
        self.assertEqual(follow_count, 1)

    def test_unfollow(self):
        """Авторизованный пользователь может отписываться от авторов."""
        Follow.objects.create(user=self.follower, author=self.author)
        self.authorized_follower.get(
            reverse(
                'posts:profile_unfollow',
                args={self.author.username}
            )
        )
        follow_count = Follow.objects.filter(
            user=self.follower.id,
            author=self.author.id
        ).count()
        self.assertEqual(follow_count, 0)

    def test_post_in_follower_index(self):
        """Новая запись автора появляется в ленте подписчиков."""
        post = Post.objects.create(
            text="Тестовый пост",
            author=self.author
        )
        Follow.objects.create(user=self.follower, author=self.author)
        response = self.authorized_follower.get(reverse('posts:follow_index'))
        post = response.context['posts'][0]
        self.assertEqual(post.text, post.text)

    def test_post_not_in_user_index(self):
        """Новой записи автора нет в ленте неподписанных пользователей."""
        post = Post.objects.create(
            text="Тестовый пост",
            author=self.author
        )
        Follow.objects.create(user=self.follower, author=self.author)
        user = User.objects.create_user(username='test_user')
        authorized_user = Client()
        authorized_user.force_login(user)
        response = authorized_user.get(reverse('posts:follow_index'))
        posts = response.context['posts']
        self.assertNotIn(post, posts)
