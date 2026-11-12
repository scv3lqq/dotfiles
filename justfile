check:
    /bin/bash -n install.sh
    zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh
    python3 -B codex/run_tests.py
    python3 -B -m unittest claude.hooks.tests.test_notify_fields claude.hooks.tests.test_runner_tmux_isolation claude.hooks.tests.test_launch_fixture_isolation claude.hooks.tests.test_fixture_code_cache claude.hooks.tests.test_inbox_ps_protocol
    python3 -B codex/check.py
    python3 -B -m unittest discover -s claude/skills/feature -p 'test_plan_edits.py'

# Quick feedback only; `just check` remains the full required gate.
check-fast:
    /bin/bash -n install.sh
    zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh
    /bin/bash -n claude/hooks/notify.sh
    /bin/bash -n tmux/agent-inbox.sh
    python3 -B codex/check.py
    python3 -B -m unittest discover -s claude/skills/feature -p 'test_plan_edits.py'
