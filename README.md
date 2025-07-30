# Efficient Mention Graph Storage

Efficient Mention Graph Storage
This project is a FastAPI application designed to process CSV files containing mention data (e.g., social media-style mentions like @username), extract relevant information, and store it in a PostgreSQL database using Celery for asynchronous task management. The system is built with scalability and high availability in mind, leveraging Redis for task queuing and PostgreSQL for persistent storage of nodes (users) and edges (mentions).

## Table of Contents

- Project Setup
- Endpoint Documentation
- Celery Tasks and Scalability
- High Availability of Redis and Celery
- Considerations for Scalability and Efficiency


## Project Setup
To get the project up and running locally, follow these steps:

### Prerequisites
- Git
- Docker and Docker Compose
- Python 3.9+

### Steps

- Clone the Repository:

        git clone https://github.com/mjmichael73/efficient-mention-graph-storage.git
        
        cd efficient-mention-graph-storage


- Set Up Environment Variables:

        Create a .env file in the backend directory:
            - DATABASE_URL=postgresql://postgres:password@mentions-graph-db:5432/mention_graph_db

            - BROKER_URL=sentinel://sentinel-1:26379;sentinel-2:26379;sentinel-3:26379/0?master_name=mymaster


- Build and Start Services:

        docker-compose up --build


- Access the Application: Once the services are running, the API is accessible at http://localhost.


- Verify Setup

        - Access Swagger Docs: http://localhost/doc
        - Upload a csv file to /upload_csv
        - Check the database




## How It Works:
The endpoint receives a CSV file via a POST request.
It reads the file, skipping the header row.
For each row, it extracts data (text with mentions), timestamp, and username.
The extracted data is collected into a list of dictionaries.
The list is passed to the sync_mentions_to_db Celery task for asynchronous processing.
The endpoint returns a response immediately with the number of rows processed, while database operations occur in the background.




## Celery Tasks and Scalability
### Tasks Overview
The project uses Celery to handle background tasks, ensuring the API remains responsive. Two main tasks are implemented:

### *sync/_mentions_to_db*

#### Purpose: 
Processes CSV data, extracts mentions (e.g., @username), and updates the database with nodes (users) and edges (mentions).

#### Process:
Extracts mentions from the data field using a regex pattern (@(\w+)).
Locks the nodes and edges tables in ACCESS EXCLUSIVE MODE to prevent race conditions.
Inserts unique usernames into the nodes table, ignoring duplicates.
Maps usernames to node IDs and creates/updates edges with weights in the edges table.
Commits changes in batches to optimize database performance.


#### Scalability Features:

    - Batch Processing: Processes data in chunks (default 10,000 edges per batch) to reduce database load.

    - Locking Mechanisms: Ensures data integrity during concurrent writes.

    - Conflict Handling: Uses on_conflict_do_nothing for nodes and on_conflict_do_update for edges to efficiently manage duplicates.

    - Retry Logic: Retries up to 3 times with exponential backoff on failure.




### *decrease_old_edge_weights*

#### Purpose: 
Periodically reduces the weight of edges not updated in the last 7 days.

#### Process:
    - Locks the edges table in ROW EXCLUSIVE MODE to allow reads while preventing write conflicts.
    - Updates edges in batches of 500, decreasing weights and updating timestamps.


#### Scalability Features:
    - Batch Updates: Limits database impact by processing small batches.
    - Scheduled Execution: Runs via Celery Beat (default every 30 seconds for testing; configurable to daily).





## Why Tasks Are Scalable

    - Asynchronous Execution: Offloading tasks to Celery workers keeps the API responsive under load.

    - Horizontal Scaling: Add more Celery workers (e.g., docker-compose scale celery=4) to handle increased task volumes.

    - Database Optimization: Batch inserts/updates and conflict handling minimize round-trips and deadlocks.

    - Concurrency Management: Locking strategies balance integrity and performance, allowing reads during updates where possible.


## High Availability of Redis and Celery

### Redis Setup

    - Master-Slave Replication: One Redis master and three slaves replicate data for durability and availability.

    - Sentinels: Three Redis Sentinels monitor the Redis cluster, detecting failures and promoting a slave to master if needed.

    - Configuration: Celery connects to Sentinels via BROKER_URL, ensuring it always uses the current master.

### Celery Configuration

    - Broker and Backend: Uses the Redis Sentinel setup for both task queuing and result storage.

    - Task Routing: Tasks are routed to the mentions queue, enabling dedicated worker pools.

    - Periodic Tasks: Celery Beat schedules tasks like decrease_old_edge_weights reliably.

### Why This Setup Is Highly Available

    - Failover: Sentinels automatically handle Redis master failures, ensuring Celery tasks continue uninterrupted.

    - Load Distribution: Slaves can handle read operations, reducing master load.

    - Resilience: Multiple Sentinels provide fault-tolerant monitoring.


## Improvements (TODO)

### Database Sharding: 
Spliting the database across multiple instances for large datasets.

### Caching: 
Using Redis to cache frequently accessed nodes/edges, reducing database queries.

### Query Optimization: 
Adding indexes on frequently queried fields (e.g., edges.last_updated) and review query performance.

### Task Prioritization: 
Implementing Celery task priorities to process urgent tasks first.

### Monitoring: 
Adding tools like Prometheus and Grafana to monitor Celery, Redis, and PostgreSQL health.

### Load Balancing: 
Deploying multiple FastAPI instances behind a load balancer (e.g., additional Nginx instances).

### Asynchronous DB Access: 
Using an async PostgreSQL driver (e.g., asyncpg) with FastAPI for better concurrency.

### Data Archiving: 
Archiving old edges/nodes to a separate table or database to keep the active dataset lean.

### Redis Streams: 
Replacing Redis lists with Streams for more efficient task queuing.