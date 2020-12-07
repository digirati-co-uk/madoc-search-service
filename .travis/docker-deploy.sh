#!/usr/bin/env bash

set -e;

if [[ -z "$1" ]]; then
  echo -e "You must pass in a docker image tag to build"
fi;

if [[ -z "$TRAVIS_BRANCH" ]]; then
    echo -e "\033[00;32m This should only be run from Travis";
    exit 1;
fi;

if [[ -z "$DOCKER_USERNAME" ]]; then
    echo -e "\033[00;32m Missing Docker username in env (DOCKER_USERNAME)";
    exit 1;
fi;

if [[ -z "$DOCKER_PASSWORD" ]]; then
    echo -e "\033[00;32m Missing Docker password in env (DOCKER_PASSWORD)";
    exit 1;
fi;

# Read first arg as the repo. (e.g. digirati/madoc-platform)
REPO_NAME="$1"

if [[ "$(docker images -q ${REPO_NAME}:latest 2> /dev/null)" == "" ]]; then
  echo -e "\033[00;32m Image was NOT built, failing the build";
  exit 1
fi;

# Login to Docker hub.
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin

# Create short commit hash for tagging.
COMMIT_HASH="$(git rev-parse --short ${TRAVIS_COMMIT})"

# Tag..
docker tag ${REPO_NAME} ${REPO_NAME}:${COMMIT_HASH}
docker tag ${REPO_NAME} ${REPO_NAME}:${TRAVIS_BRANCH}

# ..and push
docker push ${REPO_NAME}:${COMMIT_HASH}
docker push ${REPO_NAME}:${TRAVIS_BRANCH}

# Only tag latest on master.
if [[ "$TRAVIS_BRANCH" = "master" ]] && [[ "$TRAVIS_PULL_REQUEST" = "false" ]]; then
    docker tag ${REPO_NAME} ${REPO_NAME}:latest
    docker push ${REPO_NAME}:latest
fi;
