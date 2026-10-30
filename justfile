check:
    /bin/bash -n install.sh
    zsh -n zsh/.zshrc zsh/.zprofile zsh/aliases.zsh
    python3 -B -m unittest discover -s codex -p 'test_*.py'
    python3 -B codex/check.py
