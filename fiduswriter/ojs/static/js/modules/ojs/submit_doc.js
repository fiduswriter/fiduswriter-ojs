import {addAlert, post} from "../common"
import {ShrinkFidus} from "../exporter/native/shrink"
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
        const shrinker = new ShrinkFidus(this.doc, this.imageDB, this.bibDB)

        shrinker.init().then(({shrunkImageDB, shrunkBibDB}) => {
            const content = JSON.parse(JSON.stringify(this.doc.content))
            this.uploadRevision(content, shrunkBibDB, shrunkImageDB)
        })
    }

    uploadRevision(content, bibDB, imageDB) {
        post("/api/ojs/author_submit/", {
            journal_id: this.journalId,
            firstname: this.firstname,
            lastname: this.lastname,
            affiliation: this.affiliation,
            author_url: this.authorUrl,
            doc_id: this.doc.id,
            title: this.doc.title,
            abstract: this.abstract,
            content: JSON.stringify(content),
            bibliography: JSON.stringify(bibDB),
            image_ids: Object.keys(imageDB)
        })
            .then(() => addAlert("success", gettext("Article submitted")))
            .catch(error => {
                addAlert("error", gettext("Article could not be submitted."))
                throw error
            })
    }
}
