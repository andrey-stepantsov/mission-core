#!/bin/bash
set -e
echo "Generating key..."
docker exec -u client mission-client bash -c "[ -f /home/client/.ssh/id_rsa ] || ssh-keygen -t rsa -N '' -f /home/client/.ssh/id_rsa"
PUBKEY=$(docker exec -u client mission-client cat /home/client/.ssh/id_rsa.pub)
echo "Key: $PUBKEY"
echo "Pushing to host..."
docker exec mission-host bash -c "mkdir -p /home/mission/.ssh && echo '$PUBKEY' >> /home/mission/.ssh/authorized_keys && chown mission:mission /home/mission/.ssh/authorized_keys"
echo "Creating test file..."
docker exec -u mission mission-host bash -c "echo 'Hello World' > /home/mission/test_file.txt"
echo "Done."
