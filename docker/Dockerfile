# Base image for aarch64 architecture
FROM ubuntu:22.04

# Set environment variables
ENV AIRFLOW_HOME=/usr/local/airflow \
    PYTHON_VERSION=3.9 \
    AIRFLOW_VERSION=2.6.1 \
    AIRFLOW_USER=airflow

# Install necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    iproute2 \
    libssl-dev \
    libffi-dev \
    libmysqlclient-dev \
    libpq-dev \
    python3-dev \
    python3-pip \
    python3-setuptools \
    sudo \
    pkg-config \
    rsync \
    iputils-ping \
    default-libmysqlclient-dev \
    wireless-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Apache Airflow and Python dependencies
RUN pip3 install --upgrade pip setuptools wheel \
    && pip3 install apache-airflow==${AIRFLOW_VERSION} \
    && pip3 install apache-airflow[postgres,mysql,celery,redis] 

# Fix Cython and PyYAML issue
RUN pip3 install "cython<3.0.0" wheel --root-user-action=ignore \
    && pip3 install pyyaml==5.4.1 --no-build-isolation

# Create a new directory where the requirements file will be copied
WORKDIR /lib
COPY requirements.txt /lib/requirements.txt

# Install other requirements
RUN pip3 install --use-deprecated=legacy-resolver -r /lib/requirements.txt
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo "UTC" > /etc/timezone

# Postgres environment variables
ENV POSTGRES_DB=robot_db \
    POSTGRES_USER=robot_user \
    POSTGRES_PASSWORD=robot_pass \
    POSTGRES_HOST=localhost

# Install PostgreSQL and its dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-contrib \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Initialize PostgreSQL by starting the service and creating the user, DB
RUN service postgresql start && \
    su - postgres -c "psql --command \"CREATE USER ${POSTGRES_USER} WITH SUPERUSER PASSWORD '${POSTGRES_PASSWORD}';\"" && \
    su - postgres -c "createdb -O ${POSTGRES_USER} ${POSTGRES_DB}"

# Expose necessary ports
EXPOSE 8080 5432

# Add a script to start PostgreSQL and Airflow
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use the custom entrypoint script to start services
ENTRYPOINT ["/entrypoint.sh"]