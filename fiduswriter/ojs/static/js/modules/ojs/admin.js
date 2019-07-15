import {noSpaceTmp, addAlert, getJson, postJson, post, findTarget} from "../common"
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
        document.addEventListener('click', event => {
            const el = {}
            switch (true) {
                case findTarget(event, '#get_journals', el):
                    this.getJournals()
                    break
                case findTarget(event, '.related-lookup', el): {
                    // The following is slightly modified from the binding function in the
                    // admin interface to allow for lookups in fields that are added to the
                    // DOM at a later stage.
                    const nEvent = window.django.jQuery.Event('django:lookup-related') // using django's builtin jQuery as required
                    window.django.jQuery(el.target).trigger(nEvent) // using django's builtin jQuery as required
                    break
                }
                case findTarget(event, '.register-submit', el): {
                    const journalId = el.target.dataset.id
                    this.saveJournal(journalId)
                    break
                }
                default:
                    break
            }
        })
    }

    getJournals() {
        this.ojsUrl = document.getElementById('ojs_url').value
        this.ojsKey = document.getElementById('ojs_key').value
        if (this.ojsUrl.length === 0 || this.ojsKey.length === 0) {
            addAlert('error', gettext('Provide a URL for the OJS server and the key to access it.'))
            return
        }
        getJson(
            '/proxy/ojs/journals',
            {url: this.ojsUrl, key: this.ojsKey}
        ).then(
            json => {
                const journals = json['journals']
                    .sort((a, b) => parseInt(a.id) - parseInt(b.id))
                const emailLookups = []
                journals.forEach(journal => {
                    if (!journal.contact_email) {
                        return
                    }
                    const emailLookup = this.getUser(journal.contact_email).then(
                        user => {
                            if (user) {
                                Object.assign(journal, user)
                            }
                        }
                    ).catch(
                        _error => {
                            addAlert('info', gettext(`Cannot find Fidus Writer user corresponding to email: ${journal.contact_email}`))
                        }
                    )
                    emailLookups.push(emailLookup)
                })
                return Promise.all(emailLookups).then(() => {
                    const journalHTML = journals
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
            error => {
                addAlert('error', gettext('Could not connect to OJS server.'))
                throw (error)
            }
        )

    }

    getUser(email) {
        return postJson(
            '/api/ojs/get_user/',
            {email}
        ).then(
            ({json}) => {return json}
        )
    }

    saveJournal(ojs_jid) {
        const name = document.getElementById(`journal_name_${ojs_jid}`).value
        const editor = document.getElementById(`editor_${ojs_jid}`).value
        if (name.length === 0 || editor.length === 0) {
            addAlert('error', gettext('Editor and journal name need to be filled out.'))
            return
        }
        const editor_id = parseInt(editor)
        if (isNaN(editor_id)) {
            addAlert('error', gettext('Editor needs to be the ID number of the editor user.'))
            return
        }

        post(
            '/api/ojs/save_journal/',
            {
                editor_id,
                name,
                ojs_jid,
                ojs_key: this.ojsKey,
                ojs_url: this.ojsUrl
            }
        ).then(
            response => {
                if (response.status===201) {
                    addAlert('info', gettext('Journal saved.'))
                } else {
                    addAlert('warning', gettext('Journal already present on server.'))
                }
                const journalEl = document.getElementById(`journal_${ojs_jid}`)
                journalEl.parentElement.removeChild(journalEl)
            }
        ).catch(
            error => {
                addAlert('error', gettext('Could not save journal. Please check form.'))
                throw (error)
            }
        )

    }
}
