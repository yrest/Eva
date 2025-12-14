#!/bin/bash
export TASKS_WRITE_TOKEN="eva-write-2025"
export TASKS_READ_TOKEN="eva-read-2025"
export TASKS_ADMIN_TOKEN="eva-admin-2025"

cd /home/user/Eva/services/tasks
uvicorn src.main_simple:app --host 127.0.0.1 --port 8008
