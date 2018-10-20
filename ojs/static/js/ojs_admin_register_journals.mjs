import {AdminRegisterJournals} from "./modules/ojs/admin"

const theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
