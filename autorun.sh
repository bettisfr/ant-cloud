#!/bin/bash

# Activate virtual environment
source antenv/bin/activate

# Move into the project
cd ant-cloud || exit

echo "Starting Ant Cloud servers..."

# Start servers in background
python3 server-picture.py &
PID1=$!

python3 server-labeler.py &
PID2=$!

echo "server-picture.py PID: $PID1"
echo "server-labeler.py PID: $PID2"

# Keep script alive so children do not die
wait
