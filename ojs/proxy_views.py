from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from base.django_handler_mixin import DjangoHandlerMixin
from urllib.parse import urlencode
from .models import Journal, Submission, SubmissionRevision, Author, Reviewer
from django.core.files.base import ContentFile
from django.conf import settings

from document.models import Document, AccessRight
from usermedia.models import Image, DocumentImage
from os import path

class Proxy(DjangoHandlerMixin, RequestHandler):
    def write_error(self, status_code, **kwargs):
         self.write(str(kwargs["exc_info"][1]))

    @asynchronous
    def get(self, relative_url):
        user = self.get_current_user()
        if not user.is_authenticated:
            self.set_status(401)
            return
        if relative_url == 'journals':
            base_url = self.get_argument('url')
            key = self.get_argument('key')
        else:
            return
        plugin_path = \
            '/index.php/index/gateway/plugin/FidusWriterGatewayPlugin/'
        url = base_url + plugin_path + relative_url
        http = AsyncHTTPClient()
        http.fetch(
            HTTPRequest(
                url_concat(url, {'key': key}),
                'GET'
            ),
            callback=self.on_get_response
        )

    # The response is asynchronous so that the getting of the data from the OJS
    # server doesn't block the FW server connection.
    def on_get_response(self, response):
        if response.error:
            response.rethrow()
        self.write(response.body)
        self.finish()

    @asynchronous
    def post(self, relative_url):
        self.user = self.get_current_user()
        if not self.user.is_authenticated:
            self.set_status(401)
            self.finish()
            return
        self.plugin_path = \
            '/index.php/index/gateway/plugin/FidusWriterGatewayPlugin/'
        self.submission_attempts = 0
        if relative_url == 'author_submit':
            self.author_submit()
        elif relative_url == 'reviewer_submit':
            self.reviewer_submit()
        else:
            self.set_status(401)
            self.finish()
            return

    def author_submit(self):
        # Submitting a new submission revision.
        document_id = self.get_argument('doc_id')
        revision = SubmissionRevision.objects.filter(
            document_id=document_id
        ).first()
        if revision:
            self.revision = revision
            self.author_resubmit()
        else:
            self.author_first_submit()

    def author_first_submit(self):
        # The document is not part of an existing submission.
        journal_id = self.get_argument('journal_id')
        self.submission = Submission()
        self.submission.submitter = self.user
        self.submission.journal_id = journal_id
        self.submission.save()
        self.revision = SubmissionRevision()
        self.revision.submission = self.submission
        self.revision.version = "1.0.0"
        version = "1.0.0"
        # Connect a new document to the submission.
        title = self.get_argument('title')
        abstract = self.get_argument('abstract')
        contents = self.get_argument('contents')
        bibliography = self.get_argument('bibliography')
        image_ids = self.get_arguments('image_ids[]')
        document = Document()
        journal = Journal.objects.get(id=journal_id)
        document.owner = journal.editor
        document.title = title
        document.contents = contents
        document.bibliography = bibliography
        document.save()
        for id in image_ids:
            image = Image.objects.filter(id=id).first()
            if image is None:
                image = Image()
                image.pk = id
                image.uploader = journal.editor
                f = open(path.join(
                    settings.PROJECT_PATH, "base/static/img/error.png"
                ))
                image.image.save('error.png', File(f))
                image.save()
            DocumentImage.objects.create(
                document=document,
                image=image,
                title=''
            )
        self.revision.document = document
        self.revision.save()

        fidus_url = '{protocol}://{host}'.format(
            protocol=self.request.protocol,
            host=self.request.host
        )

        post_data = {
            'username': self.user.username.encode('utf8'),
            'title': title.encode('utf8'),
            'abstract': abstract.encode('utf8'),
            'first_name': self.get_argument('firstname').encode('utf8'),
            'last_name': self.get_argument('lastname').encode('utf8'),
            'email': self.user.email.encode('utf8'),
            'affiliation': self.get_argument('affiliation').encode('utf8'),
            'author_url': self.get_argument('author_url').encode('utf8'),
            'journal_id': journal.ojs_jid,
            'fidus_url': fidus_url,
            'fidus_id': self.submission.id,
            'version': version
        }

        body = urlencode(post_data)
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = base_url + self.plugin_path + 'authorSubmit'
        http = AsyncHTTPClient()
        http.fetch(
            HTTPRequest(
                url_concat(url, {'key': key}),
                'POST',
                None,
                body,
                request_timeout=40.0
            ),
            callback=self.on_author_first_submit_response
        )

    # The response is asynchronous so that the getting of the data from the OJS
    # server doesn't block the FW server connection.
    def on_author_first_submit_response(self, response):
        if response.error:
            self.revision.document.delete()
            self.revision.delete()
            code = response.code
            if code >= 500 and code < 600 and self.submission_attempts < 10:
                self.submission_attempts += 1
                # We wait 3 seconds and try again. Maybe the OJS server has
                # issues.
                ioloop = IOLoop.current()
                ioloop.call_later(delay=3, callback=self.author_first_submit)
                return
            response.rethrow()
        # Set the submission ID from the response from the OJS server.
        json = json_decode(response.body)
        self.submission.ojs_jid = json['submission_id']
        self.submission.save()
        # We save the author ID on the OJS site. Currently we are NOT using
        # this information for login purposes.
        Author.objects.create(
            user=self.user,
            submission=self.submission,
            ojs_jid=json['user_id']
        )
        AccessRight.objects.create(
            document=self.revision.document,
            user=self.user,
            rights='read-without-comments'
        )
        self.write(response.body)
        self.finish()

    def author_resubmit(self):
        submission = self.revision.submission
        if submission.submitter != self.user:
            # Trying to submit revision for submission of other user
            self.set_status(401)
            self.finish()
            return
        journal = submission.journal
        post_data = {
            'submission_id': submission.ojs_jid,
            'version': self.revision.version
        }
        body = urlencode(post_data)
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = base_url + self.plugin_path + 'authorSubmit'
        http = AsyncHTTPClient()
        http.fetch(
            HTTPRequest(
                url_concat(url, {'key': key}),
                'POST',
                None,
                body,
                request_timeout=40.0
            ),
            callback=self.on_author_resubmit_response
        )

    # The response is asynchronous so that the getting of the data from the OJS
    # server doesn't block the FW server connection.
    def on_author_resubmit_response(self, response):
        if response.error:
            code = response.code
            if code >= 500 and code < 600 and self.submission_attempts < 10:
                self.submission_attempts += 1
                # We wait 3 seconds and try again. Maybe the OJS server has
                # issues.
                ioloop = IOLoop.current()
                ioloop.call_later(delay=3, callback=self.author_resubmit)
                return
            response.rethrow()
        # submission was successful, so we replace the user's write access
        # rights with read rights.
        right = AccessRight.objects.get(
            user=self.user,
            document=self.revision.document
        )
        right.rights = 'read'
        right.save()
        self.write(response.body)
        self.finish()

    def reviewer_submit(self):
        # Submitting a new submission revision.
        document_id = self.get_argument('doc_id')
        reviewer = Reviewer.objects.filter(
            revision__document_id=document_id,
            user=self.user
        ).first()
        if reviewer is None:
            # Trying to submit review without access rights.
            self.set_status(401)
            self.finish()
        self.reviewer = reviewer
        post_data = {
            'submission_id': self.reviewer.revision.submission.ojs_jid,
            'version': self.reviewer.revision.version,
            'user_id': self.reviewer.ojs_jid,
            'editor_message': self.get_argument('editor_message'),
            'editor_author_message':
                self.get_argument('editor_author_message'),
            'recommendation': self.get_argument('recommendation')
        }

        body = urlencode(post_data)
        key = self.reviewer.revision.submission.journal.ojs_key
        base_url = self.reviewer.revision.submission.journal.ojs_url
        url = base_url + self.plugin_path + 'reviewerSubmit'
        http = AsyncHTTPClient()
        http.fetch(
            HTTPRequest(
                url_concat(url, {'key': key}),
                'POST',
                None,
                body,
                request_timeout=40.0
            ),
            callback=self.on_reviewer_submit_response
        )

    # The response is asynchronous so that the getting of the data from the OJS
    # server doesn't block the FW server connection.
    def on_reviewer_submit_response(self, response):
        if response.error:
            code = response.code
            if code >= 500 and code < 600 and self.submission_attempts < 10:
                self.submission_attempts += 1
                # We wait 3 seconds and try again. Maybe the OJS server has
                # issues.
                ioloop = IOLoop.current()
                ioloop.call_later(delay=3, callback=self.reviewer_submit)
                return
            response.rethrow()
        # submission was successful, so we replace the user's write access
        # rights with read rights.
        right = AccessRight.objects.get(
            user=self.user,
            document=self.reviewer.revision.document
        )
        right.rights = 'read'
        right.save()
        self.write(response.body)
        self.finish()
