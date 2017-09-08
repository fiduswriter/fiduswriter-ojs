import {ShrinkFidus} from "../exporter/native/shrink"
import {createSlug} from "../exporter/tools/file"
import {addAlert, csrfToken} from "../common"

// Send an article submission to FW and OJS servers.

export class SendDocSubmission {
    constructor(
        doc,
        imageDB,
        bibDB,
        journalId,
        firstname,
        lastname,
        affiliation,
        webpage
    ) {
        this.doc = doc
        this.imageDB = imageDB
        this.bibDB = bibDB
        this.journalId = journalId
        this.firstname = firstname
        this.lastname = lastname
        this.affiliation = affiliation
        this.webpage = webpage
    }

    init() {
        let shrinker = new ShrinkFidus(
            this.doc,
            this.imageDB,
            this.bibDB
        )

        shrinker.init().then(
            ({doc, shrunkImageDB, shrunkBibDB, httpIncludes}) => {
                this.uploadRevision(shrunkBibDB, shrunkImageDB)
            }
        )
    }

    uploadRevision(bibDB, imageDB) {
        let data = new window.FormData()
        data.append('journal_id', this.journalId)
        data.append('firstname', this.firstname)
        data.append('lastname', this.lastname)
        data.append('affiliation', this.affiliation)
        data.append('webpage', this.webpage)
        data.append('doc_id', this.doc.id)
        data.append('title', this.doc.title)
        data.append('contents', JSON.stringify(this.doc.contents))
        data.append('bibliography', JSON.stringify(bibDB))
        data.append('image_ids', Object.keys(imageDB))

        jQuery.ajax({
            url: '/proxy/ojs/author_submit',
            data,
            type: 'POST',
            cache: false,
            contentType: false,
            processData: false,
            crossDomain: false, // obviates need for sameOrigin test
            beforeSend: (xhr, settings) =>
                xhr.setRequestHeader("X-CSRFToken", csrfToken),
            success: () => addAlert('success', gettext('Article submitted')),
            error: () => addAlert('error', gettext('Article could not be submitted.'))
        })
    }

}
