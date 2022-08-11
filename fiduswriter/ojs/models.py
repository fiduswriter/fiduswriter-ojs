from django.db import models
from django.db.models.deletion import CASCADE
from django.conf import settings

from document.models import Document, DocumentTemplate


# A Journal registered with a particular OJS installation
class Journal(models.Model):
    ojs_url = models.CharField(max_length=512)
    ojs_key = models.CharField(max_length=512)
    ojs_jid = models.PositiveIntegerField()  # _jid as _id is foreign key
    templates = models.ManyToManyField(DocumentTemplate)
    name = models.CharField(max_length=512)
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)

    class Meta(object):
        unique_together = (("ojs_url", "ojs_jid"),)

    def __str__(self):
        return self.name


# A submission registered with OJS
class Submission(models.Model):
    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    journal = models.ForeignKey(Journal, on_delete=CASCADE)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS

    def __str__(self):
        return "{ojs_jid} in {journal} by {submitter}".format(
            ojs_jid=self.ojs_jid,
            journal=self.journal.name,
            submitter=self.submitter.username,
        )


# An author registered with OJS and also registered here
# Authors are the same for an entire submission.
class Author(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    submission = models.ForeignKey(Submission, on_delete=CASCADE)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS

    class Meta(object):
        unique_together = ("submission", "ojs_jid")

    def __str__(self):
        return "{username} ({ojs_jid})".format(
            username=self.user.username, ojs_jid=self.ojs_jid
        )


# Within each submission, there is a new revision for each revision
class SubmissionRevision(models.Model):
    submission = models.ForeignKey(Submission, on_delete=CASCADE)
    # version = stage ID + "." + round + "." + (0 for reviewer or 5 for author)
    # version)
    # For example:
    # submission version: "1.0.0"
    # Author version of 5th external review (stage ID=3): "3.5.5"
    # The version should increase like a computer version number. Not all
    # numbers are included.
    version = models.CharField(max_length=8, default="1.0.0")
    document = models.ForeignKey(Document, on_delete=CASCADE)
    # Contributor information if it has been removed from the document
    contributors = models.JSONField(default=dict)

    def __str__(self):
        return "{ojs_jid} (v{version}) in {journal} by {submitter}".format(
            ojs_jid=self.submission.ojs_jid,
            version=self.version,
            journal=self.submission.journal.name,
            submitter=self.submission.submitter.username,
        )


REVIEW_METHODS = [
    ("open", "Open"),  # Author and reviewer can see one-another's names.
    (
        "anonymous",
        "Anonymous",
    ),  # Reviewer can see name of author, but author cannot see name of reviewer.
    (
        "doubleanonymous",
        "Double anonymous",
    ),  # Author and reviewer cannot see one-another's names.
]


# A reviewer registered with OJS and also registered here
# Reviewers can differ from revision to revision.
class Reviewer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    revision = models.ForeignKey(SubmissionRevision, on_delete=CASCADE)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS
    method = models.CharField(
        max_length=15, default="doubleanonymous", choices=REVIEW_METHODS
    )

    class Meta(object):
        unique_together = ("revision", "ojs_jid")

    def __str__(self):
        return "{username} ({ojs_jid})".format(
            username=self.user.username, ojs_jid=self.ojs_jid
        )


# An editor/partial editor registered with OJS and also registered here
# Editors are the same for an entire submission.
class Editor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    submission = models.ForeignKey(Submission, on_delete=CASCADE)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS
    role = models.PositiveIntegerField(
        default=0
    )  # role (SITE_ADMIN/MANAGER/SUB_EDITOR/ASSISTANT) in OJS

    class Meta(object):
        unique_together = ("submission", "ojs_jid")

    def __str__(self):
        return "User: {username} (OJS User-ID: {user_id}), Submission: {ojs_jid} in {journal} by {submitter}".format(
            username=self.user.username,
            user_id=self.ojs_jid,
            ojs_jid=self.submission.ojs_jid,
            journal=self.submission.journal.name,
            submitter=self.submission.submitter.username,
        )
