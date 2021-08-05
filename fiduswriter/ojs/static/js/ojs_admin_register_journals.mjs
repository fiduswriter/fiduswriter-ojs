import {AdminRegisterJournals} from "./modules/ojs/admin.js"

const theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
