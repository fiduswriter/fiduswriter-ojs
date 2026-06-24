import {initSettings} from "fwtoolkit/settings"
import {AdminRegisterJournals} from "./modules/ojs/admin.js"

initSettings(window.settings)
const theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
