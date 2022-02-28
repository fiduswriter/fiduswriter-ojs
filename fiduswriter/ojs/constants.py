ROLE_ID_SITE_ADMIN = 1
ROLE_ID_MANAGER = 16
ROLE_ID_SUB_EDITOR = 17
ROLE_ID_ASSISTANT = 4097
EDITOR_ROLES = {1: "editor", 16: "editor", 17: "subeditor", 4097: "assistant"}
EDITOR_ROLE_STAGE_RIGHTS = {
    1: {1: "write", 3: "write", 4: "write", 5: "write"},
    16: {1: "write", 3: "write", 4: "write", 5: "write"},
    17: {1: "write", 3: "write", 4: "write", 5: "write"},
    4097: {1: "comment", 3: "comment", 4: "write-tracked", 5: "comment"},
}
