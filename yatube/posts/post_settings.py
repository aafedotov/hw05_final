from django.conf import settings

PAGINATOR_SET = getattr(settings, 'POSTS_PAGINATOR_SET', 10)
