# Docker and PostgreSQL: Data Engineering Workshop

* Video: TBD

In this workshop, we will explore Docker fundamentals and data engineering workflows using Docker containers. This workshop is an update for Module 1 of the [Data Engineering Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp).

**Data Engineering** is the design and development of systems for collecting, storing and analyzing data at scale.

We will cover:

- Introduction to Docker and containerization
- Running PostgreSQL in a Docker container
- Data ingestion into PostgreSQL
- Working with pgAdmin for database management
- Docker networking and port mapping
- Docker Compose for multi-container applications
- Creating a data ingestion pipeline
- SQL refresher with real-world data
- Best practices for containerized data engineering workflows

## Prerequisites

- Basic understanding of Python
- Basic SQL knowledge (helpful but not required)
- Docker and Python installed on your machine
- Git (optional)


## Introduction to Docker

Docker is a _containerization software_ that allows us to isolate software in a similar way to virtual machines but in a much leaner way.

A **Docker image** is a _snapshot_ of a container that we can define to run our software, or in this case our data pipelines. By exporting our Docker images to Cloud providers such as Amazon Web Services or Google Cloud Platform we can run our containers there.

**Why Docker?**

Docker provides the following advantages:

- Reproducibility: Same environment everywhere
- Isolation: Applications run independently
- Portability: Run anywhere Docker is installed

They are used in many situations: 

- Integration tests: CI/CD pipelines
- Running pipelines on the cloud: AWS Batch, Kubernetes jobs
- Spark: Analytics engine for large-scale data processing
- Serverless: AWS Lambda, Google Functions


**Basic Docker Commands**

Check Docker version:

```bash
docker --version
```

Run a simple container:

```bash
docker run hello-world
```

Run something more complex:

```bash
docker run ubuntu
```

Nothing happens. Need to run it in `-it` mode:

```bash
docker run -it ubuntu
```

We don't have `python` there so let's install it:

```bash
apt update && apt install python3
python3 -V
```


Important: Docker containers are stateless - any changes done inside a container will **NOT** be saved when the container is killed and started again.

When you exit the container and use it again, the changes are gone:

```bash
docker run -it ubuntu
python3 -V
```

This is good, because it doesn't affect your host system. Let's say you do something crazy like this:

```bash
docker run -it ubuntu
rm -rf / # don't run it on your computer! 
```

Next time we run it, all the files are back.

But, this is not _completely_ correct. The state is saved somewhere. We can see stopped containers:

```bash
docker ps -a
```

We can restart one of them, but we won't do it, because it's not a good practice. They take space, so let's delete them:

```bash
docker rm `docker ps -aq`
```

Next time we run something, we add `--rm`:

```bash
docker run -it --rm ubuntu
```

There are other base images besides `hello-world` and `ubuntu`. For example, Python:

```bash
docker run -it --rm python:3.13.10
# add -slim to get a smaller version
```

This one starts `python`. If we want bash, we need to overwrite `entrypoint`:

```bash
docker run -it \
    --rm \
    --entrypoint=bash \
    python:3.13.10-slim
```

So, we know that with docker we can restore any container to its initial state in a reproducible manner. But what about data? A common way to do so is with _volumes_.

Let's create some data in `test`:

```bash
TODO create random files in test/
``` 

TODO map this to python container 

TODO create a script in test that shows the files in this folder 



## Virtual environment, Dockerfile and Data Pipelines

A **data pipeline** is a service that receives data as input and outputs more data. For example, reading a CSV file, transforming the data somehow and storing it as a table in a PostgreSQL database.

Illustration: Data pipeline diagram

Let's create an example pipeline. We will create a dummy `pipeline.py` Python script that receives an argument and prints it.


```python
import sys
import pandas as pd 

# print arguments
print(sys.argv)

# argument 0 is the name of the file
# argument 1 contains the actual first argument we care about
day = sys.argv[1]

# cool pandas stuff goes here

# print a sentence with the argument
print(f'job finished successfully for day = {day}')
```

We need pandas, but we don't have it. We want to test it before we run things in a container. 

We can install it with `pip`:

```
pip install pandas
```

but it intalls it glbally. we want to use virtual environment.

TODO explain what it is . we'll use uv for that

```
pip install uv
```

now with 

uv init --python=3.13

Compare: 

uv run which python
uv run python -V

and 

which python
python -V

Now let's add pandas:

uv add pandas

now we can execute this file:

```
uv run python pipeline.py 10
```

We will see:

* `['pipeline.py', '10']`
* `job finished successfully for day = 10`

Let's containerize it by creating a Docker image. Create the following `Dockerfile` file:

```dockerfile
# base Docker image that we will build on
FROM python:3.13.10-slim

# set up our image by installing prerequisites; pandas in this case
RUN pip install pandas

# set up the working directory inside the container
WORKDIR /app
# copy the script to the container. 1st name is source file, 2nd is destination
COPY pipeline.py pipeline.py

# define what to do first when the container runs
# in this example, we will just run the script
ENTRYPOINT ["python", "pipeline.py"]
```

**Explanation:**

- `FROM`: Base image (Python 3.13)
- `RUN`: Execute commands during build
- `WORKDIR`: Set working directory
- `COPY`: Copy files into the image
- `ENTRYPOINT`: Default command to run

Let's build the image:

```bash
docker build -t test:pandas .
```

* The image name will be `test` and its tag will be `pandas`. If the tag isn't specified it will default to `latest`.

We can now run the container and pass an argument to it, so that our pipeline will receive it:

```bash
docker run -it test:pandas some_number
```

You should get the same output you did when you ran the pipeline script by itself.

> Note: these instructions assume that `pipeline.py` and `Dockerfile` are in the same directory. The Docker commands should also be run from the same directory as these files.

What about uv? Let's use it instead of using pip:

todo add comments to every line

```dockerfile
FROM python:3.13.10-slim

# TODO comment
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# TODO comment
ENV PATH="/app/.venv/bin:$PATH"

# TODO comment
COPY "pyproject.toml" "uv.lock" ".python-version" ./
RUN uv sync --locked

COPY pipeline.py pipeline.py

ENTRYPOINT ["python", "pipeline.py"]
```

## Running PostgreSQL with Docker


In later parts of the course we will use Airflow, which uses PostgreSQL internally. For simpler tests we can use PostgreSQL (or just Postgres) directly.

You can run a containerized version of Postgres that doesn't require any installation steps. You only need to provide a few _environment variables_ to it as well as a _volume_ for storing data.

Create a folder anywhere you'd like for Postgres to store data in. We will use the example folder `ny_taxi_postgres_data`. Here's how to run the container:


```bash
docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v ny_taxi_postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:13
```

TODO explain

alternative: 

create ny_taxi_postgres_data then map


```bash
docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v $(pwd)/ny_taxi_postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:13
```
explain why first create then map (its owned by the current user not docker/root)


Once the container is running, we can log into our database with [pgcli](https://www.pgcli.com/).

Install pgcli:

uv add --dev pgcli

todo explain --dev


Now use use it to connect to pg:

```bash
uv run pgcli -h localhost -p 5432 -u root -d ny_taxi
```

* `uv run` todo
* `-h` is the host. Since we're running locally we can use `localhost`.
* `-p` is the port.
* `-u` is the username.
* `-d` is the database name.
* The password is not provided; it will be requested after running the command.

When prompted, enter the password: `root`

Try some SQL commands:

```sql
-- List tables
\dt

-- Create a test table
CREATE TABLE test (id INTEGER, name VARCHAR(50));

-- Insert data
INSERT INTO test VALUES (1, 'Hello Docker');

-- Query data
SELECT * FROM test;

-- Exit
\q
```

## NY Taxi Dataset and Data Ingestion

We will now create a Jupyter Notebook `upload-data.ipynb` file which we will use to read a CSV file and export it to Postgres.

We will use data from the [NYC TLC Trip Record Data website](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

Specifically, we will use the [Yellow taxi trip records CSV file for January 2021](https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz).

This data used to be csv, but later they switched to parquet. We want to keep using CSV because we need to do a bit of extra pre-processing (for the purposes of learning it). 

A dictionary to understand each field is available [here](https://www1.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf).


> Note: The CSV data is stored as gzipped files. Pandas can read them directly.


**Explore the Data**

For that we will use Jupyter 

```
uv add --dev jupyter
```

Let's create a Jupyter notebook to explore the data:

```bash
uv run jupyter notebook
```

Create a new notebook and run:

```python
import pandas as pd

# Read a sample of the data
prefix = 'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/'
df = pd.read_csv(prefix + '/yellow_tripdata_2021-01.csv.gz', nrows=100)

# Display first rows
df.head()

# Check data types
df.dtypes

# Check data shape
df.shape
```


## Data Ingestion Script

TODO show the code for ingestion.

Then we convert it to python

uv run jupyter nbconvert --to=script notebook.ipynb
mv notebook.py ingest_data.py

The `ingest_data.py` script loads the NY Taxi data into PostgreSQL in chunks to handle large files efficiently.


Make sure PostgreSQL is running, then execute the ingestion script:

```bash
uv run python ingest_data.py \
  --user=root \
  --password=root \
  --host=localhost \
  --port=5432 \
  --db=ny_taxi \
  --table_name=yellow_taxi_trips \
  --url="https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"
```

This will download and ingest the data into your PostgreSQL database.

**Verify Data**

Connect with pgcli and query the data:

```bash
uv run pgcli -h localhost -p 5432 -u root -d ny_taxi
```

```sql
-- Count records (should return 1,369,765 rows)
SELECT COUNT(*) FROM yellow_taxi_trips;

-- View sample data
SELECT * FROM yellow_taxi_trips LIMIT 10;

-- Basic analytics
SELECT 
    DATE(tpep_pickup_datetime) AS pickup_date,
    COUNT(*) AS trips_count,
    AVG(total_amount) AS avg_amount
FROM yellow_taxi_trips
GROUP BY DATE(tpep_pickup_datetime)
ORDER BY pickup_date;
```

## pgAdmin - Database Management Tool

`pgcli` is a handy tool but it's cumbersome to use for complex queries and database management. [`pgAdmin` is a web-based tool](https://www.pgadmin.org/) that makes it more convenient to access and manage our databases. It's possible to run pgAdmin as a container along with the Postgres container, but both containers will have to be in the same _virtual network_ so that they can find each other.

**Run pgAdmin Container**

TODO: add volume mapping

```bash
docker run -it \
  -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" \
  -e PGADMIN_DEFAULT_PASSWORD="root" \
  -p 8080:80 \
  dpage/pgadmin4
```

* The container needs 2 environment variables: a login email and a password. We use `admin@admin.com` and `root` in this example.
* pgAdmin is a web app and its default port is 80; we map it to 8080 in our localhost to avoid any possible conflicts.
* The actual image name is `dpage/pgadmin4`.

**Note:** This won't work yet because pgAdmin can't see the PostgreSQL container. They need to be on the same Docker network!

**Docker Networks**

Let's create a virtual Docker network called `pg-network`:

```bash
docker network create pg-network
```

> You can remove the network later with the command `docker network rm pg-network`. You can look at the existing networks with `docker network ls`.

Stop both containers and re-run them with the network configuration:

```bash
# Run PostgreSQL on the network
docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v ny_taxi_postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  --network=pg-network \
  --name pgdatabase \
  postgres:13

# In another terminal, run pgAdmin on the same network
# todo add volume mapping
docker run -it \
  -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" \
  -e PGADMIN_DEFAULT_PASSWORD="root" \
  -p 8080:80 \
  --network=pg-network \
  --name pgadmin \
  dpage/pgadmin4
```

* Just like with the Postgres container, we specify a network and a name for pgAdmin.
* The container names (`pgdatabase` and `pgadmin`) allow the containers to find each other within the network.

**Connect pgAdmin to PostgreSQL**

You should now be able to load pgAdmin on a web browser by browsing to `http://localhost:8080`. Use the same email and password you used for running the container to log in.

1. Open browser and go to `http://localhost:8080`
2. Login with email: `admin@admin.com`, password: `root`
3. Right-click "Servers" → Register → Server
4. Configure:
   - **General tab**: Name: `Local Docker`
   - **Connection tab**:
     - Host: `pgdatabase` (the container name)
     - Port: `5432`
     - Username: `root`
     - Password: `root`
5. Save

Now you can explore the database using the pgAdmin interface!

We will explore using pgAdmin more in later sections.

## Dockerizing the Ingestion Script

Let's modify the Dockerfile we created before to include our `ingest_data.py` script:

TODO update it so it matches what we did earlier 

```dockerfile
FROM python:3.13

# psycopg2 is a postgres db adapter for python: sqlalchemy needs it
RUN pip install pandas sqlalchemy psycopg2

WORKDIR /app
COPY ingest_data.py ingest_data.py 

ENTRYPOINT [ "python", "ingest_data.py" ]
```

Explain it with comments

**Build the Docker Image**

```bash
docker build -t taxi_ingest:v001 .
```

**Run the Containerized Ingestion**

You can drop the table in pgAdmin beforehand if you want, but the script will automatically replace the pre-existing table.

```bash
docker run -it \
  --network=pg-network \
  taxi_ingest:v001 \
    --user=root \
    --password=root \
    --host=pgdatabase \
    --port=5432 \
    --db=ny_taxi \
    --table_name=yellow_taxi_trips \
    --url="https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"
```

**Important notes:**

* We need to provide the network for Docker to find the Postgres container. It goes before the name of the image.
* Since Postgres is running on a separate container, the host argument will have to point to the container name of Postgres (`pgdatabase`).
* You can drop the table in pgAdmin beforehand if you want, but the script will automatically replace the pre-existing table.

## Docker Compose

`docker-compose` allows us to launch multiple containers using a single configuration file, so that we don't have to run multiple complex `docker run` commands separately.

Docker compose makes use of YAML files. Here's the `docker-compose.yaml` file for running the Postgres and pgAdmin containers:

```yaml
services:
  pgdatabase:
    image: postgres:13
    environment:
      - POSTGRES_USER=root
      - POSTGRES_PASSWORD=root
      - POSTGRES_DB=ny_taxi
    volumes:
      - "ny_taxi_postgres_data:/var/lib/postgresql/data:rw"
    ports:
      - "5432:5432"
  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=root
    volumes:
      - "data_pgadmin:/var/lib/pgadmin"
    ports:
      - "8080:80"
```

* We don't have to specify a network because `docker-compose` takes care of it: every single container (or "service", as the file states) will run within the same network and will be able to find each other according to their names (`pgdatabase` and `pgadmin` in this example).
* All other details from the `docker run` commands (environment variables, volumes and ports) are mentioned accordingly in the file following YAML syntax.

**Start Services with Docker Compose**

We can now run Docker compose by running the following command from the same directory where `docker-compose.yaml` is found. Make sure that all previous containers aren't running anymore:

```bash
docker-compose up
```

>Note: this command assumes that the `ny_taxi_postgres_data` used for mounting the volume is in the same directory as `docker-compose.yaml`.

Since the settings for pgAdmin were stored within the container and we have killed the previous one, you will have to re-create the connection by following the steps in the pgAdmin section.

You will have to press `Ctrl+C` in order to shut down the containers. The proper way of shutting them down is with this command:

```bash
docker-compose down
```

And if you want to run the containers again in the background rather than in the foreground (thus freeing up your terminal), you can run them in detached mode:

```bash
docker-compose up -d
```

Other useful commands:

```bash
# View logs
docker-compose logs

# Stop and remove volumes
docker-compose down -v
```

**Benefits of Docker Compose:**

- Single command to start all services
- Automatic network creation
- Easy configuration management
- Declarative infrastructure

If you want to re-run the dockerized ingest script when you run Postgres and pgAdmin with `docker-compose`, you will have to find the name of the virtual network that Docker compose created for the containers. You can use the command `docker network ls` to find it and then change the `docker run` command for the dockerized script to include the network name.


--- 

Happy learning! 🐳📊
