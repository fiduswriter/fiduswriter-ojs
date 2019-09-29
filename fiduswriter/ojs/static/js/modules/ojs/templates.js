import {escapeText} from "../common"

/** Dialog to add a note to a revision before saving. */

export const firstSubmissionDialogTemplate = ({journals, first_name, last_name, affiliation, abstract}) =>
    `<h3>${gettext('Submission information')}</h3>
    <table class="fw-dialog-table fw-dialog-table-wide">
        <tbody>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('Journal')} *</h4></th>
                <td class="entry-field">
                    <div class="fw-select-container">
                        <select id="submission-journal" class="fw-button fw-white fw-large">
                        ${
                            journals.map(journal =>
                                `<option value="${journal.id}">
                                    ${escapeText(journal.name)}
                                </option>`
                            ).join('')
                        }
                        </select>
                        <div class="fw-select-arrow fa fa-caret-down"></div>
                    </div>
                </td>
            </tr>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('Abstract')} *</h4></th>
                <td class="entry-field">
                    <textarea id="submission-abstract" rows="8" style="width:678px;resize:none;">${escapeText(abstract)}</textarea>
                </td>
            </tr>
        </tbody>
    </table>
    <h3>${gettext('Corresponding author')}</h3>
    <table class="fw-dialog-table fw-dialog-table-wide">
        <tbody>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('First name')} *</h4></th>
                <td class="entry-field">
                    <input type="text" id="submission-firstname" value="${escapeText(first_name)}">
                </td>
            </tr>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('Last name')} *</h4></th>
                <td class="entry-field">
                    <input type="text" id="submission-lastname" value="${escapeText(last_name)}"></td>
            </tr>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('Affiliation')}</h4></th>
                <td class="entry-field"><input type="text" id="submission-affiliation" value="${escapeText(affiliation)}"></td>
            </tr>
            <tr>
                <th><h4 class="fw-tablerow-title">${gettext('Webpage')}</h4></th>
                <td class="entry-field"><input type="text" id="submission-author-url"></td>
            </tr>
        </tbody>
    </table>`


export const resubmissionDialogTemplate = () =>
    `<p>${gettext('By pressing the submit button your resubmission will be sent to the journal')}</p><br>
    <p><b>${gettext('Be aware that this action cannot be undone!')}</b></p>`


export const reviewSubmitDialogTemplate = () =>
    `<label for="editor">${gettext('Message for editor')}:</label>
    <p><textarea  id="message-editor" name="message-editor" class="message-reviewer" ></textarea></p><br>
    <label for="editor-author">${gettext('Message for editor and authors')}:</label>
    <p><textarea  id="message-editor-author" class="message-reviewer" ></textarea></p><br>
    <label for="recommendation">${gettext('Recommendation')}:</label>
    <p><select id="recommendation" class="fw-button fw-white fw-large" name="recommendation">
		<option label="${gettext('Choose One')}" value="">${gettext('Choose One')}</option>
        <option label="${gettext('Accept Submission')}" value="1">${gettext('Accept Submission')}</option>
        <option label="${gettext('Revisions Required')}" value="2">${gettext('Revisions Required')}</option>
        <option label="${gettext('Resubmit for Review')}" value="3">${gettext('Resubmit for Review')}</option>
        <option label="${gettext('Resubmit Elsewhere')}" value="4">${gettext('Resubmit Elsewhere')}</option>
        <option label="${gettext('Decline Submission')}" value="5">${gettext('Decline Submission')}</option>
        <option label="${gettext('See Comments')}" value="6">${gettext('See Comments')}</option>
    </select></p><br>
    <p><strong>${gettext('Be aware that this action cannot be undone!')}</strong></p>`
