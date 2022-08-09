from os import path
from document.models import Document
from usermedia.models import Image, DocumentImage
from django.conf import settings
from django.core.files import File


def create_revision(
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
    revision = Document()
    revision.owner = owner
    revision.template = template
    revision.title = title
    revision.content = content
    revision.bibliography = bibliography
    revision.path = f"/Submission {submission_id}/{title.replace('/', '')} ({revision_version})"
    revision.comments = comments
    revision.save()

    for image in images:
        if image is None:
            image = Image()
            image.uploader = owner
            f = open(
                path.join(settings.PROJECT_PATH, "base/static/img/error.png")
            )
            image.image.save("error.png", File(f))
            image.save()

        DocumentImage.objects.create(document=revision, image=image, title="")

    return revision


def copy_doc(doc, journal_editor, submission, revision_version):
    images = []
    doc_images = doc.documentimage_set.all()
    for doc_image in doc_images:
        images.append(doc_image.image)
    content = doc.content
    contributors = submission.contributors
    if revision_version == "4.0.0" and len(contributors):
        # Readd author information after review process.
        for part in content["content"]:
            if (
                "type" in part
                and part["type"] == "contributors_part"
                and "attrs" in part
                and part["attrs"]["id"] in contributors
            ):
                part["content"] = contributors[part["attrs"]["id"]]
    return create_revision(
        journal_editor,
        doc.template,
        doc.title,
        content,
        doc.bibliography,
        images,
        doc.comments,
        submission.id,
        revision_version,
    )
