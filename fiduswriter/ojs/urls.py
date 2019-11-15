from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        '^add_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9\.]+)/$',
        views.add_reviewer,
        name='add_reviewer'
    ),
    url(
        '^accept_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9\.]+)/$',
        views.accept_reviewer,
        name='accept_reviewer'
    ),
    url(
        '^remove_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9\.]+)/$',
        views.remove_reviewer,
        name='remove_reviewer'
    ),
    url(
        '^revision/(?P<submission_id>[0-9]+)/(?P<version>[0-9\.]+)/$',
        views.open_revision_doc,
        name='open_revision_doc'
    ),
    url(
        '^get_login_token/$',
        views.get_login_token,
        name='get_login_token'
    ),
    url(
        '^create_copy/(?P<submission_id>[0-9]+)/$',
        views.create_copy,
        name='create_copy'
    ),
    url(
        '^get_user/$',
        views.get_user,
        name='get_user'
    ),
    url(
        '^save_journal/$',
        views.save_journal,
        name='save_journal'
    ),
    url(
        '^get_doc_info/$',
        views.get_doc_info,
        name='get_doc_info'
    )
]
