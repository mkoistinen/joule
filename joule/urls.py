# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

from django.conf.urls import *  # NOQA
from django.conf.urls.i18n import i18n_patterns
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.conf import settings

from .views import BillEstimateView

admin.autodiscover()

urlpatterns = i18n_patterns('',
    url(r'^admin/', include(admin.site.urls)),  # NOQA
    url(r'^select2/', include('django_select2.urls')),

    url(r'^bill/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        BillEstimateView.as_view(), name='bill_view'),
    url(r'^bill/(?P<year>\d{4})/$',
        BillEstimateView.as_view(), name='bill_view'),
    url(r'^bill/$',
        BillEstimateView.as_view(), name='bill_view'),
    url(r'^/?$',
        BillEstimateView.as_view(), name='bill_view'),
)

# This is only needed when using runserver.
if settings.DEBUG:
    urlpatterns = patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',  # NOQA
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
        ) + staticfiles_urlpatterns() + urlpatterns  # NOQA
