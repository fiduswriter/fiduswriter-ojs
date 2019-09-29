import {addAlert, activateWait, deactivateWait, postJson, post, Dialog} from "../common"
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
        const docData = {
            doc_id: this.editor.docInfo.id
        }
        if (this.editor.docInfo.templateId) {
          // Document has not been initialized yet, but we have the template id
          docData.template_id = this.editor.docInfo.templateId
        }
        postJson(
            '/api/ojs/get_doc_info/',
            docData
        ).then(
            ({json}) => {
                this.submission = json['submission']
                this.journals = json['journals']
                this.setupUI()
            }
        ).catch(
            error => {
                addAlert('error', gettext('Could not obtain submission info.'))
                throw (error)
            }
        )

    }

    setupUI() {
        if (this.journals.length === 0) {
            // This installation does not have any journals setup. Abort.
            return Promise.resolve()
        }

        const fileMenu = this.editor.menu.headerbarModel.content.find(menu => menu.id==='file')
        fileMenu.content.push({
            title: gettext('Submit to journal'),
            type: 'action',
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

        const buttons = [
            {
                text: gettext("Submit"),
                classes: "fw-dark",
                click: () => {
                    const journalId = parseInt(document.getElementById("submission-journal").value)
                    const firstname = document.getElementById("submission-firstname").value.trim()
                    const lastname = document.getElementById("submission-lastname").value.trim()
                    const affiliation = document.getElementById("submission-affiliation").value.trim()
                    const authorUrl = document.getElementById("submission-author-url").value.trim()
                    const abstract = document.getElementById("submission-abstract").value.trim()
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

        const abstractNode = this.editor.docInfo.confirmedDoc.firstChild.content.content.find(node => node.attrs && node.attrs.metadata==='abstract')
        const authorsNode = this.editor.docInfo.confirmedDoc.firstChild.content.content.find(node => node.attrs && node.attrs.metadata==='authors')
        const authorNode = authorsNode && authorsNode.childCount ? authorsNode.firstChild : false
        const dialog = new Dialog({
            height: 460,
            width: 800,
            buttons,
            title: gettext('Complete missing information and choose journal'),
            body: firstSubmissionDialogTemplate({
                journals: this.journals,
                first_name: authorNode ? authorNode.attrs.firstname : this.editor.user.first_name,
                last_name: authorNode ? authorNode.attrs.lastname : this.editor.user.last_name,
                affiliation: authorNode ? authorNode.attrs.institution : '',
                abstract: !abstractNode || abstractNode.attrs.hidden ? '' : abstractNode.textContent
            })
        })
        dialog.open()
    }

    /* Dialog for submission of all subsequent revisions */
    resubmissionDialog() {
        const buttons = [
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
            ],
            dialog = new Dialog({
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
                throw (error)
            }
        )
    }

    submitDoc({journalId, firstname, lastname, affiliation, authorUrl, abstract}) {
        const submitter = new SendDocSubmission({
            doc: this.editor.getDoc(),
            templateId: this.editor.docInfo.template.id,
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
        const buttons = [
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
            ],
            reviewMessageEl = document.getElementById('review-message'),
            dialog = new Dialog({
                height: 350,
                width: 350,
                id: "review-message",
                title: gettext('Leave your messages for editor and authors'),
                body: reviewSubmitDialogTemplate(),
                buttons
            })
        if (reviewMessageEl) {
            reviewMessageEl.parentElement.removeChild(reviewMessageEl)
        }

        dialog.open()
    }

    // Send the opinion of the reviewer to OJS.
    submitReview() {
        const editor_message = document.getElementById("message-editor").value,
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
                throw (error)
            }
        )
        return true
    }

}
