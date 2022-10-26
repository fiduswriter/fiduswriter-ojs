import {Plugin, PluginKey} from "prosemirror-state"
import {DOMSerializer} from "prosemirror-model"

const key = new PluginKey("reviewContributorInput")


class ReviewContributorsPartView {
    constructor(node, view, getPos, contributors) {
        this.node = node
        this.view = view
        this.getPos = getPos
        this.dom = document.createElement("div")
        this.dom.classList.add("article-part")
        this.dom.classList.add(`article-${this.node.type.name}`)
        this.dom.classList.add(`article-${this.node.attrs.id}`)
        this.dom.classList.add(`article-${this.node.attrs.id}-readonly`)
        this.dom.contentEditable = false
        if (node.attrs.hidden || node.attrs.deleted || !contributors || !contributors.length) {
            this.dom.dataset.hidden = true
        } else {
            // Put contributors content back into place in the display if they are available.
            // This allows us to display the contributors to those who should see them and
            // not to reviewers.
            const schema = this.node.type.schema
            const serializer = DOMSerializer.fromSchema(schema)
            contributors.forEach(
                json => this.dom.append(serializer.serializeNode(schema.nodeFromJSON(json)))
            )
        }
        this.contentDOM = document.createElement("span")
        this.contentDOM.classList.add("contributors-inner")
        this.contentDOM.style.display = "none"
        this.dom.appendChild(this.contentDOM)
    }
}

export const reviewContributorPlugin = function(options) {

    return new Plugin({
        key,
        props: {
            nodeViews: {
                contributors_part: (node, view, getPos) => new ReviewContributorsPartView(node, view, getPos, options.contributors[node.attrs.id])
            }
        }
    })
}
