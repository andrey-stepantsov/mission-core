# Parasitic Mode

In this mode, the **Builder** runs on your Host machine (Mac/Linux), not in Docker. 
Aider remains in a container but "remote controls" your local shell via the daemon.

## Architecture

1. **The Host:** Runs `dd-daemon`. Watches files.
2. **The Host:** Executes `make` directly (using local clang/gcc).
3. **The Container:** Runs Aider. Mounts source. Reads `.build.log`.

## Setup

1. **Install:** Ensure the mission pack is installed.
   ```bash
   ./.mission/tools/bin/install_ddd.sh
   ```

2. **Configure:** Create a `.ddd/config.json` in your project root:
   ```json
   {
     "targets": {
       "dev": {
         "build": {
           "cmd": "make -j4",
           "filter": ["gcc_make", "gcc_json"],
           "path_strip": "$(pwd)/"
         },
         "verify": {
           "cmd": "./tests/run_tests.sh",
           "filter": "raw"
         }
       }
     }
   }
   ```

3. **Run Daemon:** Start the watcher on your host:
   ```bash
   dd-daemon
   ```

4. **Launch Aider:** Start the coder as usual. It will detect `.ddd` and automatically use it for builds.
   ```bash
   ./.mission/coder
   ```
