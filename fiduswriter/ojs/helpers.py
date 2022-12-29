from os import path
from document.models import Document
from usermedia.models import Image, DocumentImage
from django.conf import settings
from django.core.files import File


def create_doc(
    owner,
    template,
    title,
    content,
    bibliography,
    images,
    comments,
    submission_id,
    revision_version,
):
    doc = Document()
    doc.owner = owner
    doc.template = template
    doc.title = title
    doc.content = content
    doc.bibliography = bibliography
    doc.path = f"/Submission {submission_id}/{title.replace('/', '')} ({revision_version})"
    doc.comments = comments
    doc.save()

    for image in images:
        if image is None:
            image = Image()
            image.uploader = owner
            f = open(
                path.join(settings.PROJECT_PATH, "base/static/img/error.png")
            )
            image.image.save("error.png", File(f))
            image.save()

        DocumentImage.objects.create(document=doc, image=image, title="")

    return doc


def copy_revision(revision, old_version_stage, new_version_stage, new_version):
    images = []
    doc_images = revision.document.documentimage_set.all()
    for doc_image in doc_images:
        images.append(doc_image.image)
    content = revision.document.content
    if old_version_stage < 3 and new_version_stage == 3:
        # Remove author information at start of review process.
        revision.contributors = {}
        for part in content["content"]:
            if (
                "type" in part
                and part["type"] == "contributors_part"
                and "content" in part
                and "attrs" in part
                and "id" in part["attrs"]
            ):
                revision.contributors[part["attrs"]["id"]] = part["content"]
                part["content"] = []
    elif (
        old_version_stage == 3
        and new_version_stage > 3
        and len(revision.contributors)
    ):
        # Readd author information after review process.
        for part in content["content"]:
            if (
                "type" in part
                and part["type"] == "contributors_part"
                and "attrs" in part
                and part["attrs"]["id"] in revision.contributors
            ):
                part["content"] = revision.contributors[part["attrs"]["id"]]
        revision.contributors = {}
    document = create_doc(
        revision.submission.journal.editor,
        revision.document.template,
        revision.document.title,
        content,
        revision.document.bibliography,
        images,
        revision.document.comments,
        revision.submission.id,
        new_version,
    )

    # Copy revision
    revision.pk = None
    revision.document = document
    revision.version = new_version
    revision.save()

    return revision
