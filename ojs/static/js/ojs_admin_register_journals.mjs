import {AdminRegisterJournals} from "./modules/ojs"

let theJournalRegister = new AdminRegisterJournals()

theJournalRegister.init()

window.theJournalRegister = theJournalRegister
