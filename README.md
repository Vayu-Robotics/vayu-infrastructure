# vayu-infrastructure
- Vayu infrastructural services. 

# Instructions to setup the image
1. We use docker buildx to build the image locally for the target platform
    ```docker buildx build --platform linux/arm64 -t vayurobotics/vayu-infrastructure --load .```
    Change platform to amd64 for x86 platform.
2. We need to set the right permissions for postgres to persist the database.
```sudo chown -R 999:999 ./pgdata```
3. Bring up: ```docker-compose up```


# Instructions for accessing the database
1. Bash into a live vayu-infrastructure container.
2. Login to the databse : ```psql -h localhost -U robot_user -d robot_db```
3. Enter the password: ```robot_pass```
4. Run your queries when you are inside the psql shell.

# Sample Queries
- List all tables: ``\dt``
- Select entries at time of interest: ``SELECT * FROM your_table WHERE start_time BETWEEN '2024-09-01 00:00:00' AND '2024-09-01 23:59:59';``

