#!/usr/bin/env bash

ssh -o StrictHostKeyChecking=no $1 'sudo shutdown -hP now'
