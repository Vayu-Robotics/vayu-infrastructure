#!/bin/bash

cp robot_upload_sync.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable robot_upload_sync.service
systemctl start robot_upload_sync.service
