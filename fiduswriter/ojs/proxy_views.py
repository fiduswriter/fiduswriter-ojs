import json
from tornado.web import RequestHandler
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httputil import url_concat
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from base.django_handler_mixin import DjangoHandlerMixin
from urllib.parse import urlencode

from document.models import AccessRight
from usermedia.models import Image

from .models import Journal, Submission, SubmissionRevision, Author, Reviewer
from . import helpers


class Proxy(DjangoHandlerMixin, RequestHandler):
    def write_error(self, status_code, **kwargs):
        self.write(str(kwargs["exc_info"][1]))

    async def get(self, relative_url):
        user = self.get_current_user()
        if not user.is_authenticated:
            self.set_status(401)
            return
        if relative_url == "journals":
            base_url = self.get_argument("url")
            key = self.get_argument("key")
        else:
            return
        plugin_path = (
            "/index.php/index/gateway/plugin/FidusWriterGatewayPlugin/"
        )
        url = f"{base_url}{plugin_path}{relative_url}"
        http = AsyncHTTPClient()
        response = await http.fetch(
            HTTPRequest(url_concat(url, {"key": key}), "GET")
        )
        # The response is asynchronous so that the getting of the data from the
        # OJS server doesn't block the FW server connection.
        if response.error:
            response.rethrow()
        self.write(response.body)
        self.finish()

    async def post(self, relative_url):
        self.user = self.get_current_user()
        if not self.user.is_authenticated:
            self.set_status(401)
            self.finish()
            return
        self.plugin_path = (
            "/index.php/index/gateway/plugin/FidusWriterGatewayPlugin/"
        )
        self.submission_attempts = 0
        if relative_url == "author_submit":
            # Submitting a new submission revision.
            document_id = self.get_argument("doc_id")
            revision = SubmissionRevision.objects.filter(
                document_id=document_id
            ).first()
            if revision:
                self.revision = revision
                await self.author_resubmit()
            else:
                await self.author_first_submit(document_id)
        elif relative_url == "copyedit_draft_submit":
            document_id = self.get_argument("doc_id")
            revision = SubmissionRevision.objects.filter(
                document_id=document_id
            ).first()
            if revision:
                self.revision = revision
                await self.copyedit_draft_submit()
        elif relative_url == "reviewer_submit":
            await self.reviewer_submit()
        else:
            self.set_status(401)
        self.finish()
        return

    async def author_first_submit(self, document_id):
        # The document is not part of an existing submission.
        journal_id = self.get_argument("journal_id")
        journal = Journal.objects.get(id=journal_id)
        template = journal.templates.filter(
            document__id__exact=document_id
        ).first()
        if not template:
            # Template is not available for Journal.
            self.set_status(401)
            self.finish()
            return
        self.submission = Submission()
        self.submission.submitter = self.user
        self.submission.journal_id = journal_id
        self.submission.save()
        self.revision = SubmissionRevision()
        self.revision.submission = self.submission
        self.revision.version = "1.0.0"
        version = "1.0.0"
        # Connect a new document to the submission.
        title = self.get_argument("title")
        abstract = self.get_argument("abstract")
        content = self.get_argument("content")
        bibliography = self.get_argument("bibliography")
        image_ids = self.get_arguments("image_ids[]")

        images = []
        for id in image_ids:
            image = Image.objects.filter(id=id).first()
            images.append(image)

        document = helpers.create_doc(
            journal.editor,
            template,
            title,
            json.loads(content),
            json.loads(bibliography),
            images,
            {},
            self.submission.id,
            version,
        )

        self.revision.document = document
        self.revision.save()

        fidus_url = "{protocol}://{host}".format(
            protocol=self.request.protocol, host=self.request.host
        )

        post_data = {
            "username": self.user.username.encode("utf8"),
            "title": title.encode("utf8"),
            "abstract": abstract.encode("utf8"),
            "first_name": self.get_argument("firstname").encode("utf8"),
            "last_name": self.get_argument("lastname").encode("utf8"),
            "email": self.user.email.encode("utf8"),
            "affiliation": self.get_argument("affiliation").encode("utf8"),
            "author_url": self.get_argument("author_url").encode("utf8"),
            "journal_id": journal.ojs_jid,
            "fidus_url": fidus_url,
            "fidus_id": self.submission.id,
            "version": version,
        }

        body = urlencode(post_data)
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = f"{base_url}{self.plugin_path}authorSubmit"
        http = AsyncHTTPClient()
        response = await http.fetch(
            HTTPRequest(
                url_concat(url, {"key": key}),
                "POST",
                None,
                body,
                request_timeout=40.0,
            )
        )
        # The response is asynchronous so that the getting of the data from the
        # OJS server doesn't block the FW server connection.
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
        body_json = json_decode(response.body)
        self.submission.ojs_jid = body_json["submission_id"]
        self.submission.save()

        # We save the author ID on the OJS site. Currently we are NOT using
        # this information for login purposes.
        author = Author.objects.filter(
            submission=self.submission.id, ojs_jid=body_json["user_id"]
        ).first()
        if author is None:
            Author.objects.create(
                user=self.user,
                submission=self.submission,
                ojs_jid=body_json["user_id"],
            )
            AccessRight.objects.create(
                document=self.revision.document,
                holder_obj=self.user,
                path=self.revision.document.path,
                rights="read-without-comments",
            )

        self.write(response.body)

    async def copyedit_draft_submit(self):
        if self.revision.version != "4.0.0":
            # version is not 4.0.0 (not copyedit draft)
            self.set_status(403)
            self.finish()
            return

        submission = self.revision.submission
        journal = submission.journal
        ojs_uid = False
        author = submission.author_set.filter(user=self.user).first()
        if author:
            # User is the author
            ojs_uid = author.ojs_jid
        else:
            editor = submission.editor_set.filter(user=self.user).first()
            if editor:
                # User is the one of the editors
                ojs_uid = editor.ojs_jid

        if not ojs_uid:
            # User is neither author nor editor
            self.set_status(401)
            self.finish()
            return

        post_data = {"submission_id": submission.ojs_jid, "ojs_uid": ojs_uid}
        body = urlencode(post_data)
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = f"{base_url}{self.plugin_path}copyeditDraftSubmit"
        http = AsyncHTTPClient()
        response = await http.fetch(
            HTTPRequest(
                url_concat(url, {"key": key}),
                "POST",
                None,
                body,
                request_timeout=40.0,
            )
        )
        # The response is asynchronous so that the getting of the data from the
        # OJS server doesn't block the FW server connection.
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
            user=self.user, document=self.revision.document
        )
        right.rights = "read"
        right.save()

        self.write(response.body)

    async def author_resubmit(self):
        submission = self.revision.submission
        if submission.submitter != self.user:
            # Trying to submit revision for submission of other user
            self.set_status(401)
            self.finish()
            return
        journal = submission.journal
        post_data = {
            "submission_id": submission.ojs_jid,
            "version": self.revision.version,
        }
        body = urlencode(post_data)
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = f"{base_url}{self.plugin_path}authorSubmit"
        http = AsyncHTTPClient()
        response = await http.fetch(
            HTTPRequest(
                url_concat(url, {"key": key}),
                "POST",
                None,
                body,
                request_timeout=40.0,
            )
        )
        # The response is asynchronous so that the getting of the data from the
        # OJS server doesn't block the FW server connection.
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
            user=self.user, document=self.revision.document
        )
        right.rights = "read"
        right.save()

        self.write(response.body)

    async def reviewer_submit(self):
        # Submitting a new submission revision.
        document_id = self.get_argument("doc_id")
        reviewer = Reviewer.objects.filter(
            revision__document_id=document_id, user=self.user
        ).first()
        if reviewer is None:
            # Trying to submit review without access rights.
            self.set_status(401)
            self.finish()
        self.reviewer = reviewer
        post_data = {
            "submission_id": self.reviewer.revision.submission.ojs_jid,
            "version": self.reviewer.revision.version,
            "user_id": self.reviewer.ojs_jid,
            "editor_message": self.get_argument("editor_message"),
            "editor_author_message": self.get_argument(
                "editor_author_message"
            ),
            "recommendation": self.get_argument("recommendation"),
        }

        body = urlencode(post_data)
        key = self.reviewer.revision.submission.journal.ojs_key
        base_url = self.reviewer.revision.submission.journal.ojs_url
        url = f"{base_url}{self.plugin_path}reviewerSubmit"
        http = AsyncHTTPClient()
        response = await http.fetch(
            HTTPRequest(
                url_concat(url, {"key": key}),
                "POST",
                None,
                body,
                request_timeout=40.0,
            )
        )
        # The response is asynchronous so that the getting of the data from the
        # OJS server doesn't block the FW server connection.
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
            user=self.user, document=self.reviewer.revision.document
        )
        right.rights = "read"
        right.save()
        self.write(response.body)
