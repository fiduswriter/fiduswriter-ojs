import {AdminRegisterJournals} from "./modules/ojs"

const theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
