#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 <image:tag>"
    exit 1
fi

set -e

IMAGE_TAG="$1"

get_mirror_tag() {
    local image="$1"

    case "$image" in
        enterprise-public-cn-beijing.cr.volces.com/*|ccr-2vdh3abv-pub.cnc.bj.baidubce.com/*|docker.m.daocloud.io/*|m.daocloud.io/*)
            echo ""
            return
            ;;
        ghcr.io/*|quay.io/*|gcr.io/*|registry.k8s.io/*|docker.io/*)
            echo "m.daocloud.io/$image"
            return
            ;;
    esac

    slash_count=$(printf '%s' "$image" | tr -cd '/' | wc -c | tr -d ' ')
    if [ "$slash_count" -eq 0 ]; then
        echo "m.daocloud.io/docker.io/library/$image"
    elif [ "$slash_count" -eq 1 ]; then
        echo "m.daocloud.io/docker.io/$image"
    else
        echo ""
    fi
}

pull_image() {
    local image="$1"
    echo "Pulling: $image"
    docker pull "$image"
}

echo "Preparing image: $IMAGE_TAG"

MIRROR_TAG=$(get_mirror_tag "$IMAGE_TAG")

if [ -n "$MIRROR_TAG" ]; then
    echo "Trying China mirror: $MIRROR_TAG"
    if pull_image "$MIRROR_TAG"; then
        if [ "$MIRROR_TAG" != "$IMAGE_TAG" ]; then
            docker tag "$MIRROR_TAG" "$IMAGE_TAG"
        fi
        echo "Successfully pulled via China mirror: $IMAGE_TAG"
        exit 0
    fi
    echo "China mirror failed, falling back to original image: $IMAGE_TAG"
else
    echo "Image is already from a China-friendly registry or unsupported mirror mapping. Pulling original tag."
fi

if pull_image "$IMAGE_TAG"; then
    echo "Successfully pulled original image: $IMAGE_TAG"
else
    echo "Failed to pull image from both mirror and original source: $IMAGE_TAG" >&2
    exit 1
fi
