---
name: Build and Push a Docker Image
slug: docker-build-push
trigger: docker, build, image, registry, push
category: devops
quality: 0.84
author: argo-team
license: MIT
requires_tools: [docker, shell]
---

# Build and Push a Docker Image

1. Verify a `Dockerfile` exists in the build context; read it for the base image.
2. Choose a tag: `<registry>/<repo>:<git-short-sha>` plus `:latest` if on main.
3. Build with `docker build --pull -t <tag> .` and capture the image size.
4. Run a quick smoke test: `docker run --rm <tag> <healthcheck-cmd>`.
5. Authenticate to the registry, then `docker push` every tag.
6. Report the pushed digest and image size; warn if the image exceeds 500 MB.
