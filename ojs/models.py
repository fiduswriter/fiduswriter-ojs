from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible

from django.db import models
from django.contrib.auth.models import User

from document.models import Document


# A Journal registered with a particular OJS installation
@python_2_unicode_compatible
class Journal(models.Model):
    ojs_url = models.CharField(max_length=512)
    ojs_key = models.CharField(max_length=512)
    ojs_jid = models.PositiveIntegerField()  # _jid as _id is foreign key
    name = models.CharField(max_length=512)
    editor = models.ForeignKey(User)

    class Meta:
        unique_together = (("ojs_url", "ojs_jid"),)

    def __str__(self):
        return self.name


# A submission registered with OJS
@python_2_unicode_compatible
class Submission(models.Model):
    submitter = models.ForeignKey(User)
    journal = models.ForeignKey(Journal)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS

    def __str__(self):
        return u'{ojs_jid} in {journal} by {submitter}'.format(
            ojs_jid=self.ojs_jid,
            journal=self.journal.name,
            submitter=self.submitter.username
        )


# An author registered with OJS and also registered here
# Authors are the same for an entire submission.
@python_2_unicode_compatible
class Author(models.Model):
    user = models.ForeignKey(User)
    submission = models.ForeignKey(Submission)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS

    class Meta:
        unique_together = (("submission", "ojs_jid"))

    def __str__(self):
        return u'{username} ({ojs_jid})'.format(
            username=self.user.username,
            ojs_jid=self.ojs_jid
        )


# Within each submission, there is a new revision for each revision
@python_2_unicode_compatible
class SubmissionRevision(models.Model):
    submission = models.ForeignKey(Submission)
    # version = stage ID + "." + round + "." + (0 for reviewer or 5 for author)
    # version)
    # For example:
    # submission version: "1.0.0"
    # Author version of 5th external review (stage ID=3): "3.5.5"
    # The version should increase like a computer version number. Not all
    # numbers are included.
    version = models.CharField(max_length=8, default='1.0.0')
    document = models.ForeignKey(Document)

    def __str__(self):
        return u'{ojs_jid} (v{version}) in {journal} by {submitter}'.format(
            ojs_jid=self.submission.ojs_jid,
            version=self.version,
            journal=self.submission.journal.name,
            submitter=self.submission.submitter.username
        )


# A reviewer registered with OJS and also registered here
# Reviewers can differ from revision to revision.
@python_2_unicode_compatible
class Reviewer(models.Model):
    user = models.ForeignKey(User)
    revision = models.ForeignKey(SubmissionRevision)
    ojs_jid = models.PositiveIntegerField(default=0)  # ID in OJS

    class Meta:
        unique_together = (("revision", "ojs_jid"))

    def __str__(self):
        return u'{username} ({ojs_jid})'.format(
            username=self.user.username,
            ojs_jid=self.ojs_jid
        )
