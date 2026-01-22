import argparse
import sys
from .commands.init import do_init
from .commands.sync import do_pull, do_push, do_retract
from .commands.build import do_build, do_log, do_listen, do_live, do_context, do_focus
from .commands.run import do_run
from .commands.misc import do_grep, do_repair_headers

def main():
    parser = argparse.ArgumentParser(description="Projector Agent: Manage Remote Brain Hologram")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Init
    p_init = subparsers.add_parser("init", help="Initialize hologram")
    p_init.add_argument("host_target", help="SSH target (user@host)")
    p_init.add_argument("--remote-root", help="Absolute path to remote repository root", default=".")
    p_init.add_argument("--transport", help="Transport mode (ssh or local)", default="ssh")
    p_init.add_argument("--remote-mission-root", help="Absolute path to remote .mission directory (if outside repo)", default=None)
    p_init.set_defaults(func=do_init)
    
    # Pull
    p_pull = subparsers.add_parser("pull", help="Pull file from host")
    p_pull.add_argument("file", help="Remote absolute file path")
    p_pull.add_argument("--flags", help="Flags to filter compilation context (e.g. \"-DTEST\")")
    p_pull.set_defaults(func=do_pull)
    
    # Push
    p_push = subparsers.add_parser("push", help="Push file to host")
    p_push.add_argument("file", help="Local file path")
    p_push.add_argument("--trigger", action="store_true", help="Trigger remote build after push")
    p_push.set_defaults(func=do_push)
    
    # Retract
    p_retract = subparsers.add_parser("retract", help="Stop projecting a file (remove locally)")
    p_retract.add_argument("file", nargs="?", help="Local file path")
    p_retract.add_argument("--all", action="store_true", help="Retract ALL files from hologram")
    p_retract.set_defaults(func=do_retract)

    # Grep
    p_grep = subparsers.add_parser("grep", help="Run ripgrep on remote and map to hologram")
    p_grep.add_argument("pattern", help="Search pattern")
    p_grep.add_argument("path", nargs="?", help="Search path (optional)")
    p_grep.set_defaults(func=do_grep)
    
    # Listen
    p_listen = subparsers.add_parser("listen", help="Listen to remote broadcast")
    p_listen.add_argument("--mirror-log", help="Path to mirror raw log file locally")
    p_listen.set_defaults(func=do_listen)
    
    # Log (Atomic)
    p_log = subparsers.add_parser("log", help="Fetch remote build log (One-shot)")
    p_log.add_argument("-n", "--lines", type=int, help="Number of lines to tail")
    p_log.set_defaults(func=do_log)
    
    # Build
    p_build = subparsers.add_parser("build", help="Trigger remote build manually")
    p_build.add_argument("--context-from", help="Derive build context from this file path")
    p_build.add_argument("--sync", help="Synchronize specific file before building")
    p_build.add_argument("--wait", action="store_true", help="Wait for build completion and stream logs")
    p_build.set_defaults(func=do_build)
    
    # Live
    p_live = subparsers.add_parser("live", help="Live mode (Watch + Push + Listen)")
    p_live.add_argument("--auto-build", action="store_true", help="Enable automatic build triggering on file changes")
    p_live.set_defaults(func=do_live)

    # Focus (Clangd)
    p_focus = subparsers.add_parser("focus", help="Generate .clangd config from a source file")
    p_focus.add_argument("file", help="Source file (C/C++) to derive flags from")
    p_focus.set_defaults(func=do_focus)
    
    # Context (AI)
    p_context = subparsers.add_parser("context", help="Show AI-friendly compilation context")
    p_context.add_argument("file", nargs="?", help="Local file path")
    p_context.add_argument("task", nargs="?", help="Optional task description for the AI agent")
    p_context.set_defaults(func=do_context)

    # Run
    p_run = subparsers.add_parser("run", help="Run command on remote host in project context")
    p_run.add_argument("command", nargs="+", help="Command to run")
    p_run.set_defaults(func=do_run)

    # Repair Headers
    p_repair = subparsers.add_parser("repair-headers", help="Sync missing system headers")
    p_repair.set_defaults(func=do_repair_headers)
    
    # Pre-process sys.argv to handle --flags "-D..." issue
    argv_clean = []
    i = 0
    raw_args = sys.argv[1:]
    while i < len(raw_args):
        arg = raw_args[i]
        if arg == "--flags" and i + 1 < len(raw_args):
            val = raw_args[i+1]
            if val.startswith("-"):
                argv_clean.append(f"--flags={val}")
                i += 2
                continue
        argv_clean.append(arg)
        i += 1

    args = parser.parse_args(argv_clean)
    args.func(args)

if __name__ == "__main__":
    main()
