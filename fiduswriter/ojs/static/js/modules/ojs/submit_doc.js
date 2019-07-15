import {ShrinkFidus} from "../exporter/native/shrink"
import {addAlert, post} from "../common"
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
        const shrinker = new ShrinkFidus(
            this.doc,
            this.imageDB,
            this.bibDB
        )

        shrinker.init().then(
            ({shrunkImageDB, shrunkBibDB}) => {
                this.uploadRevision(shrunkBibDB, shrunkImageDB)
            }
        )
    }

    uploadRevision(bibDB, imageDB) {
        post(
            '/proxy/ojs/author_submit',
            {
                journal_id: this.journalId,
                firstname: this.firstname,
                lastname: this.lastname,
                affiliation: this.affiliation,
                author_url: this.authorUrl,
                doc_id: this.doc.id,
                title: this.doc.title,
                abstract: this.abstract,
                contents: JSON.stringify(this.doc.contents),
                bibliography: JSON.stringify(bibDB),
                image_ids: Object.keys(imageDB)
            }
        ).then(
            () => addAlert('success', gettext('Article submitted'))
        ).catch(
            error => {
                addAlert('error', gettext('Article could not be submitted.'))
                throw (error)
            }
        )
    }

}
