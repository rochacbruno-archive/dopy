# help
uv run dolist --help
# actions
uv run dolist --actions
# list all actions

# Add a new task
uv run dolist add "Testar a bagaça"

# list all tasks
uv run dolist ls --all
uv run dolist ls --status done

# list/export all in JSON
uv run dolist ls --json
uv run dolist ls --status new --json  # also with any of the ls filters


# list all tasks with a search term
uv run dolist ls --all --search task

# must implement this next command
ID=$(uv run dolist ls --search baga --json | jq ".[0].id")
# assuming id is 10 for now

uv run dolist $ID show
uv run dolist $ID remind 3 hours  # must work unquoted
uv run dolist $ID remind "3 hours"  # and also quoted
uv run dolist $ID delay 1 min
uv run dolist $ID start
uv run dolist $ID note amazing text to add as note # must work unquoted
uv run dolist $ID note "another amazing text to add as note"  # and also quoted
uv run dolist $ID note --rm 1  # delete first note

# new commands to be implemented

# Bulk action on all items from a search
# delete all done tasks
uv run dolist ls --status done --action delete -y

# add a reminder on all tasks having batata in the title
uv run dolist ls --search baga --action remind --action-args "3 hours" -y

# post pone all tasks having food tag
uv run dolist ls --tag food --all --action post -y

# `--action` must accept all actions that `dolist {id} [action]` takes


