import json
from httpx import HTTPError, Request
from urllib.parse import urlencode

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.db import IntegrityError
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.http import require_http_methods

from allauth.account.models import EmailAddress

from document.models import Document, AccessRight, DocumentTemplate
from usermedia.models import Image

from . import models
from . import token
from . import constants
from . import helpers


OJS_PLUGIN_PATH = "/index.php/index/gateway/plugin/FidusWriterGatewayPlugin/"


# logs a user in
def login_user(request, user):
    # TODO: Is next line really needed?
    user.backend = settings.AUTHENTICATION_BACKENDS[0]
    login(request, user)


# Find a user -- First check if it is an author, then a reviewer.
# If it's none of the two, check if there is authorization to login as an
# editor and if this is the case, log the user in as the journal's owner.
# Under all other circumstances, return False.
def find_user(journal_id, submission_id, version, user_id, is_editor):
    author = models.Author.objects.filter(
        submission_id=submission_id, ojs_jid=user_id
    ).first()
    if author:
        # It's an author
        return author.user

    revision = models.SubmissionRevision.objects.filter(
        submission_id=submission_id, version=version
    ).first()
    if revision:
        revision_id = revision.id
        reviewer = models.Reviewer.objects.filter(
            revision_id=revision_id, ojs_jid=user_id
        ).first()
        if reviewer:
            return reviewer.user

    if is_editor:
        editor = models.Editor.objects.filter(
            submission_id=submission_id, ojs_jid=user_id
        ).first()
        if editor:
            return editor.user

    return False


# To login from OJS, the OJS server first gets a temporary login token from the
# Django server for a specific user and journal using the api key on the server
# side. It then logs the user in using the login token on the client side. This
# way, the api key is not exposed to the client.
@csrf_exempt
@require_GET
def get_login_token(request):
    response = {}
    api_key = request.GET.get("key")
    submission_id = request.GET.get("fidus_id")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    journal_id = submission.journal_id
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        return JsonResponse(response, status=403)

    user_id = request.GET.get("user_id")
    is_editor = request.GET.get("is_editor")
    version = request.GET.get("version")

    # Validate is_editor
    try:
        is_editor = int(is_editor)
    except ValueError:
        is_editor = 0

    user = find_user(journal_id, submission_id, version, user_id, is_editor)
    if not user:
        response["error"] = "User not accessible"
        return JsonResponse(response, status=403)
    response["token"] = token.create_token(user, journal_key)
    return JsonResponse(response, status=200)


# Open a revision doc. This is where the reviewers/editor arrive when trying to
# enter the submission doc on OJS.
@csrf_exempt
@require_http_methods(["GET", "POST"])
def open_revision_doc(request, submission_id, version):
    params = request.POST.copy()
    params.update(request.GET)
    login_token = params["token"]
    user_id = int(login_token.split("-")[0])
    User = get_user_model()
    user = User.objects.get(id=user_id)
    if user is None:
        return HttpResponse("Invalid user", status=404)
    rev = models.SubmissionRevision.objects.get(
        submission_id=submission_id, version=version
    )
    key = rev.submission.journal.ojs_key

    if not token.check_token(user, key, login_token):
        return HttpResponse("No access", status=403)
    if (
        rev.document.owner != user
        and AccessRight.objects.filter(
            document=rev.document, user=user
        ).count()
        == 0
    ):
        # The user to be logged in is neither the editor (owner of doc), nor
        # has he access rights to the doc. We prohibit access.

        # Access forbidden
        return HttpResponse("Missing access rights", status=403)
    login_user(request, user)

    return redirect(f"/document/{rev.document.id}/", permanent=True)


# Check if the revision doc exists.
@csrf_exempt
@require_GET
def check_revision_doc(request, submission_id, version):
    api_key = request.GET.get("key")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    journal_id = submission.journal_id
    res = 0

    # Validate api key
    if journal_key == api_key:
        user_id = request.GET.get("user_id")
        is_editor = request.GET.get("is_editor")

        # Validate is_editor
        try:
            is_editor = int(is_editor)
        except ValueError:
            is_editor = 0

        user = find_user(
            journal_id, submission_id, version, user_id, is_editor
        )

        # Validate if user exists
        if not user:
            return HttpResponse("User not accessible", status=403)

        # Validate if doc exists
        try:
            models.SubmissionRevision.objects.get(
                submission_id=submission_id, version=version
            )
            res = 1
        except Exception:
            res = 0

    return HttpResponse(res, status=200)


# Send basic information about the current document and the journals that can
# be submitted to. This information is used as a starting point to decide what
# OJS-related UI elements to add on the editor page.
@login_required
@require_POST
def get_doc_info(request):
    response = {}
    document_id = int(request.POST.get("doc_id"))
    if document_id == 0:
        response["submission"] = {"status": "unsubmitted"}
        template_id = int(request.POST.get("template_id"))
    else:
        document = Document.objects.get(id=document_id)
        if (
            document.owner != request.user
            and AccessRight.objects.filter(
                document=document, user=request.user
            ).count()
            == 0
        ):
            # Access forbidden
            return HttpResponse("Missing access rights", status=403)
        template_id = document.template_id
        # OJS submission related
        response["submission"] = dict()
        revision = models.SubmissionRevision.objects.filter(
            document_id=document_id
        ).first()
        if revision:
            user_role = ""
            reviewer = revision.reviewer_set.filter(user=request.user).first()
            if reviewer:
                user_role = "reviewer"
            elif (
                revision.submission.author_set.filter(
                    user=request.user
                ).count()
                > 0
            ):
                # User with author role but not submission submitter as sub-author
                user_role = (
                    "author"
                    if revision.submission.submitter.id == request.user.id
                    else "sub-author"
                )
            else:
                editor = revision.submission.editor_set.filter(
                    user=request.user
                ).first()
                if editor and editor.role in constants.EDITOR_ROLES:
                    user_role = constants.EDITOR_ROLES[editor.role]

            response["submission"]["status"] = "submitted"
            response["submission"]["submission_id"] = revision.submission.id
            response["submission"]["version"] = revision.version
            response["submission"][
                "journal_id"
            ] = revision.submission.journal_id
            response["submission"]["user_role"] = user_role
            if reviewer and reviewer.method == "doubleanonymous":
                response["submission"]["contributors"] = {}
            else:
                response["submission"]["contributors"] = revision.contributors
        else:
            response["submission"]["status"] = "unsubmitted"
    journals = []
    for journal in models.Journal.objects.filter(templates=template_id):
        journals.append(
            {
                "id": journal.id,
                "name": journal.name,
                "editor_id": journal.editor_id,
                "ojs_jid": journal.ojs_jid,
            }
        )
    response["journals"] = journals

    status = 200
    return JsonResponse(response, status=status)


@login_required
@require_GET
async def get_journals(request):
    base_url = request.GET["url"]
    key = request.GET["key"]
    url = f"{base_url}{OJS_PLUGIN_PATH}journals"
    response = await helpers.send_async(
        Request("GET", url, params={"key": key})
    )
    return HttpResponse(response.content)


@login_required
@require_POST
async def author_submit(request):
    # Submitting a new submission revision.
    document_id = request.POST["doc_id"]
    revision = (
        await models.SubmissionRevision.objects.filter(document_id=document_id)
        .select_related(
            "submission__journal", "submission__submitter", "document"
        )
        .afirst()
    )
    request_user = await request.auser()
    if revision:
        # resubmission
        submission = revision.submission
        if submission.submitter != request_user:
            # Trying to submit revision for submission of other user
            return HttpResponseForbidden()
        data = {
            "submission_id": submission.ojs_jid,
            "version": revision.version,
        }
        journal = submission.journal
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = f"{base_url}{OJS_PLUGIN_PATH}authorSubmit"
        response = await helpers.send_async(
            Request(
                "POST",
                url,
                params={"key": key},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                content=urlencode(data),
            )
        )

        # submission was successful, so we replace the user's write access
        # rights with read rights.
        right = await AccessRight.objects.aget(
            user=request_user, document=revision.document
        )
        right.rights = "read"
        await right.asave()

        return HttpResponse(response.content)
    else:
        # The document is not part of an existing submission.
        journal_id = request.POST["journal_id"]
        journal = (
            await models.Journal.objects.filter(id=journal_id)
            .select_related("editor")
            .afirst()
        )
        template = await journal.templates.filter(
            document__id__exact=document_id
        ).afirst()
        if not template:
            # Template is not available for Journal.
            return HttpResponseForbidden()
        submission = await models.Submission.objects.acreate(
            submitter=request_user, journal_id=journal_id
        )
        version = "1.0.0"
        # Connect a new document to the submission.
        title = request.POST["title"]
        abstract = request.POST["abstract"]
        content = request.POST["content"]
        bibliography = request.POST["bibliography"]
        image_ids = request.POST.getlist("image_ids[]")

        images = []
        for id in image_ids:
            image = await Image.objects.filter(id=id).afirst()
            images.append(image)

        document = await helpers.create_doc_async(
            journal.editor,
            template,
            title,
            json.loads(content),
            json.loads(bibliography),
            images,
            {},
            submission.id,
            version,
        )
        revision = await models.SubmissionRevision.objects.acreate(
            submission=submission, version=version, document=document
        )

        fidus_url = request.build_absolute_uri("/")[:-1]

        data = {
            "username": request_user.username.encode("utf8"),
            "title": title.encode("utf8"),
            "abstract": abstract.encode("utf8"),
            "first_name": request.POST["firstname"].encode("utf8"),
            "last_name": request.POST["lastname"].encode("utf8"),
            "email": request_user.email.encode("utf8"),
            "affiliation": request.POST["affiliation"].encode("utf8"),
            "author_url": request.POST["author_url"].encode("utf8"),
            "journal_id": journal.ojs_jid,
            "fidus_url": fidus_url,
            "fidus_id": submission.id,
            "version": version,
        }
        key = journal.ojs_key
        base_url = journal.ojs_url
        url = f"{base_url}{OJS_PLUGIN_PATH}authorSubmit"
        try:
            response = await helpers.send_async(
                Request(
                    "POST",
                    url,
                    params={"key": key},
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    content=urlencode(data),
                )
            )
        except HTTPError:
            await document.adelete()
            await revision.adelete()
            raise
        # Set the submission ID from the response from the OJS server.
        body_json = json.loads(response.content)
        submission.ojs_jid = body_json["submission_id"]
        await submission.asave()

        # We save the author ID on the OJS site. Currently we are NOT using
        # this information for login purposes.
        author = await models.Author.objects.filter(
            submission=submission.id, ojs_jid=body_json["user_id"]
        ).afirst()
        if author is None:
            await models.Author.objects.acreate(
                user=request_user,
                submission=submission,
                ojs_jid=body_json["user_id"],
            )
            await AccessRight.objects.acreate(
                document=revision.document,
                holder_obj=request_user,
                path=revision.document.path,
                rights="read-without-comments",
            )
        return HttpResponse(response.content)


@login_required
@require_POST
async def copyedit_draft_submit(request):
    document_id = request.POST["doc_id"]
    request_user = await request.auser()
    revision = (
        await models.SubmissionRevision.objects.filter(document_id=document_id)
        .select_related("submission__journal")
        .afirst()
    )
    if not revision:
        return HttpResponseNotFound()
    if revision.version != "4.0.0":
        # version is not 4.0.0 (not copyedit draft)
        return HttpResponseForbidden()
    submission = revision.submission
    journal = submission.journal
    ojs_uid = False
    author = await submission.author_set.filter(user=request_user).afirst()
    if author:
        # User is the author
        ojs_uid = author.ojs_jid
    else:
        editor = await submission.editor_set.filter(user=request_user).afirst()
        if editor:
            # User is the one of the editors
            ojs_uid = editor.ojs_jid

    if not ojs_uid:
        # User is neither author nor editor
        return HttpResponseForbidden()

    data = {"submission_id": submission.ojs_jid, "ojs_uid": ojs_uid}
    key = journal.ojs_key
    base_url = journal.ojs_url
    url = f"{base_url}{OJS_PLUGIN_PATH}copyeditDraftSubmit"
    response = await helpers.send_async(
        Request(
            "POST",
            url,
            params={"key": key},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(data),
        )
    )

    # submission was successful, so we replace the user's write access
    # rights with read rights.
    right = await AccessRight.objects.aget(
        user=request_user, document=revision.document
    )
    right.rights = "read"
    await right.asave()
    return HttpResponse(response.content)


@login_required
@require_POST
async def reviewer_submit(request):
    # Submitting a new submission revision.
    document_id = request.POST["doc_id"]
    request_user = await request.auser()
    reviewer = (
        await models.Reviewer.objects.filter(
            revision__document_id=document_id, user=request_user
        )
        .select_related("revision__submission__journal", "revision__document")
        .afirst()
    )
    if reviewer is None:
        # Trying to submit review without access rights.
        return HttpResponseForbidden()
    data = {
        "submission_id": reviewer.revision.submission.ojs_jid,
        "version": reviewer.revision.version,
        "user_id": reviewer.ojs_jid,
        "editor_message": request.POST["editor_message"],
        "editor_author_message": request.POST["editor_author_message"],
        "recommendation": request.POST["recommendation"],
    }

    key = reviewer.revision.submission.journal.ojs_key
    base_url = reviewer.revision.submission.journal.ojs_url
    url = f"{base_url}{OJS_PLUGIN_PATH}reviewerSubmit"
    response = await helpers.send_async(
        Request(
            "POST",
            url,
            params={"key": key},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(data),
        )
    )
    # submission was successful, so we replace the user's write access
    # rights with read rights.
    right = await AccessRight.objects.aget(
        user=request_user, document=reviewer.revision.document
    )
    right.rights = "read"
    await right.asave()
    return HttpResponse(response.content)


# Get a user based on an email address. Used for registration of journal.
@staff_member_required
@require_POST
def get_user(request):
    response = {}
    status = 200
    email = request.POST.get("email")
    email_address = EmailAddress.objects.filter(email=email).first()
    if email_address:
        response["user_id"] = email_address.user.id
        response["user_name"] = email_address.user.username
    return JsonResponse(response, status=status)


# Save a journal. Used on custom admin page.
@staff_member_required
@require_POST
def save_journal(request):
    response = {}
    try:
        journal = models.Journal.objects.create(
            ojs_jid=request.POST.get("ojs_jid"),
            ojs_key=request.POST.get("ojs_key"),
            ojs_url=request.POST.get("ojs_url"),
            name=request.POST.get("name"),
            editor_id=request.POST.get("editor_id"),
        )
        dts = DocumentTemplate.objects.filter(user=None)
        for dt in dts:
            journal.templates.add(dt)
        status = 201
    except IntegrityError:
        status = 200
    return JsonResponse(response, status=status)


# Return an existing user or create a new one. The email/username come from
# OJS. We return an existing user if it has the same email as the OJS user
# as we expect OJS to have checked whether the user actually has access to the
# email. We do not automatically connect to a user with the same username,
# as this may be purely coincidental.
# NOTE: An evil OJS editor can get access to accounts that he does not have
# email access for this way.
def get_or_create_user(email, username):
    User = get_user_model()
    user_with_email = User.objects.filter(email=email).first()
    if user_with_email:
        return user_with_email
    # try to find an unused username, starting with the username used in OJS
    counter = 0
    usernamebase = username
    while User.objects.filter(username=username).first():
        username = f"{usernamebase}{counter}"
        counter += 1
    return User.objects.create_user(username, email)


# A reviewer has accepted a review. Give comment/review access to the reviewer.
@csrf_exempt
@require_POST
def accept_reviewer(request, submission_id, version):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    revision = models.SubmissionRevision.objects.get(
        submission_id=submission_id, version=version
    )
    journal_key = revision.submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        status = 403
        return JsonResponse(response, status=status)

    ojs_jid = int(request.POST.get("user_id"))
    reviewer = models.Reviewer.objects.filter(
        revision=revision, ojs_jid=ojs_jid
    ).first()
    if reviewer is None:
        response["error"] = "Unknown reviewer"
        status = 403
        return JsonResponse(response, status=status)
    review_method = request.POST.get("review_method")

    # ojs-fiduswriter < 3.0.0.0 specified "access_rights" instead of "review_method".
    if not review_method:
        if request.POST.get("access_rights") == "comment":
            review_method = "open"
        else:
            review_method = "doubleanonymous"

    reviewer.method = review_method
    reviewer.save()

    if review_method == "open":
        rights = "comment"
    else:
        rights = "review"
    # Make sure the connect document has reviewer access rights set for the
    # user.
    access_right = AccessRight.objects.filter(
        document=revision.document, user=reviewer.user
    ).first()
    if access_right is None:
        access_right = AccessRight(
            document=revision.document,
            holder_obj=reviewer.user,
            path=revision.document.path,
        )
        status = 201

    access_right.rights = rights
    access_right.save()
    return JsonResponse(response, status=status)


# Add a reviewer to the document connected to a SubmissionRevision as a
# reviewer.
# Also ensure that there is an Reviewer set up for the account to allow for
# password-less login from OJS.
@csrf_exempt
@require_POST
def add_reviewer(request, submission_id, version):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    revision = models.SubmissionRevision.objects.get(
        submission_id=submission_id, version=version
    )
    journal_key = revision.submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        status = 403
        return JsonResponse(response, status=status)

    ojs_jid = int(request.POST.get("user_id"))

    # Make sure there is an Reviewer/user registered for the reviewer.
    reviewer = models.Reviewer.objects.filter(
        revision=revision, ojs_jid=ojs_jid
    ).first()
    if reviewer is None:
        email = request.POST.get("email")
        username = request.POST.get("username")
        user = get_or_create_user(email, username)
        reviewer = models.Reviewer.objects.create(
            revision=revision, ojs_jid=ojs_jid, user=user
        )
        status = 201
    # Make sure the connect document has reviewer access rights set for the
    # user.
    access_right = AccessRight.objects.filter(
        document=revision.document, user=reviewer.user
    ).first()
    if access_right is None:
        access_right = AccessRight(
            document=revision.document,
            holder_obj=reviewer.user,
            path=revision.document.path,
        )
        status = 201
    access_right.rights = "read-without-comments"
    access_right.save()
    return JsonResponse(response, status=status)


@csrf_exempt
@require_POST
def remove_reviewer(request, submission_id, version):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    revision = models.SubmissionRevision.objects.get(
        submission_id=submission_id, version=version
    )
    journal_key = revision.submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        status = 403
        return JsonResponse(response, status=status)

    ojs_jid = int(request.POST.get("user_id"))
    # Delete reviewer access rights set for the corresponding user,
    # if there are any. Thereafter delete the Reviewer.
    reviewer = models.Reviewer.objects.filter(
        revision=revision, ojs_jid=ojs_jid
    ).first()
    if reviewer is None:
        response["error"] = "Unknown reviewer"
        status = 403
        return JsonResponse(response, status=status)
    AccessRight.objects.filter(
        document=revision.document, user=reviewer.user
    ).delete()
    reviewer.delete()
    return JsonResponse(response, status=status)


@csrf_exempt
@require_POST
def create_copy(request, submission_id):
    response = {}
    status = 201
    api_key = request.POST.get("key")
    old_version = request.POST.get("old_version")
    old_version_parts = old_version.split(".")
    old_version_stage = int(old_version_parts[0])

    new_version = request.POST.get("new_version")
    new_version_parts = new_version.split(".")
    new_version_stage = int(new_version_parts[0])

    revision = models.SubmissionRevision.objects.get(
        submission_id=submission_id, version=old_version
    )
    journal_key = revision.submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        status = 403
        return JsonResponse(response, status=status)

    # Copy the revision
    revision = helpers.copy_revision(
        revision, old_version_stage, new_version_stage, new_version
    )

    # Add user rights

    # Rights for editors
    granted_user_ids = request.POST.get("granted_users").split(",")
    if granted_user_ids:
        editors = models.Editor.objects.filter(submission=revision.submission)
        if editors is not None:
            for editor in editors:
                if str(editor.ojs_jid) in granted_user_ids:
                    role = int(editor.role)
                    rights = constants.EDITOR_ROLE_STAGE_RIGHTS[role][
                        new_version_stage
                    ]
                    AccessRight.objects.create(
                        document=revision.document,
                        holder_obj=editor.user,
                        path=revision.document.path,
                        rights=rights,
                    )

    # Rights for authors
    if new_version_stage == 4 or new_version_parts[-1] == "5":
        # We have an author version and we give the author write access.
        if new_version_stage == 4:
            access_right = "write-tracked"
        else:
            access_right = "write"

        authors = models.Author.objects.filter(submission=revision.submission)
        for author in authors:
            AccessRight.objects.create(
                document=revision.document,
                holder_obj=author.user,
                path=revision.document.path,
                rights=access_right,
            )

    return JsonResponse(response, status=status)


# Add a editor connected to a submission
# password-less login from OJS.
@csrf_exempt
@require_POST
def add_editor(request, submission_id):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        return JsonResponse(response, status=403)

    ojs_jid = int(request.POST.get("user_id"))

    # check, if editor account already exists
    editor = models.Editor.objects.filter(
        submission=submission_id, ojs_jid=ojs_jid
    ).first()

    # if no editor exists, create one
    if editor is None:
        email = request.POST.get("email")
        username = request.POST.get("username")
        role = request.POST.get("role")
        user = get_or_create_user(email, username)
        editor = models.Editor.objects.create(
            user=user, submission=submission, ojs_jid=ojs_jid, role=role
        )
        status = 201

    # create access_rights for existing revisions
    # get ids of stages access granted
    granted_stage_ids = request.POST.get("stage_ids").split(",")
    if granted_stage_ids:
        revisions = models.SubmissionRevision.objects.filter(
            submission_id=submission_id
        )
        if revisions is not None:
            for revision in revisions:
                version = revision.version.split(".")
                stage_id = version[0]
                if stage_id in granted_stage_ids:
                    access_right = AccessRight.objects.filter(
                        document=revision.document, user=editor.user
                    ).first()
                    if access_right is None:
                        role = int(editor.role)
                        rights = constants.EDITOR_ROLE_STAGE_RIGHTS[role][
                            int(stage_id)
                        ]
                        access_right = AccessRight(
                            document=revision.document,
                            holder_obj=editor.user,
                            path=revision.document.path,
                        )
                        access_right.rights = rights
                        access_right.save()
                        status = 201

    return JsonResponse(response, status=status)


# Remove editor
# password-less login from OJS.
@csrf_exempt
@require_POST
def remove_editor(request, submission_id):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        return JsonResponse(response, status=403)

    ojs_jid = int(request.POST.get("user_id"))

    # check, if editor account already exists
    editor = models.Editor.objects.filter(
        submission=submission_id, ojs_jid=ojs_jid
    ).first()
    if editor is None:
        response["error"] = "Unknown reviewer"
        status = 403
        return JsonResponse(response, status=status)

    revisions = models.SubmissionRevision.objects.filter(
        submission_id=submission_id
    )
    if revisions is not None:
        for revision in revisions:
            AccessRight.objects.filter(
                document=revision.document, user=editor.user
            ).delete()

    editor.delete()

    return JsonResponse(response, status=status)


# Add a author connected to a submission
# password-less login from OJS.
@csrf_exempt
@require_POST
def add_author(request, submission_id):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        return JsonResponse(response, status=403)

    ojs_jid = int(request.POST.get("user_id"))

    # check, if author account already exists
    author = models.Author.objects.filter(
        submission=submission_id, ojs_jid=ojs_jid
    ).first()

    # if no author exists, create one
    if author is None:
        email = request.POST.get("email")
        username = request.POST.get("username")
        user = get_or_create_user(email, username)
        author = models.Author.objects.create(
            user=user, submission=submission, ojs_jid=ojs_jid
        )
        status = 201

    # create access_rights for existing revisions
    # get ids of stages access granted
    revisions = models.SubmissionRevision.objects.filter(
        submission_id=submission_id
    )
    if revisions is not None:
        for revision in revisions:
            version = revision.version.split(".")
            stage_id = version[0]
            if (
                stage_id == "1"
                or stage_id == "4"
                or (stage_id == "3" and version[2] == "5")
            ):
                access_right = AccessRight.objects.filter(
                    document=revision.document, user=author.user
                ).first()

                if access_right is None:
                    access_right = AccessRight(
                        document=revision.document,
                        holder_obj=author.user,
                        path=revision.document.path,
                    )

                    if stage_id == "1":
                        access_right.rights = "read-without-comments"
                    elif stage_id == "3":
                        access_right.rights = "write"
                    else:
                        access_right.rights = "write-tracked"

                    access_right.save()
                    status = 201

    return JsonResponse(response, status=status)


# Remove author
# password-less login from OJS.
@csrf_exempt
@require_POST
def remove_author(request, submission_id):
    response = {}
    status = 200
    api_key = request.POST.get("key")
    submission = models.Submission.objects.get(id=submission_id)
    journal_key = submission.journal.ojs_key
    if journal_key != api_key:
        # Access forbidden
        response["error"] = "Wrong key"
        return JsonResponse(response, status=403)

    ojs_jid = int(request.POST.get("user_id"))

    # check, if author account already exists
    author = models.Author.objects.filter(
        submission=submission_id, ojs_jid=ojs_jid
    ).first()
    if author is None:
        response["error"] = "Unknown reviewer"
        status = 403
        return JsonResponse(response, status=status)

    revisions = models.SubmissionRevision.objects.filter(
        submission_id=submission_id
    )
    if revisions is not None:
        for revision in revisions:
            AccessRight.objects.filter(
                document=revision.document, user=author.user
            ).delete()

    author.delete()

    return JsonResponse(response, status=status)
