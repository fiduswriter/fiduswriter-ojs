import {initSettings} from "fwtoolkit/settings.js"
import {AdminRegisterJournals} from "./modules/ojs/admin.js"

initSettings(window.settings)
const theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
