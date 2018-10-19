from django.contrib import admin
from django.shortcuts import render
from django.urls import path

from . import models


class SubmissionAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Submission, SubmissionAdmin)


class SubmissionRevisionAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.SubmissionRevision, SubmissionRevisionAdmin)


class AuthorAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Author, AuthorAdmin)


class ReviewerAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Reviewer, ReviewerAdmin)


class JournalAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        extra_urls = [
            path(
                'register_journal/',
                self.admin_site.admin_view(self.register_journal_view)
            )
        ]
        urls = extra_urls + urls
        return urls

    def register_journal_view(self, request):
        response = {}
        return render(request, 'ojs/register_journals.html', response)

admin.site.register(models.Journal, JournalAdmin)
