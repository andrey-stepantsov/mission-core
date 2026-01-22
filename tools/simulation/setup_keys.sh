#!/bin/bash
set -e
echo "Generating key..."
docker exec -u neo mission-client bash -c "[ -f /home/neo/.ssh/id_rsa ] || ssh-keygen -t rsa -N '' -f /home/neo/.ssh/id_rsa"
# Configure SSH to ignore host keys for simulation
docker exec -u neo mission-client bash -c "echo 'Host *' > /home/neo/.ssh/config && echo '    StrictHostKeyChecking no' >> /home/neo/.ssh/config && echo '    UserKnownHostsFile /dev/null' >> /home/neo/.ssh/config && chmod 600 /home/neo/.ssh/config"
PUBKEY=$(docker exec -u neo mission-client cat /home/neo/.ssh/id_rsa.pub)
echo "Key: $PUBKEY"
echo "Pushing to host..."
docker exec mission-host bash -c "mkdir -p /home/oracle/.ssh && echo '$PUBKEY' >> /home/oracle/.ssh/authorized_keys && chown oracle:oracle /home/oracle/.ssh/authorized_keys"
echo "Creating test file..."
docker exec -u oracle mission-host bash -c "echo 'Hello World' > /home/oracle/test_file.txt"
echo "Done."
