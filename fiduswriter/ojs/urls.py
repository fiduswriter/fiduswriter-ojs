from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        "^add_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9.]+)/$",
        views.add_reviewer,
        name="add_reviewer",
    ),
    re_path(
        "^accept_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9.]+)/$",
        views.accept_reviewer,
        name="accept_reviewer",
    ),
    re_path(
        "^remove_reviewer/(?P<submission_id>[0-9]+)/(?P<version>[0-9.]+)/$",
        views.remove_reviewer,
        name="remove_reviewer",
    ),
    re_path(
        "^check_revision/(?P<submission_id>[0-9]+)/(?P<version>[0-9.]+)/$",
        views.check_revision_doc,
        name="check_revision_doc",
    ),
    re_path(
        "^revision/(?P<submission_id>[0-9]+)/(?P<version>[0-9.]+)/$",
        views.open_revision_doc,
        name="open_revision_doc",
    ),
    re_path(
        "^get_login_token/$", views.get_login_token, name="get_login_token"
    ),
    re_path(
        "^create_copy/(?P<submission_id>[0-9]+)/$",
        views.create_copy,
        name="create_copy",
    ),
    re_path("^get_user/$", views.get_user, name="get_user"),
    re_path("^save_journal/$", views.save_journal, name="save_journal"),
    re_path("^get_doc_info/$", views.get_doc_info, name="get_doc_info"),
    re_path(
        "^add_editor/(?P<submission_id>[0-9]+)/$",
        views.add_editor,
        name="add_editor",
    ),
    re_path(
        "^remove_editor/(?P<submission_id>[0-9]+)/$",
        views.remove_editor,
        name="remove_editor",
    ),
    re_path(
        "^add_author/(?P<submission_id>[0-9]+)/$",
        views.add_author,
        name="add_author",
    ),
    re_path(
        "^remove_author/(?P<submission_id>[0-9]+)/$",
        views.remove_author,
        name="remove_author",
    ),
]
