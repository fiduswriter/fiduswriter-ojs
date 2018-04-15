import {BibliographyDB} from "../bibliography/database"
import {ImageDB} from "../images/database"
import {addAlert, activateWait, deactivateWait, postJson, post, Dialog} from "../common"
import {SaveCopy} from "../exporter/native"
import {firstSubmissionDialogTemplate, resubmissionDialogTemplate, reviewSubmitDialogTemplate} from "./templates"
import {SendDocSubmission} from "./submit_doc"
import {READ_ONLY_ROLES, COMMENT_ONLY_ROLES} from "../editor"

// Adds functions for OJS to the editor
export class EditorOJS {
    constructor(editor) {
        this.editor = editor
        this.submission = {
            status: 'unknown'
        }
        this.journals = false
    }

    init() {

        postJson(
            '/ojs/get_doc_info/',
            {
                doc_id: this.editor.docInfo.id
            }
        ).then(
            ({json}) => {
                this.submission = json['submission']
                this.journals = json['journals']
                this.setupUI()
            }
        ).catch(
            error => {
                addAlert('error', gettext('Could not obtain submission info.'))
                throw(error)
            }
        )

    }

    setupUI() {
        if (this.journals.length === 0) {
            // This installation does not have any journals setup. Abort.
            return Promise.resolve()
        }

        this.editor.menu.toolbarModel.content.push(
            {
                id: 'submit-ojs',
                type: 'button',
                title: gettext('Submit to journal'),
                icon: 'paper-plane',
                action: editor => {
                    if (this.submission.status === 'submitted') {
                        if (this.submission.user_role === 'author') {
                            this.resubmissionDialog()
                        } else if (this.submission.user_role === 'reviewer') {
                            this.reviewerDialog()
                        }
                    } else {
                        this.firstSubmissionDialog()
                    }
                },
                disabled: editor => {
                    if (
                        READ_ONLY_ROLES.includes(editor.docInfo.access_rights) ||
                        (
                            COMMENT_ONLY_ROLES.includes(editor.docInfo.access_rights) &&
                            this.submission.status !== 'submitted'
                        ) ||
                        (
                            this.submission.status === 'submitted' &&
                            editor.docInfo.access_rights === 'write' &&
                            this.submission.version.slice(-1) === '0'
                        ) ||
                        (
                            this.submission.status === 'submitted' &&
                            this.submission.user_role === 'editor'
                        )
                    ) {
                        return true
                    } else {
                        return false
                    }
                }
            }
        )
        let fileMenu = this.editor.menu.headerbarModel.content.find(menu => menu.id==='file')
        fileMenu.content.push({
            title: gettext('Submit to journal'),
            type: 'action',
            icon: 'paper-plane',
            tooltip: gettext('Submit to journal'),
            action: editor => {
                if (this.submission.status === 'submitted') {
                    if (COMMENT_ONLY_ROLES.includes(editor.docInfo.access_rights)) {
                        this.reviewerDialog()
                    } else {
                        this.resubmissionDialog()
                    }
                } else {
                    this.firstSubmissionDialog()
                }
            },
            disabled: editor => {
                if (
                    READ_ONLY_ROLES.includes(editor.docInfo.access_rights) ||
                    (
                        COMMENT_ONLY_ROLES.includes(editor.docInfo.access_rights) &&
                        this.submission.status !== 'submitted'
                    ) ||
                    (
                        this.submission.status === 'submitted' &&
                        editor.docInfo.access_rights === 'write' &&
                        this.submission.version.slice(-1) === '0'
                    )
                ) {
                    return true
                } else {
                    return false
                }
            }
        })
        return Promise.resolve()
    }

    // Dialog for an article that has no submisison status. Includes selection of journal.
    firstSubmissionDialog() {

        let dialog

        let buttons = [
            {
                text: gettext("Submit"),
                classes: "fw-dark",
                click: () => {
                    let journalId = parseInt(document.getElementById("submission-journal").value)
                    let firstname = document.getElementById("submission-firstname").value.trim()
                    let lastname = document.getElementById("submission-lastname").value.trim()
                    let affiliation = document.getElementById("submission-affiliation").value.trim()
                    let authorUrl = document.getElementById("submission-author-url").value.trim()
                    let abstract = document.getElementById("submission-abstract").value.trim()
                    if (firstname==="" || lastname==="" || abstract==="") {
                        addAlert('error', gettext('Firstname, lastname and abstract are obligatory fields!'))
                        return
                    }
                    this.submitDoc({journalId, firstname, lastname, affiliation, authorUrl, abstract})
                    dialog.close()
                }
            },
            {
                type: 'cancel'
            }
        ]

        let abstractNode = this.editor.docInfo.confirmedDoc.firstChild.content.content.find(node => node.type.name==='abstract')

        dialog = new Dialog({
            height: 560,
            width: 800,
            buttons,
            title: gettext('Complete missing information and choose journal'),
            body: firstSubmissionDialogTemplate({
                journals: this.journals,
                first_name: this.editor.user.first_name,
                last_name: this.editor.user.last_name,
                abstract: abstractNode.attrs.hidden ? '' : abstractNode.textContent
            })
        })
        dialog.open()
    }

    /* Dialog for submission of all subsequent revisions */
    resubmissionDialog() {
        let dialog
        let buttons = [
            {
                text: gettext('Send'),
                click: () => {
                    this.submitResubmission()
                    dialog.close()
                },
                classes: 'fw-dark'
            },
            {
                type: 'cancel'
            }
        ]
        dialog = new Dialog({
            height: 50,
            width: 300,
            buttons,
            title: gettext('Resubmit'),
            body: resubmissionDialogTemplate()
        })
        dialog.open()
    }

    submitResubmission() {

        post(
            '/proxy/ojs/author_submit',
            {
                doc_id: this.editor.docInfo.id
            }
        ).then(
            () => {
                addAlert('success', gettext('Resubmission successful'))
                window.setTimeout(() => window.location.reload(), 2000)
            }
        ).catch(
            error => {
                addAlert('error', gettext('Review could not be submitted.'))
                throw(error)
            }
        )
    }

    submitDoc({journalId, firstname, lastname, affiliation, authorUrl, abstract}) {
        let submitter = new SendDocSubmission({
            doc: this.editor.getDoc(),
            imageDB: this.editor.mod.db.imageDB,
            bibDB: this.editor.mod.db.bibDB,
            journalId,
            firstname,
            lastname,
            affiliation,
            authorUrl,
            abstract
        })
        return submitter.init()
    }

    // The dialog for a document reviewer.
    reviewerDialog() {
        let dialog
        let buttons = [
            {
                text: gettext('Send'),
                click: () => {
                    if (this.submitReview()) {
                        dialog.close()
                    }
                },
                classes: 'fw-dark'
            },
            {
                type: 'cancel'
            }
        ]
        let reviewMessageEl = document.getElementById('review-message')
        if (reviewMessageEl) {
            reviewMessageEl.parentElement.removeChild(reviewMessageEl)
        }

        dialog = new Dialog({
            height: 350,
            width: 350,
            id: "review-message",
            title: gettext('Leave your messages for editor and authors'),
            body: reviewSubmitDialogTemplate(),
            buttons
        })
        dialog.open()
    }

    // Send the opinion of the reviewer to OJS.
    submitReview() {
        let editor_message = document.getElementById("message-editor").value,
            editor_author_message = document.getElementById("message-editor-author").value,
            recommendation = document.getElementById("recommendation").value
        if (editor_message === '' || editor_author_message === '' || recommendation === '') {
            addAlert('error', gettext('Fill out all fields before submitting!'))
            return false
        }
        activateWait()
        post(
            '/proxy/ojs/reviewer_submit',
            {
                doc_id: this.editor.docInfo.id,
                editor_message,
                editor_author_message,
                recommendation
            }
        ).then(
            () => {
                deactivateWait()
                addAlert('success', gettext('Review submitted'))
                window.setTimeout(() => window.location.reload(), 2000)
            }
        ).catch(
            error => {
                addAlert('error', gettext('Review could not be submitted.'))
                throw(error)
            }
        )
        return true
    }

}
