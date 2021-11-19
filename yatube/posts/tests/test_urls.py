from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            group=cls.group,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = PostsURLTests.user
        self.user_author = PostsURLTests.user_author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.user_author)

    def test_pages_status(self):
        """Проверяем доступность страниц."""
        url_names = [
            '/',
            '/about/author/',
            '/about/tech/',
            '/group/test/',
            '/profile/auth/',
            '/posts/1/',
        ]
        for address in url_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    @override_settings(DEBUG=False)
    def test_unexisting_page(self):
        """Проверяем, что вернется custom 404."""
        weird_url = '/weird_page'
        response = self.guest_client.get(weird_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        template = 'core/404.html'
        self.assertTemplateUsed(response, template)

    def test_edit_page_redirect_non_author(self):
        """
        Проверяем, что НЕ автора поста редиректит со страницы редактирования.
        """
        get_url = reverse(
            'posts:post_edit', kwargs={'post_id': PostsURLTests.post.pk}
        )
        redirect_url = reverse(
            'posts:post_detail', kwargs={'post_id': PostsURLTests.post.pk}
        )
        response = self.authorized_client.get(get_url, follow=True)
        self.assertRedirects(response, redirect_url)

    def test_edit_page(self):
        """Проверяем, что автору поста доступна страница редактирования."""
        get_url = reverse(
            'posts:post_edit', kwargs={'post_id': PostsURLTests.post.pk}
        )
        response = self.author_client.get(get_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_redirect_non_authorized(self):
        """
        Проверяем, что неавторизованного юзера редиректит.
        """
        response = self.guest_client.get(
            reverse('posts:post_create'), follow=True
        )
        redirect_url = reverse('users:login') + '?next=' + reverse(
            'posts:post_create'
        )
        self.assertRedirects(response, redirect_url)

    def test_authorized_pages(self):
        """
        Проверяем, что авторизованному юзеру доступны страницы.
        """
        urls = [reverse('posts:post_create'),
                reverse(
                    'posts:add_comment',
                    kwargs={'post_id': PostsURLTests.post.pk}
                ),
                reverse('posts:follow_index'),
                reverse(
                    'posts:profile_follow',
                    kwargs={'username': PostsURLTests.user_author}
                ),
                reverse(
                    'posts:profile_unfollow',
                    kwargs={'username': PostsURLTests.user_author}
                )
                ]
        for url in urls:
            response = self.authorized_client.get(url, follow=True)
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test/': 'posts/group_list.html',
            '/profile/auth/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.author_client.get(address)
                self.assertTemplateUsed(response, template)
