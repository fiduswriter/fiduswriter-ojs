import {noSpaceTmp, csrfToken, addAlert} from "../common"
import {handleFetchErrors} from "./common"
// Adds capabilities for admins to register journals

export class AdminRegisterJournals {
    constructor() {
        this.journals = []
        this.ojsUrl = ''
        this.ojsKey = ''
    }

    init() {
        this.bind()
    }

    bind() {
        jQuery(document).on('click', '#get_journals', () => this.getJournals())
        // The following is slightly modified from the binding function in the
        // admin interface to allow for lookups in fields that are added to the
        // DOM at a later stage.
        jQuery(document).on('click', '.related-lookup', function(e) {
            e.preventDefault()
            var event = jQuery.Event('django:lookup-related')
            jQuery(this).trigger(event)
            if (!event.isDefaultPrevented()) {
                window.showRelatedObjectLookupPopup(this)
            }
        })
        let that = this
        jQuery(document).on('click', '.register-submit', function(event) {
            let journalId = jQuery(this).attr('data-id')
            that.saveJournal(journalId)
        })
    }

    getJournals() {
        this.ojsUrl = jQuery('#ojs_url').val()
        this.ojsKey = jQuery('#ojs_key').val()
        if (this.ojsUrl.length === 0 || this.ojsKey.length === 0) {
            addAlert('error', gettext('Provide a URL for the OJS server and the key to access it.'))
            return
        }

        fetch(`/proxy/ojs/journals?url=${encodeURIComponent(this.ojsUrl)}&key=${encodeURIComponent(this.ojsKey)}`, {
            method: "GET",
            credentials: 'same-origin',
        }).then(
            handleFetchErrors
        ).then(
            response => response.json()
        ).then(
            json => {
                let journals = json['journals']
                    .sort((a, b) => parseInt(a.id) - parseInt(b.id))
                let emailLookups = []
                journals.forEach(journal => {
                    if (!journal.contact_email) {
                        return
                    }
                    let emailLookup = this.getUser(journal.contact_email).then(
                        user => {
                            if (user) {
                                Object.assign(journal, user)
                            }
                        }
                    )
                    emailLookups.push(emailLookup)
                })
                return Promise.all(emailLookups).then(() => {
                    let journalHTML = journals
                        .map(journal =>
                        noSpaceTmp`
                            <div id="journal_${journal.id}">
                                <b>${journal.id}</b>&nbsp;
                                <input type="text" value="${journal.name}" id="journal_name_${journal.id}">&nbsp;
                                ${gettext('Editor')} :
                                <input type="text" class="vForeignKeyRawIdAdminField" value="${journal.user_id ? journal.user_id : ''}" id="editor_${journal.id}">
                                <a href="/admin/auth/user/?_to_field=id" class="related-lookup" id="lookup_editor_${journal.id}" title="Lookup"></a>&nbsp;
                                <strong>${journal.user_name ? journal.user_name : ''}</strong>
                                <button data-id="${journal.id}" class="register-submit">${gettext('Register')}</button>
                            </div>`
                    ).join('')
                    document.getElementById('journal_form').innerHTML = journalHTML
                })
            }
        ).catch(
            () => addAlert('error', gettext('Could not connect to OJS server.'))
        )

    }

    getUser(email) {
        let body = new window.FormData()
        body.append('email', email)
        body.append('csrfmiddlewaretoken', csrfToken)

        return fetch('/ojs/get_user/', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            response => response.json()
        ).catch(
            error => addAlert('info', gettext(`Cannot find Fidus Writer user corresponding to email: ${email}`))
        )

    }

    saveJournal(ojs_jid) {
        let name = jQuery(`#journal_name_${ojs_jid}`).val()
        let editor = jQuery(`#editor_${ojs_jid}`).val()
        if (name.length === 0 || editor.length === 0) {
            addAlert('error', gettext('Editor and journal name need to be filled out.'))
            return
        }
        let editor_id = parseInt(editor)
        if (isNaN(editor_id)) {
            addAlert('error', gettext('Editor needs to be the ID number of the editor user.'))
            return
        }

        let body = new window.FormData()
        body.append('editor_id', editor_id)
        body.append('name', name)
        body.append('ojs_jid', ojs_jid)
        body.append('ojs_key', this.ojsKey)
        body.append('ojs_url', this.ojsUrl)
        body.append('csrfmiddlewaretoken', csrfToken)

        fetch('/ojs/save_journal/', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            response => {
                if (response.status===201) {
                    addAlert('info', gettext('Journal saved.'))
                } else {
                    addAlert('warning', gettext('Journal already present on server.'))
                }
                let journalEl = document.getElementById(`journal_${ojs_jid}`)
                journalEl.parentElement.removeChild(journalEl)
            },
            () => addAlert('error', gettext('Could not save journal. Please check form.'))
        )

    }
}
