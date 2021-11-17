import shutil
import tempfile


from django.core.cache import cache
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostTemplatesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='author')
        cls.user_author2 = User.objects.create_user(username='author2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test2',
            description='Тестовое описание 2',
        )
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
        small_gif2 = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded2 = SimpleUploadedFile(
            name='small.gif',
            content=small_gif2,
            content_type='image/gif'
        )
        Follow.objects.create(
            user=cls.user_author,
            author=cls.user_author2
        )
        Post.objects.bulk_create([
            Post(author=cls.user_author,
                 group=cls.group,
                 text=f'Тестовый пост {i}',
                 image=cls.uploaded,
                 ) for i in range(12)
        ]
        )
        Post.objects.bulk_create([
            Post(author=cls.user_author2,
                 group=cls.group2,
                 text=f'Тестовый пост {i}',
                 image=cls.uploaded2,
                 ) for i in range(12, 15)
        ]
        )
        Comment.objects.create(
            post=Post.objects.last(),
            author=cls.user_author,
            text='Тестовый коммент',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = PostTemplatesTests.user_author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_follow_page(self):
        """Проверяем правильную выдачу на странице подписок."""
        response = self.authorized_client.get(reverse('posts:follow_index'))
        follow_objects = response.context['page_obj']
        for post in follow_objects:
            self.assertEqual(post.author, PostTemplatesTests.user_author2)

    def test_pages_uses_correct_template(self):
        """
        Проверяем, что во view-функциях используются правильные html-шаблоны.
        """
        test_object = Post.objects.all().last()
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_posts',
                kwargs={
                    'slug': PostTemplatesTests.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={
                        'username': PostTemplatesTests.user_author.username}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': test_object.pk}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': test_object.pk}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Проверяем контекст и паджинатор главной страницы."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)
        test_object = response.context['page_obj'][0]
        first_object = Post.objects.all().first()
        self.assertEqual(test_object.text, first_object.text)
        self.assertEqual(test_object.group, first_object.group)
        self.assertEqual(test_object.image, first_object.image)

    def test_group_page_show_correct_context(self):
        """Проверяем контекст и паджинатор страницы группы."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostTemplatesTests.group.slug}
            )
        )
        self.assertEqual(len(response.context['page_obj']), 10)
        group_objects = response.context['page_obj']
        for post in group_objects:
            self.assertEqual(post.group, PostTemplatesTests.group)
        response = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostTemplatesTests.group2.slug}
            )
        )
        group_objects = response.context['page_obj']
        first_object = Post.objects.filter(
            group=PostTemplatesTests.group2).first()
        self.assertEqual(group_objects[0].text, first_object.text)
        self.assertEqual(group_objects[0].group, first_object.group)
        self.assertEqual(group_objects[0].image, first_object.image)

    def test_group_profile_show_correct_context(self):
        """Проверяем контекст и паджинатор страницы профиля."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': PostTemplatesTests.user_author.username}
            )
        )
        self.assertEqual(len(response.context['page_obj']), 10)
        profile_objects = response.context['page_obj']
        test_object = Post.objects.filter(author=self.user).first()
        self.assertEqual(profile_objects[0].image, test_object.image)
        for post in profile_objects:
            self.assertEqual(post.author, test_object.author)

    def test_group_post_detail_show_correct_context(self):
        """Проверяем контекст страницы поста."""
        first_object = Post.objects.all().last()
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': first_object.pk}
            )
        )
        post = response.context['post']
        self.assertEqual(post.id, first_object.pk)
        self.assertEqual(post.image, first_object.image)
        self.assertEqual(
            post.comments.first().text,
            first_object.comments.first().text
        )
        self.assertEqual(
            post.comments.first().author,
            first_object.comments.first().author
        )

    def test_group_post_edit_show_correct_context(self):
        """Проверяем контекст страницы редактирования поста."""
        first_object = Post.objects.all().last()
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': first_object.pk}
            )
        )
        form = response.context['form']
        post = response.context['post']
        self.assertEqual(post.id, first_object.pk)
        self.assertIsInstance(form.fields.get('text'), forms.fields.CharField)
        self.assertIsInstance(form.fields['group'], forms.fields.ChoiceField)

    def test_group_post_create_show_correct_context(self):
        """Проверяем контекст страницы создания поста."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form = response.context['form']
        self.assertIsInstance(form.fields.get('text'), forms.fields.CharField)
        self.assertIsInstance(form.fields['group'], forms.fields.ChoiceField)

    def test_cache_index_page(self):
        """Проверяем кеширование главной страницы."""
        response1 = self.authorized_client.get(reverse('posts:index'))
        test_object1 = response1.content
        Post.objects.filter(group=PostTemplatesTests.group2).delete()
        response2 = self.authorized_client.get(reverse('posts:index'))
        test_object2 = response2.content
        self.assertEqual(test_object1, test_object2)
        cache.clear()
        response3 = self.authorized_client.get(reverse('posts:index'))
        test_object3 = response3.content
        self.assertNotEqual(test_object1, test_object3)
