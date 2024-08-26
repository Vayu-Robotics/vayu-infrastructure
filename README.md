# vayu-infrastructure
- Vayu infrastructural services. 

# Instructions to build the image
1. We use docker buildx to build the image locally for the target platform
    ```docker buildx build --platform linux/arm64 -t vayurobotics/vayu-infrastructure --load .```
    Change platform to amd64 for x86 platform.
