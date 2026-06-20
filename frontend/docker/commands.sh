#!/bin/bash

set -o errexit
set -o nounset

# Use standalone server for optimal performance (output from next.config.ts)
# This includes only the minimal dependencies needed for production
node server.js
