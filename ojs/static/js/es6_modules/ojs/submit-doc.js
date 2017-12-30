import {ShrinkFidus} from "../exporter/native/shrink"
import {createSlug} from "../exporter/tools/file"
import {addAlert, csrfToken} from "../common"
import {handleFetchErrors} from "./common"
// Send an article submission to FW and OJS servers.

export class SendDocSubmission {
    constructor({
        doc,
        imageDB,
        bibDB,
        journalId,
        firstname,
        lastname,
        affiliation,
        authorUrl,
        abstract
    }) {
        this.doc = doc
        this.imageDB = imageDB
        this.bibDB = bibDB
        this.journalId = journalId
        this.firstname = firstname
        this.lastname = lastname
        this.affiliation = affiliation
        this.authorUrl = authorUrl
        this.abstract = abstract
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
        let body = new window.FormData()
        body.append('journal_id', this.journalId)
        body.append('firstname', this.firstname)
        body.append('lastname', this.lastname)
        body.append('affiliation', this.affiliation)
        body.append('author_url', this.authorUrl)
        body.append('doc_id', this.doc.id)
        body.append('title', this.doc.title)
        body.append('abstract', this.abstract)
        body.append('contents', JSON.stringify(this.doc.contents))
        body.append('bibliography', JSON.stringify(bibDB))
        body.append('image_ids', Object.keys(imageDB))

        return fetch('/proxy/ojs/author_submit', {
            method: "POST",
            credentials: 'same-origin',
            body
        }).then(
            handleFetchErrors
        ).then(
            () => addAlert('success', gettext('Article submitted'))
        ).catch(
            () => addAlert('error', gettext('Article could not be submitted.'))
        )
    }

}
