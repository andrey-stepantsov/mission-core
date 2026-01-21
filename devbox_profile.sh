# Devbox Bash Profile
# Sourced when entering the devbox shell via init_hook

# 1. Load Standard Config (try to preserve user's generic settings)
if [ -f /etc/bashrc ]; then source /etc/bashrc; fi
if [ -f ~/.bashrc ]; then source ~/.bashrc; fi

# 2. Mission Configuration
export PATH=$PWD/.mission/tools/bin:$PATH
if [ -f .mission/.env ]; then source .mission/.env; fi

# 3. Python Environment
if [ ! -d .venv ]; then
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install pytest
else
  source .venv/bin/activate
fi

# 4. Aliases
alias projector="projector" # Ensures precedence over potential file paths
alias p="projector"         # Short alias

# 5. Prompt/Welcome
echo "👻 Chaos Remote Brain Environment (Bash)"
PS1="(.venv) (devbox) \u@\h \W $ "
