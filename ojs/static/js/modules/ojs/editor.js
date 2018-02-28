import {BibliographyDB} from "../bibliography/database"
import {ImageDB} from "../images/database"
import {addAlert, csrfToken, activateWait, deactivateWait} from "../common"
import {handleFetchErrors} from "./common"
import {SaveCopy} from "../exporter/native"
import {firstSubmissionDialogTemplate, resubmissionDialogTemplate, reviewSubmitDialogTemplate} from "./templates"
import {SendDocSubmission} from "./submit-doc"
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
        let body = new window.FormData()
        body.append('doc_id', this.editor.docInfo.id)
        body.append('csrfmiddlewaretoken', csrfToken)

        return fetch('/ojs/get_doc_info/', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            response => response.json()
        ).then(
            json => {
                this.submission = json['submission']
                this.journals = json['journals']
                this.setupUI()
            }
        ).catch(
            () => addAlert('error', gettext('Could not obtain submission info.'))
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
        let diaButtons = {}, that = this

        diaButtons[gettext("Submit")] = function() {
            let journalId = parseInt(jQuery("#submission-journal").val())
            let firstname = jQuery("#submission-firstname").val().trim()
            let lastname = jQuery("#submission-lastname").val().trim()
            let affiliation = jQuery("#submission-affiliation").val().trim()
            let authorUrl = jQuery("#submission-author-url").val().trim()
            let abstract = jQuery("#submission-abstract").val().trim()
            if (firstname==="" || lastname==="" || abstract==="") {
                addAlert('error', gettext('Firstname, lastname and abstract are obligatory fields!'))
                return
            }
            that.submitDoc({journalId, firstname, lastname, affiliation, authorUrl, abstract})
            jQuery(this).dialog("close")
        }

        diaButtons[gettext("Cancel")] = function() {
            jQuery(this).dialog("close")
        }

        let abstractNode = this.editor.docInfo.confirmedDoc.firstChild.content.content.find(node => node.type.name==='abstract')

        jQuery(firstSubmissionDialogTemplate({
            journals: this.journals,
            first_name: this.editor.user.first_name,
            last_name: this.editor.user.last_name,
            abstract: abstractNode.attrs.hidden ? '' : abstractNode.textContent
        })).dialog({
            autoOpen: true,
            height: 700,
            width: 800,
            modal: true,
            buttons: diaButtons,
            create: function() {
                let theDialog = jQuery(this).closest(".ui-dialog")
                theDialog.find(".ui-button:first-child").addClass("fw-button fw-dark")
                theDialog.find(".ui-button:last").addClass("fw-button fw-orange")
            }
        })
    }

    /* Dialog for submission of all subsequent revisions */
    resubmissionDialog() {
        let buttons = [], dialog
        buttons.push({
            text: gettext('Cancel'),
            click: () => {
                dialog.dialog('close')
            },
            class: 'fw-button fw-orange'
        })
        buttons.push({
            text: gettext('Send'),
            click: () => {
                this.submitResubmission()
                dialog.dialog('close')
            },
            class: 'fw-button fw-dark'
        })
        dialog = jQuery(resubmissionDialogTemplate()).dialog({
            autoOpen: true,
            height: 100,
            width: 300,
            modal: true,
            buttons
        })
    }

    submitResubmission() {
        let body = new window.FormData()
        body.append('doc_id', this.editor.docInfo.id)

        fetch('/proxy/ojs/author_submit', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            () => {
                addAlert('success', gettext('Resubmission successful'))
                window.setTimeout(() => window.location.reload(), 2000)
            }
        ).catch(
            () => addAlert('error', gettext('Review could not be submitted.'))
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
        let buttons = [], dialog
        buttons.push({
            text: gettext('Cancel'),
            click: () => {
                dialog.dialog('close')
            },
            class: 'fw-button fw-orange'
        })
        buttons.push({
            text: gettext('Send'),
            click: () => {
                if (this.submitReview()) {
                    dialog.dialog('close')
                }
            },
            class: 'fw-button fw-dark'
        })
        jQuery("#review-message").remove()
        dialog = jQuery(reviewSubmitDialogTemplate()).dialog({
            autoOpen: true,
            height: 490,
            width: 350,
            modal: true,
            buttons
        })
    }

    // Send the opinion of the reviewer to OJS.
    submitReview() {
        let editorMessage = jQuery("#message-editor").val(),
            editorAuthorMessage = jQuery("#message-editor-author").val(),
            recommendation = jQuery("#recommendation").val()
        if (editorMessage === '' || editorAuthorMessage === '' || recommendation === '') {
            addAlert('error', gettext('Fill out all fields before submitting!'))
            return false
        }
        let body = new window.FormData()
        body.append('doc_id', this.editor.docInfo.id)
        body.append('editor_message', editorMessage)
        body.append('editor_author_message', editorAuthorMessage)
        body.append('recommendation', recommendation)
        activateWait()

        fetch('/proxy/ojs/reviewer_submit', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            () => {
                deactivateWait()
                addAlert('success', gettext('Review submitted'))
                window.setTimeout(() => window.location.reload(), 2000)
            }
        ).catch(
            () => addAlert('error', gettext('Review could not be submitted.'))
        )
        return true
    }

}
