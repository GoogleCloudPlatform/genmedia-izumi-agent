#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# By default, this script will build and run the application in the 'dev' environment.
# This is because the Dockerfile sets the default value of APP_ENV to 'dev'.
docker build -f deployment/Dockerfile --build-arg APP_ENV=dev -t izumi-backend:dev .

# Check if the build command was successful
if [ $? -ne 0 ]; then
  echo "Docker build failed. Exiting."
  exit 1
fi

# Mount gcloud config to get access to application default credentials.
docker run -p 8080:8080 -e PORT=8080 -v ~/.config/gcloud:/home/myuser/.config/gcloud izumi-backend:dev

# Stop any docker running with the image above with this command.
# docker stop $(docker ps -aq --filter ancestor=izumi-backend:dev)

# Install Docker on MacOS with Lima
# brew install colima
# colima start
