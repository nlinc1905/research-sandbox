# Notes from Learning About GCP

There are 3 ways to deploy applications in GCP, which will be described in the following sections:
1. Serverless
2. Server
3. Container

These notes use the code from: [https://github.com/siddd88/udemy-gcp-serverless-architecture](https://github.com/siddd88/udemy-gcp-serverless-architecture)

GCP has several CLI tools:
* gcloud - for basic GCP interaction
* gsutil - for cloud storage buckets
* bq - for big query
* kubectl - for K8s (note that gcloud manages the K8s cluster but kubectl handles the pods)

## Architecture Considerations

Architects should build for:
* Resiliency - ability to tolerate faults in the system
* Availability - be ready to service requests all the time
* Scalability - can handle increasing and decreasing loads with ease
* Performance - responds quickly
* Security - security
* Cost - as cheap as possible

If you want disaster recovery, you should think about multi-regional applications.

## Serverless Applications

Serverless applications still use a server, but the server is abstracted away so that you don't have to worry about 
configuring or scaling it.  You can think of a serverless application as a service with on demand scaling.  When a 
serverless application is not being used, there is no cost, as the servers are ephemeral.

With serverless, you only need to worry about the code for your app, not the infrastructure (resiliency, availability, 
scalability, etc.) because they are managed for you by the cloud provider.  

### Serverless Options in GCP

Data Processing
* Cloud Run
* App Engine
* Dataproc Serverless
* Cloud Functions
* Cloud Composer/Airflow
Data Warehouse
* Bigquery
* Hive
Machine Learning
* VertexAI
* Bigquery ML
RDBMS
* cloudSQL - MySQL, Postgres

## Server Hosted Applications

Traditional applications hosted on a server that you configure.  You must handle configuration and scaling.  Even when 
demand is low, the server is always available.  This means there is a cost to keeping the server up all the time.  

### Server Options in GCP

Data Processing
* Dataproc - Hadoop cluster on GCP that you can spin up and specify the number of nodes
* Compute Engine
* Cloud Composer/Airflow - Can run Airflow by spinning up a cluster with a specified number of nodes
Machine Learning
* Vertex AI

## Containers

A containerized application is an application running in a container, and that container needs a pod or server to run 
on.  In Kubernetes, each pod usually has 1 container running on it.  Communication between containers requires a 
container orchestration service, like Kubernetes.  

Containerized applications are designed for serverless deployments. 

Container Security Best Practices
* Use native logging
* Do not run privileged containers - containers should not be able to access info about the machine they run on
* Containers should be stateless and immutable during runtime - use persistent volumes for state
* Containers should be easy to monitor - /metrics endpoint for Prometheus or use a sidecar container to read and translate logs into format that Prometheus can understand

### Container Hosting Options in GCP

Data Processing
* Cloud Run
* App Engine
* Docker - Artifact & container registry that supports hosting Docker images
Container Orchestration
* GKE (Kubernetes Engine)

## Monolithic vs Micro-Service Architectures

### Monolithic

The entire application is a single unit, with many modules.  For example, each Django application (pages, users, etc.) 
is a module within the larger application.  In this type of setup, modules can directly impact each other.  

Benefits
* Faster to develop initial prototype
Drawbacks
* Hard to scale - must scale entire app for higher use of 1 module
* High infrastructure cost
* Maintenance requires changes across many modules

### Micro-Service

The application is split into many services that can scale independently.

Benefits
* Easier to scale and maintain
* Can use a different tech stack per micro-service
* Feature releases require updating only 1 micro-service
* Dev teams can split between services & specialize

The challenge with moving to micro-service architectures at the enterprise level is that your dev teams deploy in 
different languages, frameworks, etc.  One way to manage things to ensure all dev teams deploy the same way is to use 
containerization.  

#### Communication Between Micro-Services

One option is to use http endpoints and communicate with REST API calls.  This can be synchronous or asynchronous.  

##### Synchronous

In synchronous communication, each service waits for a response before continuing to process a request.  An example of 
when this causes problems is when you have a logging service for your app, and it goes down, causing the app to go down 
with it.  

<em>Decoupling</em> refers to splitting your service up into parts that communicate asynchronously, using a message 
broker.  Decoupling is good when you have a service that depends on another, but the dependent service cannot keep up 
with the service that is sending it data.  As an example, consider a customer checkout process.  The process starts 
when the oder service publishes an OrderReceived message to a message broker topic.  The billing service receives the 
message and publishes an OrderBilled event, which the warehouse service receives and publishes an OrderReadyToShip 
event, which the shipping service receives and publishes an OderShipped event, which the emails service receives and 
sends an email to the customer.  The point is that 1 process can involve several de-coupled services <- this is event 
driven architecture.  

##### Asynchronous

In asynchronous communication, each service can process a request without waiting for responses from other components. 
This can be useful when you have a DB call that takes a while to return, and you do not want to hold up downstream 
processes.  If the downstream processes depend on the result of the DB call, then you have no choice but to wait, but 
if they do not, an async call can make the application run faster.  

De-coupling services using an event driven micro-service architecture involves the use of a message broker to make 
communication asynchronous.  It is important to remember that the main benefits are resiliency and availability of each 
service to continue processing requests (async).  Async apps are not necessarily faster, in fact, adding a message 
broker usually increases overall latency.  It also adds complexity to your architecture.  So async, decoupled services 
with a message broker is not the solution to every problem.  There are other ways to achieve resiliency and availability.

An example of async communication is using a message broker, like Kafka or Pub-Sub.  The message broker subscribes to 
services that you need responses from and listens for whenever the response comes in.  

It is important for every service to have its own subscription to a publisher stream (topic).  If many services share a 
subscription, the messages will be split between them.  Only when each service has its own subscription will they 
receive all messages from the topic.  Message brokers like pub-sub retain messages until a verification has been 
received from each subscriber, that the message was received.  Messages can be pushed to subscribers, or the subscribers 
can pull messages periodically.  

Sometimes you might need messages to process only once.  You can add Dataflow to pub-sub to ensure de-duplication of 
messages.  You can also order messages, but you can do this without adding Dataflow, when you create a topic.  Dataflow 
can move messages from pub-sub to splunk, BigQuery, and other places: it is a managed ETL tool for stream and batch 
processing, and 1 of its functions is to move pub-sub messages to more permanent storage.  Dataflow also allows real 
time analytics and window functions built with Python, SQL, or Java.  It's like cloud functions for pub/sub, but as a 
DAG of jobs in an ETL process instead of a function.  

Commands to create a pub-sub topic, subscribe, pull, etc.

```
# Set the project
gcloud config set project glowing-furnace-304608

# Create a topic (a message stream)
gcloud pubsub topics create topic-from-gcloud

# Create a subscription
gcloud pubsub subscriptions create subscription-gcloud-1 --topic=topic-from-gcloud

# Pull from subscription
gcloud pubsub subscriptions pull subscription-gcloud-1

# Publish some messages to see what happens
gcloud pubsub topics publish topic-from-gcloud --message="My First Message"
gcloud pubsub topics publish topic-from-gcloud --message="My Second Message"
gcloud pubsub topics publish topic-from-gcloud --message="My Third Message"
gcloud pubsub subscriptions pull subscription-gcloud-1 --auto-ack
gcloud pubsub subscriptions pull subscription-gcloud-2 --auto-ack

# Inspect and delete topics (subscriptions are deleted when the topic is)
gcloud pubsub topics list
gcloud pubsub topics delete topic-from-gcloud
gcloud pubsub topics list-subscriptions my-first-topic
```

#### Event Driven Architecture

Events are things that happened in the past, e.g. user password change, successful payment, profile deletion, etc.  An 
event is an immutable object that contains data.  An event driven architecture uses events to trigger de-coupled 
micro-services.  Events in this architecture are communicated asynchronously.  

As an example, suppose you have a checkout micro-service (ms) that communicates with an inventory ms and a shipping ms.  
Checkout is an event that triggers the inventory and shipping ms.  

Events can be stateful or stateless.  Stateless events are events that stand alone, with no ties to previous events.  It 
does not matter which consumer/subscriber handles the message.  Stateful events are events that are related to past or 
future events.  They are used for aggregators or time sensitive events, like an email notification if there are more 
than x failures of a system in < 1 minute.  Another example is aggregating, e.g. counting number of failed orders in 
the last hour.  Stateful events must route to the same consumer/subscriber for aggregations.  You cannot route stateful 
events to > 1 consumer, because they do not communicate with one another.  This means that stateful events cannot be 
load balanced, and scalability is hindered.  A rule of thumb is to strive for stateless EDA unless stateful is required.  

##### Event Streaming

Event streaming is when messages are published to queues that store messages for a period of time before they are 
removed.  The consumers listen to queues and pull messages when needed.  Streaming engines can be used as the single 
source of truth, because they serve as a DB of sorts.  Sensor readings or IoT data are examples of streamed events. 

Event streams are used mainly for events generated outside the system.  That distinguishes them from pub/sub or topic 
based message brokers that are used mainly for events generated by the system, like new orders or new user accounts. 
Message brokers tend to keep events until they are acknowledged, while event streams do not care if the events are 
acknowledged.  

Kafka is an example of an event streaming service.  Pub/sub and RabbitMQ are examples of message brokers.  

## Getting Started with GCP

1. Set up a GCP account with credit card, email, and org details.
2. Install gcloud CLI.
   1. Verify installation with `gcloud --version`
3. Authenticate with `gcloud auth login`
   1. Your terminal can now run commands linked to your account.  You must authenticate with every new terminal.  
4. Set your default project with `gcloud config set project PROJECT_ID`

You can also use Cloud Shell from the GCP console, instead of the gcloud CLI installed locally.  

## Building and Pushing Images to Your GCP Project's Image Repository (Artifact Registry)

GCP's image repository, a.k.a. container registry, has been renamed artifact registry.  To migrate, replace the gcr.io 
parts of the lines below with `LOCATION-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE`.  For example: 
`us-central1-docker.pkg.dev/PROJECT_ID/REPOSITORY/test-app`.  You can also copy images from container registry to 
artifact registry with the URL `us-docker.pkg.dev/PROJECT_ID/gcr.io`.

1. Build the image 
   1. `docker build -t test-app .`
2. Test the image locally 
   1. `docker run -p 8081:8081 test-app`
   2. assume the image runs a hello-world app on port 8081, and you map local port 8081:docker port 8081
   3. assume you have exposed port 8081 in the container
   4. Open localhost:8081 in browser
3. Tag the image locally
   1. Container registry: `docker tag test-app gcr.io/PROJECT_ID/test-app`
   2. Artifact registry: `docker tag SOURCE_IMAGE LOCATION-docker.pkg.dev/PROJECT_ID/REPOSITORY/TARGET_IMAGE:TAG`
   3. If tag is not supplied, 'latest' is used by default.
4. Push the image to registry
   1. Container registry: `docker push gcr.io/PROJECT_ID/test-app`
   2. Artifact registry: `docker push LOCATION-docker.pkg.dev/PROJECT_ID/REPOSITORY/TARGET_IMAGE:TAG`
   3. If tag is not supplied, 'latest' is used by default.
   4. This will only work if you have authenticated with gcloud CLI in the terminal

If you want to pull an image from your GCP project:
1. Container registry: `docker pull gcr.io/PROJECT_ID/test-app`
2. Artifact registry: `docker pull LOCATION-docker.pkg.dev/PROJECT_ID/REPOSITORY/TARGET_IMAGE:TAG`

## Deploying a Containerized Application to Cloud Run

Cloud run is a fully managed compute environment for serverless containerization.  It is used for stateless 
applications, that is, applications that do not need to store data or remember sequences of events in memory.  
Cloud run scales automatically and allows you to pay only for what you use.  

Cloud run differs from K8s in that it was designed to deploy a containerized app in seconds: cloud run manages things 
that you could define yourself in K8s.  Cloud run for Anthos is an option that allows you to run a K8s cluster over 
multiple clusters, including different cloud providers and on premises.  

If your application is stateful, use the App Engine instead of cloud run.  Cloud run is useful as long as your 
container takes < 10 seconds to start, as when it is not being used, the application has no server.  So when a 
request comes in, cloud run scales the application up and the container must start before the application runs.  
You can supply a minimum number of instances argument to cloud run, which will guarantee that many servers are 
available.  This would be useful for containers that take a while to start, so that requests are not delayed
(there would still be a delay during scaling).  

Since cloud run is serverless, you should aim to keep images as small as possible, because larger images take 
longer for containers to start.  Larger images also likely utilize more CPU%, and cloud run scales based on CPU 
utilization, aiming for each instance to be utilized <= 60%.  

As with all services, you can deploy with the CLI using the commands below, or use the cloud console.  If you choose 
the console, you can configure CPU allocation, auto-scaling, ingress, and authentication for requests.

To deploy with cloud run, you have 2 options:

<em>Option 1</em>
1. Build & push image to artifact registry
2. Run the command to deploy an image from the registry with cloud run.

<em>Option 2</em>
1. Run the command to deploy application to cloud run directly from source code.  
   1. Internally, GCP runs option 1 under the hood, obscured from view.  

The command below executes option 1, deploying the image tagged 'test-app' from the artifact registry.  Note that the 
commands below are for the container registry, which uses gcr.io.  If you are using artifact registry, use the patterns 
shown in the section of this document that shows how to push/pull with the artifact registry.

```
gcloud run deploy test-app \
   --image gcr.io/{PROJECT_ID}/test-app \
   --region us-central1 \
   --allow-unauthenticated \
   --max-instances 2 \
   --min-instances 1 
```

The command below executes option 2, deploying source code in the current directory (`--source .`) to cloud run.

```
gcloud run deploy test-app \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances 2 \
  --min-instances 1 
```

After deploying, you can go to Cloud Run in the console and click on the name of the application.  There will be a URL 
at the top where you can access the application.  

### Cloud Run Parameters

Cloud run has a max concurrent requests parameter per container instance, which defaults to 80 and maxes out at 1,000. 
Cloud run has CPU values of 1, 2, 4, 6, and 8.  Min and max instances handle instance scaling.  Platform is a parameter 
that can be 1 of <managed, GKE, Kubernetes>.  GKE and Kubernetes platform are used only when your organization requires 
deployments to be on a K8s cluster.  

## Cloud Build

Cloud build is a managed CD platform that automates building and deploying applications to cloud run, app engine, etc.  
To use cloud build, you create a cloudbuild.yaml file that has instructions for building the docker image, pushing the 
image to artifact registry, and deploying the image to wherever you want (e.g. cloud run).  To make the deployment 
continuous, add cloudbuild.yaml to the Git repo and create build triggers on GCP.  The triggers automatically detect 
code changes and run deployments.  Here is an example cloudbuild.yaml:

```
steps:
# Build the container image
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/PROJECT_ID/test-app', '.']
# Push the container image to Container Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/PROJECT_ID/test-app']
# Deploy container image to Cloud Run
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args: ['run', 'deploy', 'test-app', '--image', 'gcr.io/PROJECT_ID/test-app', '--region', 'us-east1']
images:
- gcr.io/PROJECT_ID/test-app
```

If you want to run cloud build yourself with this yaml: `gcloud builds submit --region us-central1`

If you want GitHub to run this, add the commit SHA to the yaml file as the image tag (use $COMMIT_SHA instead of the 
actual hash).  Then create a  trigger from the gcloud console.  Tell the trigger which repo to watch and which type of 
event to look for (e.g. branch push).  Choose the service account that will process the trigger and make sure it has 
the permissions (go to IAM service account credentials API in the gcloud console).  You can do this using the CLI 
and the following commands.  

```
# Assign the roles 
gcloud projects add-iam-policy-binding PROJECT_ID \
--member=serviceAccount:PROJECT_NBR@cloudbuild.gserviceaccount.com --role=roles/iam.serviceAccountUser

gcloud projects add-iam-policy-binding PROJECT_ID \
--member=serviceAccount:131640033627@cloudbuild.gserviceaccount.com --role=roles/run.admin
```

## Deploying a Containerized Application to App Engine

App engine is a serverless option for deploying stateful and stateless applications, which may or may not be 
containerized.  This means you only pay for infrastructure + usage time, and there is no maintenance overhead for 
provisioning, scaling, logging, monitoring, or load balancing (it's managed).  

App engine offers 2 types of environments: standard and flexible.  Standard gives you pre-configured runtime, much like 
a server that comes pre-loaded with CUDA and Python packages.  Flexible gives you control over the runtime, and you can 
use a custom docker image.  Note that if you choose flexible, you must have 1 instance running at all times.  App Engine 
Standard environment has a more limited networking configuration and doesn't allow for the creation of VPN connections, 
nor does it allow SSH access.  If you need to SSH into a VM, use flexible.  Standard does no support C++.

App engine is structured in a component hierarchy, with application at the top.  You can only create 1 application per 
project, and this application serves as the container for everything that you create in app engine.  Under application 
comes service.  The service component is what you are deploying in app engine, like a micro-service.  So when you deploy 
your "app" to app engine, app engine thinks of your "app" as a service contained in your project's application.  
Services are versioned and each version is tied to 1 or more instances.  Thus, when you deploy to app engine, you are 
deploying to managed compute instances.  This is why app engine is the most flexible way to deploy: you can deploy a 
standalone app (service) or a containerized app (also a service).  

Before starting a deployment with app engine, save your service account (SA) credentials env var, which is a path to a 
JSON file with your credentials that you can download from GCP:
`export GOOGLE_APPLICATION_CREDENTIALS='/path to credentials file/sa_creds.json'`

You can deploy directly from source `gcloud app deploy`.  This command assumes you have an app.yaml file in the current 
directory with instructions.  Example:
```
runtime: python39
service: default
```
This file specifies which runtime to use.  It's using app engine's standard environment for Python 3.9, just like what 
you would get using FROM python39 in a docker file.  If you were using app engine's flexible environment, your app.yaml 
file might look like this instead:
```
runtime: python
service: default
env: flex
entrypoint: gunicorn -b :$PORT main:app
runtime_config:
  python_version: 3.9
```

### Splitting Traffic Between Different Versions of an Application

You can split traffic between app versions, like for A/B testing.  You can do this from the console under 'Versions' 
and either clicking the box next to the version and selecting the option to migrate traffic, or the 3 dots to split 
traffic.  Below will show how to do it via the CLI.  

```
# Check the versions and instance running for the app 
gcloud app versions list
gcloud app instances list 

# Get the URL for the app for a specific version
gcloud app browse --version {version_id}

# Split the traffic between different versions of the app .Defaults to split by IP addresses
# Replace v1 and v2 with your version numbers
gcloud app services set-traffic --splits=v1=.5,v2=.5

# Split the traffic between different versions of the app by random and not by IP Addresses 
# Replace v1 and v2 with your version numbers
gcloud app services set-traffic splits=v1=.5,v2=.5 --split-by=random
````

### Caching in App Engine

Data retrieval is time-consuming.  Frequently accessed data can be retrieved faster if it is stored in a cache, or 
key-value store, like Redis or Memcache.  GCP provides 2 types of Memcache: shared and dedicated.  Shared works on a 
best effort basis, meaning performance is not guaranteed, but it is free.  Dedicated is performant but costly. 

To use memcache with app engine, you must enable app engine APIs in the app.yaml file: `app_engine_apis: true`

Memcache uses DataStore (another GCP service) under the hood.

As an example, suppose you have an app that queries BigQuery.  Your function can first check if the query (key) exists 
in memcache.  If not query BigQuery and store the result in memcache.  Return the result from memcache.  In Python, the 
memcache.set() function takes a parameter that indicates how long the data should be stored, e.g. 3600 seconds or 1 
hour.  

#### Cache Write Policies

<em>This section applies to caching in general, not just caching in app engine.</em>

If you have a cache serving as a DB cache, you have write policy options for synchronizing the cache with the DB:
1. Write-through
   1. Data is written to the cache and DB simultaneously or sequentially, acknowledgement (Ack) is sent when both writes are complete
   2. Useful for fast reads and for preventing data loss
   3. Has higher overhead because it has to write 2x
   4. Best used for apps that write and then read that data immediately
2. Write-back
   1. Data is written to cache only and Ack is sent immediately, sync service copies data to DB later
   2. Useful for fast writes
   3. Has risk of data loss if there is a cache failure or the sync fails (low availability and durability)
   4. Best used for write-heavy apps that require low latency and can accept some data loss
3. Write-around
   1. Data is written to DB only and Ack is sent immediately, data is loaded to cache from DB if app hits cache and does not find the needed data
   2. Has no risk of data loss but recently written data requires a cache miss to be loaded to cache
   3. Best used for apps that don't re-read or infrequently access data once it is written

#### DataStore

Memcache uses DataStore under the hood.  DataStore is a NoSQL document oriented key-value store, similar to MongoDB.  
It is useful for apps with constantly changing, high speed data, like mobile games, real time inventory, and session 
management.  

An example of using DataStore is a wish list microservice.  When the user adds an item to the wish list, the wish list 
MS sends a message to pub/sub with {session ID, product ID, wishlist status}.  Pubsub triggers a cloud function to 
persist the data in DataStore, and the wish list MS retrieves it from there.  

### App Engine Scaling

App engine has 2 types of scaling: auto and manual.  In auto-scaling, the instance types (compute engines) available 
are F class.  In manual scaling, the instance types are B class.  If you do not specify scaling in your app.yaml file, 
the default is auto-scaling with an F1 instance.  You can add scaling instructions to your app.yaml file as follows:

```
# Example - 1 : Manual Scaling using B Instance Types 
# App engine will spin up 2 B2 instances at deployment time, and they will remain up
instance_class: B2
manual_scaling:
  instances: 2

# Example - 2 : Automatic Scaling using F Instance Types 
# App engine will spin up 1 F4 instance at deployment time, and can scale to a max of 5 F4 instances
# Scaling will occur when CPU of any instance reaches 80% or 10 concurrent requests over all instances
# Resources for each instance can also be specified, but they are optional (will use defaults if not specified)
instance_class: F4
automatic_scaling:
   min_num_instances: 1
   max_num_instances: 5
   target_cpu_utilization: 0.8
   max_idle_instances: automatic
   max_concurrent_requests: 10
   min_pending_latency: automatic
resources:
  cpu: 1
  memory_gb: 0.5
  disk_size_gb: 10
```

## Deploying a Containerized Application to Cloud Functions

Cloud functions is a serverless execution environment for running single purpose functions that are attached to events 
emitted from your GCP project's infrastructure.  You can think of it as a function as a service, which can be either 
HTTP or event driven.  Cloud functions are stateless.  Cloud functions use pub/sub and cloud run under the hood.  Cloud 
functions can be written in any programming language.  You pay only for what you use (nbr invocations, compute time, 
memory & cpu).  Cloud functions are for small, event driven tasks.  If you need to trigger a process to run on a large 
amount of data, you should deploy an app to App Engine that can be triggered instead.  Cloud functions are also not a 
good option for push/pull processes in your apps: use cloud functions to respond to events emitted from GCP 
architecture itself, not your apps, e.g. cloud function triggered when IAM policy changes.  

An example for when you might use a cloud function is when you dump a new data file to a bucket and need to run 
ETL, or to load it to a BigQuery table.  You might also use cloud functions for webhooks, IoT, or lightweight APIs.  
The key is lightweight, short running code.  Best practices for cloud functions:
* Send HTTP responses in HTTP functions
* Do not start background tasks using cloud functions
* Write stateless, idempotent functions

Cloud functions can use images from the artifact registry.  They have a timeout of 9 minutes for event triggered 
functions and 60 minutes for HTTP triggered functions.  They are limited to 16 Gb RAM with 4 CPUs, and 1,000 concurrent 
requests.  

Auto-scaling in cloud functions depends on invocations: 1 invocation = 1 instance until the function completes.  So if 
a function is running and a new invocation comes in, another instance is created.  This is not true if you configure 
instance concurrency: you can specify how many concurrent invocations a single instance can handle (max = 1,000).  
Concurrency only works if your function is written such that it can run concurrently.  Like all serverless apps, 
cold starts are a problem that can be overcome by specifying a min nbr of instances, although this increases cost.  

To use Cloud Functions, you must enable the following APIs:
```
# APIs to be enabled 
- cloud function 
- cloud build 
- eventarc
- cloud run admin api 
- artifact registry 
```

You should also give the SA permissions to execute the cloud function, which you can do via the console or CLI.  You 
should assign 1 SA per cloud function.

```
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects list --filter="project_id:$PROJECT_ID" --format='value(project_number)')
SERVICE_ACCOUNT=$(gsutil kms serviceaccount -p $PROJECT_NUMBER)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT \
  --role roles/pubsub.publisher

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member serviceAccount:$SERVICE_ACCOUNT \
  --role roles/run.admin
```

The commands below show how to deploy a cloud function with the CLI.  You can also use the cloud console.  

The command to deploy from the current directory is:

```
gcloud functions deploy YOUR_FUNCTION_NAME \
--gen2 \
--runtime=python310 \
--region=us-central1 \
--source=. \
--entry-point=upload_file \
--trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
--trigger-event-filters="bucket=cloud-func-trigger"
```

In the above example, you define an entry point, which is the name of a function in your Python script that will run 
when the trigger event occurs.  There are also filters that you can add to filter events, to ensure that your function 
runs when it is supposed to.  Here for example, the function only runs when the 'cloud-func-trigger' bucket receives a 
file and the event type is 'storage.object.v1.finalized', meaning the object finished writing in the bucket.  

You can monitor the cloud function logs from the console or from the CLI: 
`gcloud beta functions logs read FUNCTION_NAME --gen2 --limit=100`

### Triggering a Cloud Function from a Pub/Sub Message

You can trigger a cloud function any time a message is sent to a specific topic in a pub/sub stream.  

In the example below, a function is deployed to run whenever a certain topic receives a message.  The entry point is 
the function is a Python script to run.  The second command shows how to test the cloud function by publishing a message 
to the topic.

```
# Deploy cloud function with pub-sub trigger
gcloud functions deploy YOUR_FUNCTION_NAME --runtime python38 \
--trigger-topic YOUR_TOPIC --entry-point FUNCTION_TO_RUN --memory=1GB

# Publish message to the above topic 
gcloud pubsub topics publish YOUR_TOPIC --message="Hello Cloud Function"
```

You would run the commands above from the directory in which you have a .py file with a function called 
FUNCTION_TO_RUN.  In the example .py script below, FUNCTION_TO_RUN = process_pubsub_events, and it is a function to 
decode a message, parse the event ID and type, and print them.  

```
import base64

def process_pubsub_events(event, context):

    message = base64.b64decode(event['data']).decode('utf-8')

    event_id = context.event_id
    event_type = context.event_type

    print(f"A new event is received: id={event_id}, type={event_type}")
    print(f"data = {message}")
```

### Triggering a Cloud Function from an HTTP Request

The command is similar to the one for pub/sub, where FUNCTION_NAME comes from your .py script:
`gcloud functions deploy FUNCTION_NAME --runtime python310 --trigger-http --allow-unauthenticated`

## Using Workflows for Orchestration

GCP workflows is a managed workflow orchestration tool, like Dagster or Prefect.  A YAML or JSON file defines workflow 
components.  Example workflow.yaml:

```
# Data validation workflow called via get request to the URL passed to the args section
- data_validation:
    call: http.get
    args:
        url: https://fraud-detection-input-validation-dot-gcp-serverless-project.uc.r.appspot.com
    result: data_validataion_result
# Model training workflow depends on output of data validation flow
# This step is a post to the URL provided in args, with the arguments provided in body (output from data validation)
- model_training:
    call: http.post
    args:
        url: https://fraud-detection-model-training-dot-gcp-serverless-project.uc.r.appspot.com/
        body:
            is_output_valid: ${data_validataion_result.body.is_output_valid}
            total_attrbutes: ${data_validataion_result.body.total_attrbutes}
    result: model_training_result
# The final step is to return the output of model training
- return_result:
    return: ${model_training_result}
```

To deploy this workflow from the current dir: `gcloud workflows deploy YOUR-WORKFLOW-wf --source workflow.yaml`

To run this workflow: `gcloud workflows run YOUR-WORKFLOW-wf`

The workflow components must be deployed somewhere too.  Each component must be deployed, so if you are deploying to 
app engine, for example, then each component needs its own app.yaml file.  As an example, here is what a model training 
deployment component might look like, using app engine flexible mode:

```
# app.yaml
runtime: python
service: fraud-detection-model-training
env: flex
entrypoint: gunicorn -t 0 -b :$PORT main:app
runtime_config:
  python_version: 3.7
instance_class: F2
automatic_scaling:
   min_num_instances: 1
```

This yaml corresponds with the model_training component of the previously defined workflow.  Since model training 
depends on data validation, data validation should be deployed with its own app.yaml.  

## Big Data Processing on Dataproc Serverless

Dataproc is a serverless offering to run Spark batch workloads without configuring a Spark cluster.  You specify 
workload parameters and then submit the job, and Dataproc will handle allocation of resources.  DataFlow and Apache 
offer similar services, but they have larger learning curves.  Dataproc's syntax is more similar to base Spark.  
Dataproc requires a persistent history server (PHS), a single node dataproc cluster, to be started.  This single node 
allows you to run stuff.  It provides logs, history, and Yarn metrics out of the box.  

Dataproc can do stream & batch processing for ETL using Spark under the hood, just like DataFlow.  If you have an 
existing ETL pipeline in Spark that you want to move to cloud, use Dataproc.  If you need to build a new ETL pipeline 
in Spark, use DataFlow.  Spark clusters in dataproc take 1 minute to launch, they're ephemeral as long as the job, and 
you only pay for what you use.  Dataproc has a cloud storage connector automatically installed on a cluster, allowing 
you to access data in cloud storage for Dataproc, instead of the attached HDFS that you would usually need for big data 
jobs.  

These are the 5 properties that control auto-scaling behavior of spark jobs:
1. spark.dynamicAllocation.enabled - defaults to True, decides whether to use workload allocation
2. spark.dynamicAllocation.initialExecutors - min, default = 2, max = 500
3. spark.dynamicAllocation.minExecutors - min, default = 2
4. spark.dynamicAllocation.maxExecutors - default = 1000, max = 2000
5. spark.dynamicAllocation.executorAllocationRatio - rarely used, default = 0.3, max = 1.0 for max scalability

### Deploying a Spark Job to Dataproc

Make sure dataproc is enabled for your account: `gcloud services enable dataproc.googleapis.com`.  Pyspark jobs running 
on dataproc are not exposed to the internet; they only have private IP addresses.  So you need to create a subnet to 
allow Google to access the dataproc server internally.  A subnet is like a post office; you don't send mail directly to 
people, you send it to your local post office, which sends it to their local post office.  Subnets allow more efficient 
routing by gathering ranges of IP addresses and communicating everything between the ranges, before more fine grained 
communication happens.  A <em>subnet mask</em> is like the address of a post office; it specifies where communication 
is sent before being split to the devices within that range of IPs.  The command below creates a subnet for dataproc:

```
export GOOGLE_CLOUD_PROJECT={your-project-id}
export REGION=us-central1
export BUCKET=pyspark-jobs-ph

# Create Subnet 
gcloud compute networks subnets update default \
  --region=${REGION} \
  --enable-private-ip-google-access

gcloud compute networks subnets describe default \
  --region=${REGION} \
  --format="get(privateIpGoogleAccess)"
```

A couple more steps are needed to set up and submit a job.  First, create a bucket in the same region.  Then set up a 
Dataproc PHS cluster in that region.  

```
# Define a PH Cluster Name   
export PHS_CLUSTER_NAME=pyspark-phs

# Create a bucket to keep PHS logs
gsutil mb -l ${REGION} gs://${BUCKET}

# Create a single node dataproc PHS Cluster (enables spark UI and logs)
gcloud dataproc clusters create ${PHS_CLUSTER_NAME} \
    --region=${REGION} \
    --single-node \
    --enable-component-gateway \
    --properties=spark:spark.history.fs.logDirectory=gs://${BUCKET}/phs/spark-job-history
    --properties=spark:spark.dynamicAllocation.maxExecutors=10
```

You should now be able to access the dataproc cluster from the GCP console, and see graphs on the cluster stats, as 
well as a link to the Web UI for Yarn where you can see submitted jobs in Hadoop.  

Let's suppose you have a Spark job in a .py file like the one below.

```
# mysparkjob.py
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col,year,month
from pyspark.sql.types import BooleanType

# BigQuery table to read (it's a public dataset with stackoverflow posts)
table = "bigquery-public-data:stackoverflow.stackoverflow_posts"

# Initialize Spark session
spark = SparkSession.builder \
    .appName("pyspark-example") \
    .config("spark.jars", "gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.12-0.26.0.jar") \
    .getOrCreate()

# Read the bigquery table into a dataframe
df = spark.read.format("bigquery").load(table)

# Filter the df for specific tags, and show the top 50 tags by post count by year, month
df = df.filter(col("tags").isNotNull()) \
        .select(
            df.tags,
            year(df.creation_date).alias('post_year'), \
            month(df.creation_date).alias('post_month')
            ) \
        .groupBy(["tags","post_year","post_month"]) \
        .count() \
        .orderBy("count", ascending=False) \
        .limit(50) \
        .cache()

# Write the result to a CSV
df.write.option("header", True).csv("gs://serverless-spark-udemy/test_output")
```

You can submit this job to dataproc as follows:

```
# Submit the pyspark batch job to dataproc serverless 
# batch parameter is a random ID that you specify
# deps-bucket is a bucket to use temporarily to upload your python script
# jars is a parameter with spark version .jar file
gcloud dataproc batches submit pyspark mysparkjob.py \
  --batch=top-stackoverflow-tags \
  --region=${REGION} \
  --deps-bucket=gs://serverless-spark-udemy \
  --jars=gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.12-0.26.0.jar \
--history-server-cluster=projects/${GOOGLE_CLOUD_PROJECT}/regions/${REGION}/clusters/${PHS_CLUSTER_NAME} \
  -- ${BUCKET}

# Submit the pyspark batch job to dataproc serverless with autoscaling parameters 
# This is the same as above but customizing the iniitalExecutors parameter
gcloud dataproc batches submit pyspark top_stackoverflow_tags.py \
  --batch=top-stackoverflow-tags \
  --region=${REGION} \
  --deps-bucket=gs://serverless-spark-udemy \
  --jars=gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.12-0.26.0.jar \
--history-server-cluster=projects/${GOOGLE_CLOUD_PROJECT}/regions/${REGION}/clusters/${PHS_CLUSTER_NAME} \
--properties=spark.dynamicAllocation.initialExecutors=3 \
  -- ${BUCKET}
```

You can monitor the status of the job in GCP console > Dataproc > Batches.  Look for the batch name that you defined in 
the 'batch' parameter from when you submitted the job.  If no batch was defined, you'll get a random one.  

#### Scheduling Dataproc Jobs with Cloud Composer (Managed Apache Airflow)

You can do this via GCP Console.  Go to cloud composer and create an environment.  Fill out the specs, with node count, 
machine type (N1 for example is the smallest), SA, number of schedulers (leave as 1 most times).  Once created, go to 
the DAGs folder that appears in the console by the environment name.  GCP will automatically create a bucket for the 
environment.  If you go into it, you can see a DAGs folder where you can upload your .py airflow DAG.  An example of an 
Airflow DAG is here: https://github.com/siddd88/udemy-gcp-serverless-architecture/blob/main/dataproc-pyspark/airflow-composer/dataproc-serverless-dag.py

When you no longer need a scheduled job, be sure to delete the environment, the batch, and the PHS cluster.

## BigQuery

BigQuery is an exabyte scale relational data warehouse.  CSV/JSON format imports and exports are possible.  You can also 
directly query other sources (cloud storage, cloud SQL, BigTable, Google Drive) using permanent or temporary external 
tables.  

If you need to load historical logs for analysis, use BigQuery instead of Cloud Logging.  Cloud Logging is only for 
monitoring, error reporting, and debugging, not for analytics and queries.

To query an object (e.g. CSV file) stored in a bucket in cloud storage, upload the file to the bucket, and get its URL.  
The URL can be used in Python libraries to query or write data to a BigQuery table.  For example, you could have a 
Python app that ingests data from a bucket into a BigQuery table by creating the table and then filling it with data 
from the object at the bucket URL.

Create a table in BigQuery by going to BigQuery in the console and:
1. Click on the 3 dots next to your project and select 'create dataset'
2. Run CREATE_TABLE command for the dataset name and table name, e.g. `CREATE TABLE ds_name.table_name (colname STRING)`
3. If the cloud services (cloud run, app engine) are not enabled, enable them in cloud build settings.
4. Make note of the service account email that will be executing the build.

BigQuery queries are expensive for large datasets, so always use the bq CLI to dry run queries to check how costly they 
will be: `bq --dry-run`, or use a price calculator with a byte size volume estimate.  Partitioning a BigQuery table 
can reduce its costs because it increases query efficiency.  

BigQuery is for analytics, and sometimes you have sensitive data that you do not need for analysis.  You can limit 
access to specific columns by tagging the column  and using an IAM policy to restrict access to each policy tag.  As 
an example, you can use Google's default "Business Criticality: High" policy tag for an employee's SSN when you create 
a BigQuery table using the cloud console and create a column for "employee SSN".  That way, any time the table with 
this column is queried, Google will compare the IAM group policy access to the policy tag and only display the column 
if the user has the right permissions.  You can also use row level policies to hide access to certain rows.  A good 
example of this is EU privacy laws that restrict non Europeans from viewing PII.  You can create a row access policy 
using SQL-like syntax:
```
CREATE ROW ACCESS POLICY
   us_filter
ON 
   dataset1.table1
GRANT TO
   ("group:sales-us@example.com", "user:jon@example.com")
FILTER USING
   (Region="US");
```
In this example, 'Region' is a column in table1.  And you can limit access to rows with certain column values.  

BigQuery ML allows some types of ML models to be implemented in SQL
* regression
* k-means
* ARIMA models
* matrix factorization
* tree based models
* imported TF model
The benefit of doing ML in BigQuery is that no data needs to be moved to hit a model.  

## VertexAI

VertexAI is a managed ML platform for
* Data prep
* Model training & versioning
* Model evaluation
* Model deployment

VertexAI supports UI and code based model development, jupyter notebooks, and common frameworks (TF, Torch, etc.).  
On the left side of the console, you'll see workbench (jupyter), pipelines (kubeflow for ML orchestration), training to 
monitor model training, model registry to track deployed versions of models, endpoints where models are deployed and 
where you can see their traffic, and batch predictions if your model is set up for batch mode.  

To get started with VertexAI, create a service account (SA) that will run everything in VertexAI.  Name it something 
like 'vertexai-project-id'.  

### Workbench Notebooks

Notebooks can be managed or user-managed.  Both come with pre-installed environments like CUDA + torch.  Managed 
notebooks have built in integration with other services.  User-managed gives more control to the user.  

If you start a new user-managed notebook, you can upload your own Docker file, requirements.txt, and training script.  
When you first start, you'll only have a /src and /tutorials folders.  Click + to create a new folder to dump your 
files.  At this point, refer to the code in /vertexai_adclicks_notebook.  Upload the advertising.csv to a bucket, as 
shown in the model_training.py script.  Proceed following the README in that directory.  

## Kubeflow

Kubeflow is an SDK for defining and manipulating ML pipelines and orchestrating components.  It is built on top of 
Kubernetes.  You can access kubeflow using notebooks for interacting with the system using the SDK.  There is also a 
UI for managing and tracking jobs, steps, and runs.  

In VertexAI, Kubeflow is a managed service called Pipelines.  Everything Kubeflow does can also be done manually with 
Dagster and K8s, but the benefit is that it is managed: you pay give up control of costs a little bit for ease of use.

Like every orchestration tool, Kubeflow breaks things into atomic elements.  For Kubeflow, these are components.  A 
component is a self-contained set of code that performs 1 step in a ML workflow.  Every component consists of inputs, 
outputs, a container image that the code will run inside, and metadata like (name, desc, etc.).  

Kubeflow has domain specific language (DSL) pipelines where you invoke the components and Python libraries to interact 
with Kubeflow pipeline APIs (any other components you have defined).  A DSL pipeline is defined in a YAML file called 
the compiler, much like Dagster or Prefect.  

<em>The benefit of using Kubeflow is that your ML pipeline's resources during data processing, training, evaluating, 
or serving, are abstracted away, meaning you don't have to worry about configuring them.</em>

Look in the kubeflow folder for examples.

## Scheduling Chron Jobs with Cloud Scheduler

Cloud scheduler is a managed chron job scheduler.  It has retries built in and allows chron expressions for scheduling.  
Each cron job is sent to a target according to the specifications in the schedule:
* Public HTTP(S) endpoints
* Pub/Sub topics
* App engine HTTP(S) endpoints

Suppose you have a pubsub topic already created, with a cloud function set up to run upon receipt of a message.  You 
can schedule a cron job to invoke the pubsub trigger, and thus the cloud function.  The cron job can send a simple 
message to the pubsub the would release the trigger.  

## Monitoring App Engine, Cloud Run, or Cloud Functions

You can use the Monitoring service to set up alerts and monitor your apps.  Go to the Monitoring service from GCP 
console.  Go to metrics on the left and from the dropdown, pick gae (Google App Engine).  You will see some metrics to 
pick from, like response latency.  You can aggregate over time windows and pick 99 percentile for aligner.  You can add 
this metric to a dashboard if you want.  It will be available under Dashboards on the left side of the Monitoring tool.  
Next go to Alerting on the left side, and decide on a notification channel (Slack, email, webhook, sms, pubsub, etc.).  
Create an alert policy based on the metrics you have created and thresholds that you define. 

If you have an instance group that you want to monitor and trigger an alert when under some condition(s), install a 
cloud monitoring agent in each instance in the group.  Alerts are not configured to read from Cloud Storage or Cloud 
Pub/Sub for data to analyze, so you need the monitoring agent installed on the VM to trigger the alert.  

If you want to collect detailed metrics on K8s application performance and ensure applications collect a consistent set 
of metrics, while minimizing the amount of code application developers have to provide to collect such metrics, use 
Anthos Service Mesh.  Anthos Service Mesh, which runs as a sidecar to applications running in pods, makes it so that 
application code does not need to be changed to collect metrics, and the service mesh can be consistently deployed 
across applications.  Installing a Cloud Monitoring agent or Prometheus would require ensuring the component is 
installed in all images that the service uses, which takes more manual effort.  

## Compute Engine

Compute engine offers raw compute servers that you can use (like AWS EC2) with hardware tailored to various needs and 
an OS installed. 

Every instance has internal IP (to GCP services) and external IP (open to the internet).  You can create a static IP 
address to avoid having to SSH to a new address every time you start/stop an instance.  Just make sure the static IP is 
in the same region as the instance.  A static IP address can be assigned to any instance in your project (you can 
change which instance it is assigned to).  Static IPs are not free.  

You can configure startup scripts (bash scripts) to run every time an instance (virtual machine or VM) is created.  
You'll find this option in the management section when you create the VM instance.  You can simplify things further by 
creating an instance template with machine type, image, labels, startup script, etc. and use it to launch instances.  
Another option is to create a custom image that you can load into new VMs to avoid running startup scripts or reduce 
startup time.  You can store the custom image in cloud storage.  Custom images are usually preferable to startup 
scripts.  

Every VM has basic firewall rules to allow or disable internet traffic.  If you want your VM to be accessible, like 
when you host a website on it, check the box to allow HTTPS traffic.  If you want it to be private (SSH only), then 
uncheck that box.  More sophisticated rules, like VPCs, can also be used.  

GCP has spot instances but it calls them preemptible VMs.  You can configure preemptibility when you create the 
instance, in the availability policy section.  Also in that section, you can define how the MV will migrate if Google 
needs to push updates (default is to migrate to another VM and shut the old one down).  UPDATE: GCP now offers spot VMs 
as a specific VM type.  Spot VMs no longer have a max runtime of 24 hours.  

Compute Engine with Persistent Disks is a highly available, scalable, and durable solution that is designed to provide 
low RTO and RPO in case of a disaster. Persistent Disks are automatically replicated within a zone to protect against 
hardware failures and can also be replicated across zones or regions for additional protection. Additionally, Compute 
Engine allows for easy creation of instance templates and auto-scaling groups to help ensure that resources are readily 
available in the event of a disaster. Persistent disks are durable network storage devices that your instances can 
access like physical disks in a desktop or a server. The data on each persistent disk is distributed across several 
physical disks. Compute Engine manages the physical disks and the data distribution for you to ensure redundancy and 
optimal performance. Persistent disks are located independently of your virtual machine (VM) instances, so you can 
detach or move persistent disks to keep your data even after you delete your instances. Persistent disk performance 
scales automatically with size, so you can resize your existing persistent disks or add more persistent disks to an 
instance to meet your performance and storage space requirements.  Persistent disks can only be increased in size.  If 
you want to shrink them, you must detach and create a new one.  Persistent disks can be moved between VMs by snapshotting 
and creating a new disk from the snapshot.  Regional persistent disks are replicated in 2 zones by default (they are 
regional by default), but they can also be zonal.  

Shielded VMs provide verifiable integrity, which means that it ensures that the VM boots from a known, verified, and 
trusted state. Shielded VMs provide the necessary secure boot process by using UEFI firmware, which confirms the 
signature of the boot loader before booting it. Shielded VMs also protect VMs against rootkit and bootkit malware 
attacks. Virtual Trusted Platform Module (vTPM) is another feature offered by Shielded VMs. vTPM is a specialized 
computer chip that can be used to protect objects, such as keys and certificates, that are used to authenticate access 
to your system.  Virtual Trusted Platform Module (vTPM) can be disabled if needed. However, it is generally recommended 
to keep it enabled for added security.  Secure Boot is not enabled by default in Shielded VMs. It needs to be explicitly 
enabled when creating a Shielded VM.

### Labels and Tags

Labels can be used as queryable annotations for resources, but can't be used to set conditions on policies. Tags 
provide a way to conditionally allow or deny policies based on whether a resource has a specific tag.

If you want to check billing for a department, query for labeled resources.  

If you want to limit a group's access, use IAM + tags.

### GPU and TPU Acceleration

GPUs offer high precision float computation.  TPUs offer low precision float computation.  The cheapest TPU is $24/hour, 
or $17k/month, so definitely make sure you do not leave one running by mistake.  There are pre-emptible TPUs in certain 
zones or TPU types.  

VMs with a GPU cannot have their block storage disks scaled while running.  They need to be shut down first.

### Sole Tenant Nodes

When you create a VM, it is hosted on shared hardware (other users share it).  If you need dedicated hardware for 
compliance reasons, you can create a <em>Sole Tenant Node</em> from the Compute Engine service.  You would first make 
a node group with a template, node types, and auto-scaling.  The most important part of a node group is the affinity 
label section.  When you create VMs, you assign it to the node group using those labels.  You will find this option 
under the sole-tenancy section near the bottom of the create instance screen.  

### Choosing which Engine to Use

Use general purpose for apps and dev environments.  Use memory optimized for in-memory databases.  Use compute 
optimized for games.  

### Load Balancing vs Auto-Scaling

Load balancing is balancing traffic between instances.  Auto-scaling is changing resources (more instances, larger 
instances) based on demand.

#### Load Balancing

Load balancing can operate in a single region or across regions.  Load balancing in general can apply to any deployed 
app, but there is also a specific managed service in GCP called load balancer.  This managed service applies to VMs in 
the compute engine service, and it only routes to healthy instances.  

Load balancers typically provide a single anycast IP that serves as an entrypoint, or gateway, into a distributed app.  
They can apply balancing at any network communication layer by balancing the protocol associated with that layer (e.g. 
HTTP, UDP, TCP, etc.)  They can also be internal facing or external facing.  

Load balancers require a backend service (which MIG or pods to route to), balancing mode (how to distribute load), and 
a frontend service (how will external requests come to the load balancer, which IP address and port, which protocol, 
any certs for security, ).  You can have multiple backend services.  

When you create a load balancer in GCP, you will have the option of adding a Cloud CDN (content delivery network) that 
will cache files like JS scripts or images (files that do not change often) to speed up load times.  A CDN is a service 
with servers around the globe to cache your content regionally to reduce load times.  This lets you avoid having to set 
up servers around the globe to serve content in each region.  Cloudflare is a common CDN example.  

Traffic that comes from the internet to a load balancer stops at the load balancer.  From that point forward, traffic 
is internal.  This means you can have HTTP traffic to the load balancer and a different protocol, like TCP for speed, 
from the load balancer to the devices and back.  If your communication to the load balancer is secure and becomes 
unsecure afterwards (e.g. HTTPS to balancer and then TCP to VM instances), it is called TLS termination or offloading.  
This is perfectly ok and actually reduces some of the load from the instances (bc it removes 1 communication layer).  
You could also refer to this setup as a <em>proxy</em> because it transforms the request before sending it on. 

##### Types of Load Balancers

External HTTP(S)
* Traffic Types: global external HTTP(S)
* Destination Ports: HTTP on 80 or 8080, HTTPS on 443
* Proxy or Pass Through: Proxy because it transforms the external request before passing it internally
* Layer 7 load balancer that allows 1 external IP address for all services and has HTTP header and cookie info

Internal HTTP(S)
* Traffic Types: regional internal HTTP(S)
* Destination Ports: HTTP on 80 or 8080, HTTPS on 443
* Proxy or Pass Through: Proxy

SSL Proxy
* Traffic Types: global external TCP with SSL offload at the load balancer (see notes in above section)
* Destination Ports: many options
* Proxy or Pass Through: Proxy because it transforms the external request before passing it internally

TCP Proxy
* Traffic Types: global external TCP without SSL offload at the load balancer (see notes in above section)
* Destination Ports: many options
* Proxy or Pass Through: Proxy

External Network TCP/UDP
* Traffic Types: regional external TCP or UDP
* Destination Ports: any
* Proxy or Pass Through: Pass through
* Level 4 load balancer (a.k.a. session level load balancer) that simply forward requests and responses between the client and server using TCP/UDP, has no info on HTTP headers or cookies, but can be used for sticky sessions

Internal TCP/UDP
* Traffic Types: regional internal TCP or UDP
* Destination Ports: any
* Proxy or Pass Through: Pass through

Note about pass through: if you have a pass through load balancer, the client or external user can see the request 
after it passes through the load balancer and goes to your back end VMs.  

##### Load Balancing Algorithms

* Round-robin = distribute requests evenly, 1 after the other
* Weighted round-robin = distribute requests in proportion to each server's capacity, 1 after the other
* Fewest connections = distribute new request to the server with the fewest active connections
* Lowest latency = distribute new request to the server with teh lowest response time and availability (must track response times)

#### Instance Groups

If you create an instance group, the instances can be managed as 1 unit.  Instance groups (IGs) can either be managed
(every VM in the IG has the same config, as initialized through a template) or unmanaged (can have customized or 
different VMs in the group).  Managed groups can be auto-scaled and auto-healed but unmanaged cannot.  Managed IGs can 
be regional (VMs spread across regions) or zonal (VMs spread across zones in 1 region).  Regional is better for 
availability.  New versions can be released with 0 down time for managed IGs.  As you can see, managed IGs are the way 
to go.  

Managed IGs (MIGs) are like Kubernetes.  If it is easier to deploy your app as a container, you should go with K8s.  If 
it is easier to deploy your app as an image, you can go with MIGs.  MIGs operate with VM instances, whereas K8s operates 
with containers.  

Just like with K8s, MIGs have health checks that you can configure, and whenever a VM is unhealthy, MIG will terminate 
it and spin up a new one to replace it - this is auto-healing.  Health checks are usually done on HTTP, not TCP.  Since 
health checks run periodically, you'll probably want to configure an initial delay for the 1st health check, so that 
GCP is not waiting for your instance to start and thinks that that means it is unhealthy.  

When auto-scaling, MIGs can have cool down and ramp up times.  Ramp up times produce latency, so there is an option to 
use predictive auto-scaling, or you can just use CPU utilization with the expectation that once a threshold is crossed, 
you need to begin ramping up.  Cool down times delay scaling down just to make sure the heavy load has passed.  

MIGs can be stateful (when you need to persist data, like setting up a MIG as a DB) or stateless (when you do not need 
to save data, like serving a REST API or batch processing a queue of work).  

MIGs can be updated in a rolling update by applying a new instance template to the group.  If you modify the startup 
script in an instance template that is being used by a Managed Instance Group (MIG), you will want to propagate the 
changes to all instances in the group. To minimize effort and cost while maintaining available capacity, you should 
perform a rolling-action replace with max-unavailable set to 0 and max-surge set to 1. A rolling-action replace involves 
replacing instances in the MIG one at a time, while maintaining the available capacity. With max-unavailable set to 0, 
the number of unavailable instances will be minimized during the update. With max-surge set to 1, one new instance will 
be created before the old instance is terminated, ensuring that the capacity remains the same during the update.

### Moving VM Instances 

VMs can be moved between zones in a region, but not between regions.  The exceptions are if a VM has a SSD attached, is 
in a MIG, or has Terminated status.  You can always create copies of persistent disks in the zone you want to move to 
though.  

## Networking

Communication between devices happens over many layers.  
* Application Layer - HTTP, SMTP, FTP - Highest layer
* Transport Layer - TCP, TLS (SSL), UDP - Middle layer
* Network Layer - IP - Lowest layer

High performance apps sometimes communicate over the lowest (network) layer directly, but most apps communicate at the 
application layer, which utilizes both layers below it.  

### Types of Communication (Protocols)

A protocol is like a language.  Devices can only communicate if they share the same protocol.  Each protocol has its 
own syntax.  Protocols are assigned to the different communication layers.  

#### Network Layer

The network layer transfers bits and bytes.  It is called the network layer because communication in this layer happens 
over a network, like the internet.  

The network layer uses IP (internet protocol) and is unreliable, because info can be lost in the network.  

#### Transport Layer

The transport layer ensures that bits and bytes are transferred properly.  In a network of many devices, traffic can be 
spread over many devices or routers.  The transport layer resolves any discrepancies to ensure that a target device 
receives the info it is intended to receive.  

The transport layer uses TCP (transmission control protocol), which favors reliability over performance.  It is used to 
ensure that info arrives and is ordered the right way.  If you are downloading a file, reliability is of utmost 
importance, so TCP (or TLS) would be used.  TCP uses a <em>check sum</em> that compares the number of bytes in a 
received packet to the number of bytes that were sent, and if they do not match, TCP asks the sender to re-send the 
packet.

The transport layer also uses TLS (transport layer security), which acts like TCP but with encryption.  You might see 
SSL referenced sometimes.  TLS is the new & improved SSL.  If you hear SSL, it is likely TLS because the terms are used 
interchangeably.  

The transport layer also uses UDP (user datagram protocol), which favors performance over reliability.  It is used to 
ensure that info arrives and is ordered the right way, however it allows for some info to be lost.  Video streaming apps 
make use of UDP instead of TCP, because it's usually preferable to avoid buffering rather than having HD quality.  

#### Application Layer

The application layer (highest layer) is where REST API calls are made and emails are sent.  

The application layer uses HTTP (hypertext transfer protocol), which is a stateless request/response protocol, and 
HTTPS, the secure version of HTTP that uses certificates between devices for security.

#### RESTful

Good practice is to structure URL queries as [resources/ID] where resources is plural and multiple resources are 
chained in groups of 2 (resource with ID), e.g. authors/27/books/343.  If you need more than 2 levels to identify a 
resource, GraphQL might be more suitable for your requests instead of HTTP.  

PUT is idempotent, meaning duplicate requests are ok (setting an attribute to False many times does not matter - end 
result is false), whereas POST is not (setting an attribute to False many times has an ambiguous result).  So if you 
need to enable/disable a user ability, for example, PUT would be better to use if the request could happen multiple 
times, e.g. users/23/enable, which is in [resources/ID/action] structure.  POST requests are like counters, which are 
different depending on how many times you increment them - they are not idempotent.  

#### Websockets

In HTTP, a client must ask the server if there is new information any time that it needs to.  The server will never 
just tell the client that new info exists unprompted.  The connection between client and server is terminated as soon as 
a request finishes.

Websockets connect the client and server once and keep the connection open.  So the server can send info to the client 
unprompted.  It also means that clients and servers can send messages without expecting a response from the other.  A 
chat service is a great example of when websockets would be useful.  

Websockets can cause trouble with load balancers because they create long lived connections.  That means they also may 
introduce complications to your code: if the connection is lost, it must be re-established.

HTTP and websockets are both built on top of TCP.

The difference between a websocket and a message queue is that the client/server in a websocket know about each other 
and are connected.  A message queue connects services that do not know each other exists and do not actually care about 
communicating.  

### Remote Procedure Calls (RPC)

RPCs allow 1 service to call another as if it were a local function, meaning services written in different programming 
languages can easily communicate.  

RPC does not work in web browsers, so if you need a communication protocol that supports web & mobile, for example, RPC 
is not an option (it does not support web, and limited for mobile).  If you need to communicate externally, RPC is not 
an option.

gRPC uses protobuf, a binary protocol, to encode messages, making them much smaller and faster than JSON or XML.  
Protobuf messages need to be decoded, because they are not human readable.  

### Virtual Private Cloud (VPC)

A VPC is your own private network in GCP, just like a local area network.  VPC is a global network that contains 
subnets in 1 or more regions.  VPC's allow you to bring your own IP addresses for migrating on premise resources to the 
cloud, which means you won't have to update firewall rules in your services.  You can take these IPs with you if you 
migrate off GCP.

Every project has a default VPC, but you can create your own too.  When you create a resource, like a VM, the VPC shows 
up in the network interfaces box.  

Shared VPC allows resources in different projects to talk to one another without leaving Google (no outside internet 
communication).  Projects with a shared VPC must be in the same organization, because a shared VPC is created at the 
org level and requires shared VPC admin rights to create.  You can specify which subnets you share in the shared VPC.

VPC peering allows resources to be shared across organizations.  It is secure because all communication happens in 
Google's network, and is not exposed to the open internet.  Using VPC peering incurs no data transfer charges.  VPC 
Network Peering is a service that enables you to establish a direct, private connection between two VPC networks. You 
would use it for times when you would otherwise have to create an external connection to another network domain, like 
if you are a SaaS company that needs to connect to your client's data source.  Ordinarily, this would require a VPN or 
setting up an external IP rule.  But VPC peering eliminates that need, has lower latency than an external IP or VPN, and 
eliminates the egress charges for data transfer to an external IP.  When you use VPC Network Peering, traffic stays 
within Google's network and does not traverse the public internet. Additionally, VPC Network Peering allows you to use 
private IP addresses within your VPC networks (bring your own IP).  To set up a peered VPC, both sides (client and SaasS 
provider) must set up their VPC for peering, because they are administered separately.  You can only peer up to 25 PVCs.  

The resource hierarchy in GCP goes: Organization > Folder > Project > Resources.  An org can have many folders, a 
folder can have many projects, and a project can have many resources.  Good practice is to separate your environments 
at the project level, so there is a project for dev, a project for prod.  Billing occurs at the org level, but an org 
can have many billing accounts that can be linked to different projects.  Policies can be defined at the project, 
folder, or organization level.  You can share policies across two different projects in GCP as long as they are in the 
same folder or organization.  Both IAM and organization policies are inherited through the resource hierarchy, and the 
effective policy for each resource in the hierarchy is the result of policies directly applied on the resource and 
policies inherited from its ancestors (the union).  Projects belong to the organization, not the user who creates them, 
so if a user is deleted, the project remains.  

Best practices for VPC:
* Use multiple projects, one for each environment and each application within an environment
* Use separate VPCs for each org unit and a common VPC for shared services
* Isolate sensitive applications in their own VPC

Cloud Interconnect provides a secure and private connection between an on-premises data center and GCP, while Cloud KMS 
and Cloud IAM help control access to data.  Cloud Interconnect is used to connect your on-premises network to your 
Google Cloud VPC network using a physical connection, and it doesn't apply when a connection needs to be established 
between two VPC networks (they're both already in the cloud).  Google Cloud Dedicated Interconnect is a dedicated, 
high-speed, low-latency connectivity option that enables data replication between on-premises data centers and GCP 
projects. It provides a direct physical connection between your on-premises network and Google's network, which can 
reduce latency and packet loss.  If your customer is experience data loss during transmission, using Google Cloud 
Dedicated Interconnect would likely resolve the latency issues and packet loss that the company is experiencing with 
their VPN connection.

Using redundant network connections between the on-premises data center and Google Cloud Platform helps to minimize the 
risk of network failure. This can be achieved by configuring multiple connections and using load balancing to distribute 
the traffic across them. If one connection fails, the traffic is automatically rerouted to the other connection, 
ensuring that the network remains available.

Partner Interconnect connection allows the customer to lower latency by connecting directly to a partner network that 
is directly connected to Google.  A Dedicated Interconnect connection would require the customer to buy new hardware 
to get a 10 gig interface for their firewall.  These are options you can use when the customer needs to hardline connect 
one of their data centers to GCP.  

VPC Service Controls improves your ability to mitigate the risk of data ex-filtration from Google Cloud services.

#### VPC vs Cloud VPN

While VPNs deal with workflow security problems, VPCs deal with the workload.  VPC peering is similar to site-to-site 
VPN, in that it allows communications between two otherwise isolated environments. The biggest difference between VPC 
peering and site-to-site VPN, however, is that no VPN connection is required.

#### Subnets

A subnet separates public and private resources in a VPC.  Subnets with private resources only allow connections from 
other subnets in your VPC.  Subnets with public resources allow public connections to the public resources, and 
communicate through other subnets to access back end resources.  Subnets are like post offices that collect ranges of 
IP addresses, and a subnet mask is the post office's address that serves as a proxy address for the resources contained 
in it.  

Subnets can also help distribute resources across multiple regions for higher availability.  

Default subnets are created for every region in your project.

If you need to restrict access to a subnet in a VPC, use firewall rules.

Suppose you have a VM in a subnet in a VPC in 1 region.  If you create a new subnet in the same VPC and region, VMs in 
that VPC + region can communicate with each other using private IP addresses, which is the most secure and efficient 
way to access applications running on the VMs.  If you want to access them both from the same private IP, you can use 
the IP from 1 instance as the endpoint, and it eliminates the need for any additional configuration, such as firewall
rules or VPNs. 

Subnets cannot have overlapping IP addresses.  When you create a new subnet, make sure it does not overlap with an 
existing range.  Also make sure any on premises IPs do not conflict with a VPC subnet range.  Resources in the same 
subnet can communicate.  

#### Classless Inter-Domain Routing (CIDR) Blocks

Resources in a network can use IP addresses within a given range.  That range is defined by a CIDR block.  A CIRD block 
consists of a starting IP address like 69.208.0.0 and a range like /28.  The range indicates how many bits (out of 32) 
are fixed.  So /28 means 28/32 bits are fixed.  This corresponds with 16 total IP addresses, meaning your CIDR block 
with a starting IP of 69.208.0.0 can go up to 69.208.0.15.  The math is: (32 - 28) = 4 flexible bits -> 2**4 = 16 
possible values.  

10.0.0.0/8 is the largest private IP address range and allows for over 16 million IP addresses. It is commonly used for 
private networks and is recommended by Google for VPCs.

#### Firewall Rules

Firewall rules are rules to control incoming (ingress) and outgoing (egress) traffic.  Each rule has a priority 
assigned to it from 0 (highest) to 64435 (lowest).  The default is 65535, which allows all egress and denies all 
ingress.

#### Network Address Translation (NAT)

NAT is a way to map multiple local private addresses to a public one before transferring the information.  In other 
words, it provides outbound access to the internet to devices without external IP addresses. Organizations that want 
multiple devices to employ a single IP address use NAT, as do most home routers.

Historically, a NAT worked as a proxy for all device communication to pass through before going out to the internet.  
The problem with this is that the NAT is a single point of failure.  Google Cloud NAT avoids this problem by ditching 
the NAT as a proxy and instead serves as a pass through for the devices: each device is mapped using its IP and a port.  
You would use cloud NAT to reduce the need for external IP addresses.  

A NAT is a good way to allow VMs to download the latest software from the internet, while not being exposed to the 
internet.  

#### Cloud VPN

Cloud VPN securely extends your peer network, i.e. on premise network, to Google's network (your VPC) through an IPsec 
VPN tunnel. Traffic is encrypted and travels between the two networks over the public internet. Cloud VPN is useful for 
low-volume data connections with < 3 Gbps, but you can add VPN endpoints to increase this, e.g. 2 endpoints at 3 Gbps = 
6 total Gbps.  If the customer wants to ensure that all network traffic between their virtual machine instances is 
encrypted, both in transit and at rest, use cloud VPN.  

There are 2 types of cloud VPN: 
* Classic
  * 1 external IP address
  * Static or dynamic routing
  * 99.9% available (you could implement > 1 VPN for higher availability, but this is not necessary with HA VPN)
* High Availability (HA)
  * 2 external IP addresses
  * Only dynamic routing
  * 99.99% available

While VPNs deal with workflow security problems, VPCs deal with the workload.  VPC peering is similar to site-to-site 
VPN, in that it allows communications between two otherwise isolated environments. The biggest difference between VPC 
peering and site-to-site VPN, however, is that no VPN connection is required for peering.

Cloud VPN is designed for low throughput.  If you need high throughput, consider Cloud Interconnect instead, which links 
your on premise network to Google.  A dedicated cloud interconnect is a direct physical connection to Google.  It is 
ideal for high data transfer and extremely low latency, like financial transactions.  Dedicated interconnect can only be 
used when there is a Google facility nearby.  If there is not, you can use another telecom provider's facility if they 
are nearby and have a direct connection to Google.  This is called partner interconnect.  

## Google Kubernetes Engine (GKE)

GKE is the container orchestration service that uses Kubernetes (K8s).  When you set up GKE, you can specify whether 
you want the cluster to be standard (you manage it) or autopilot (Google manages cluster level scaling).  You pay for 
nodes in a standard cluster and pods in the autopilot cluster.  Autopilot helps manage costs for you.  

A K8s cluster is a group of compute engine instances with a master node that manages the cluster and worker nodes to 
run workloads (pods).  Everything entered with the kubectl command is sent to the master node.  A master node consists 
of:
* API server that handles all communication for the cluster (inside and out)
* Scheduler that places containers on pods and terminates/starts new ones
* Control manager that manages deployments and replicasets to ensure they are healthy
* etcd that is a distributed database that stores the cluster state

K8s can have node pools.  A node pool is a group of VMs within a cluster that is designated for a type of workload.  
The default node pool created for regional Standard clusters consists of nine nodes (three per zone) spread evenly 
across 3 zones in a region.  So if you deploy a K8s cluster with x VM machines in the default zone, and leave the 
number of zones as the default, you end up with 3x total machines, spread over 3 zones in 1 region. If you want to add 
or remove nodes, you can do that with `gcloud cluster resize` command on the fly.

K8s clusters can be scaled in infrastructure (larger nodes or more nodes in the cluster) or in workload (larger pods or 
more pods on a node).  Pods can be scaled horizontally with horizontal pod autoscaler (HPA) manifest or vertical pod 
autoscaler (VPA) manifest.  K8s clusters are scaled using the `gcloud` CLI to add/remove nodes.  The `kubectl` CLI can 
only be used to edit pods resources within deployments.  If you need to add nodes to a node pool or cluster after 
deploying the K8s cluster, there is no way to modify it without cluster down time, so the best idea is to create a new 
cluster with a new node pool, redeploy to that cluster and remove the old one.

Nodes in K8s are compute engine VMs that run: kubelet, kube-proxy, and a container runtime like Docker.  Node pools are 
collections of nodes with the same configuration.  Pods are deployed to specific node pools using the nodeSelector field 
in the pod or deployment manifest. Pods have unique IP addresses, even if they are on the same node.  Deployments are 
sets of pods running replicas of a containerized application.  Deployments are used for stateless applications.  
StatefulSets are used for stateful applications.  Pods in stateful sets are not interchangeable.

Deployments represent a micro-service, with all its releases.  A deployment manages new releases to ensure 0 downtime.  
A replicaset ensures that a specific number of pods are running for a specific micro-service version.  Replicasets are 
versioned and the pods they generate are tied to that version.  So: deployments manage releases of replicasets and 
replicasets manage pods for that version.  If a pod goes down, the replicaset makes sure a new one is created.

Services are sets of pods with a network endpoint that can be used for discovery and load balancing.  Ingresses are 
collections of rules for routing external HTTP(S) traffic to services.  A service ensures that there are no disruptions 
when a pod fails and loses its IP address and another one with a new IP comes in to replace it.  Services identify sets 
of pods using label selectors.K8s assigns a service an IP address called a cluster IP by default.  Load balancers do 
the same thing, and you can actually create a K8s service with type = load balancer.  These are the service types:
* Cluster IP services are only reachable from within the cluster, unless you expose it to the public with an ingress or gateway
* NodePort services exposes your micro-service on a static port on the K8 cluster's worker nodes (pods)
* LoadBalancer services expose the service externally using the cloud provider's load balancer
Ingresses can also perform load balancing or SSL termination.  Every ingress requires an ingress controller, like 
nginx, that performs the routing as specified in the ingress rules.  If you use nginx as your ingress controller, it 
serves as a load balancer: [ingress-nginx](https://github.com/kubernetes/ingress-nginx/blob/main/README.md#readme) is 
an Ingress controller for Kubernetes using NGINX as a reverse proxy and load balancer.  K8s ingresses usually only 
expose HTTP(S) ports/endpoints to the public.  If you need to expose endpoints for other types of communication (TCP, 
UDP, etc.), you should consider using a service type of LoadBalancer or NodePort, instead of the default Cluster IP.  
The usual use case for an ingress is to user service type of cluster IP or NodePort, and use ingress nginx as 1 load 
balancer for balancing load on all of your microservices in the cluster.  (If you wanted each service to have its own 
load balancer, you would use service type LoadBalancer, but it can be counter-productive to have so many load 
balancers).  When you do cluster IP service (only accessible within the cluster) + ingress, you are essentially doing 
SSL termination, because outside traffic hits the ingress load balancer (nginx) and gets routed to the appropriate 
service, but at this point you are inside the cluster and can now communicate with the cluster IP.  So the service 
sends info back to the ingress load balancer, which sends it back to the client.  An ingress can redirect to multiple 
micro-services, so if you have a web app with many micro-services (shopping cart, inventory, user info, etc.) each one 
might have a service config, but you could make 1 ingress for all of them.

A DaemonSet object ensures that all (or some) nodes run a copy of a specific pod.  Example use cases are making sure 
pods are running logging or monitoring agents.  

If you need to access other GCP services from containerized apps in K8s, you should use workload identity for security, 
instead of an SA.  Workload Identity is the recommended way of accessing Google Cloud services from GKE because it 
provides improved security over service accounts.  Service accounts are authenticated with long-lived keys and are less 
secure than short-lived access tokens used by Workload Identity.

### IP Addresses in K8s

A cluster's VPC determines the IP addresses that are available to all K8s resources in the cluster.  Every node in the 
cluster has a pool of IP address pulled from the cluster's total available IP addresses.  The pool of IP addresses 
assigned to a node are distributed over the pods.  This is what limits the number of pods that a single node can handle.  
K8s in standard mode has a max of 110 pods/node with a /24 CIDR block.  K8s in autopilot mode has a max of 32 pods/node.  
Pod IP addresses are ephemeral and when a pod dies, its IP is up for grabs again.  When a new pod starts, it gets one 
of the available IP addresses from the pool of IP addresses assigned to its parent node.  

A K8s service manages pod IP addresses.  The service itself has its own IP address called the clusterIP, which is 
constant for the life of the service.  This is internal to the cluster, meaning any resources in the cluster can send 
requests to the service at the stable clusterIP.  You can create a service with a nodePort type instead of clusterIP, 
and this will allow clients (internal AND external resources) to send requests to the IP address of a node and the 
node's port.  Finally, the loadBalancer type service allows clients to send requests to an IP address of a load balancer 
like nginx, which has been configured in the cluster.  

### Pod Storage Options

Pods can store data in cloud storage, cloud SQL, cloud filestore, etc.  They can also store data on disk files in the 
container, but these are ephemeral with the life of the pod.  They can also store data on volumes.  A volume is a 
directory on a pod that is accessible to all containers running on that pod (tpyically there would only be 1 container 
per pod though).  Persistent volumes are not ephemeral and are managed by persistent volume claims (PVC).  

### Pod Health Checks

A readiness probe checks if a pod is ready to serve traffic.  A failed readiness probe will stop it from serving 
requests but will not shut down the pod.  

A liveness probe checks whether the pod is functioning at all.  A failed liveness probe will terminate the pod.  
Liveness probes do not wait for readiness probes, so you should use initialDelaySeconds to ensure it does not fail 
before the readiness probe.

## Disentangling Service Options

### Infrastructure as a Service (IAAS)

When you use a cloud provider's physical hardware and you manage the code, auto-scaling, OS upgrades, availability, etc.  
Example: Use a VM to deploy an app.

### Platform as a Service (PAAS)

When you use a cloud provider's platform to manage everything except the application code itself.  
Example:  Deploy to Google App Engine or Cloud Functions, VertexAI, managed DB service

## Docker Notes

Docker builds images in layers.  Every line in your docker file is a layer.  Layers should be ordered in terms of 
increasing changes, so your first layer (FROM base_image) should change least frequently.  This means your copy 
lines should follow that order too.  So you should first copy files that do not change often and that docker needs, 
followed by files that change more frequently.  If docker encounters a layer that already exists (it remembers that it 
has built the layer before) it will not rebuild the layer (unless you specify force rebuild).  To reduce docker build 
time, use as many layers as possible, or as many lines in the Docker file as possible.  

## Storage Options on Google Cloud

See the image at this link: [https://cloud.google.com/blog/topics/developers-practitioners/map-storage-options-google-cloud](https://cloud.google.com/blog/topics/developers-practitioners/map-storage-options-google-cloud)

The bottom line is you have 3 options:
1. Cloud storage bucket
   1. Used for storing any file type
   2. Accessible any time
   3. Use for media streaming, documents, images, backups, NOT for querying
2. Block storage volume (PersistentDisk)
   1. Used for storing VM image data
   2. Ephemeral when tied to a VM unless a snapshot backup is saved or a machine image is created
   3. Machine image saves image + volumes, custom image saves only software loaded on an image
3. File storage server (FileStore)
   1. Used for storing any file type
   2. Accessible any time
   3. Fully managed network file storage
   4. Use for media processing, ML, data analytics, app migrations

Data Lifecycle and the GCP Tools for Each Part:
* Ingest via batch or stream
  * Pub-sub, transfer service, transfer appliance, gsutil, bigquery, dataflow
* Store durably and cheaply
  * Cloud storage (object storage), cloud SQL or cloud spanner (relational), firestore or bigtable (noSQL), bigquery
* Process & analyze
  * Dataprep (clean + prep data as managed service), Dataflow (managed ETL), Dataproc (spark)
* Explore & visualize
  * BigQuery, VertexAI, Datalab, Cloud data studio (dashboards + viz)

Choose BigTable when you need to execute time series queries.  Choose BigQuery when you want to do complex ad hoc 
analysis on data. Choose Datastore when you need to make IoT data available to other apps.  Also choose BigTable and not 
Cloud Video Intelligence API for real time video analysis, because the Video Intelligence API cannot handle real time.  

A <em>data lake</em> is a single platform with solutions for data storage, management, and analytics.  It makes 
collecting, reporting, and visualizing big data easy and scalable.  BigQuery is kind of like this in the sense that 
querying (compute) and storage are separate.  You could also store data in cloud storage to serve as the storage 
component of your cloud data lake (this is preferred).  You can then use the services bulleted above, for each part of 
the data lifecycle, to create your cloud data lake.  

### Firestore

Datastore was Google managed MongoDB, a NoSQL document store.  Firestore is its replacement.  Firestore was originally 
a separate product optimized for real time NoSQL storage for mobile apps.  Now, there is Firestore in native mode that 
does what the original Firestore did, and Firestore in Datastore mode, which is backwards compatible with Datastore.  
Firestore in Datastore mode removes the limitation of eventual consistency that Datastore had.  Datastore mode is write 
optimized while Firestore (and Firestore in native mode) is read optimized.  Firestore (and native mode) can be accessed 
by the front end, while Firestore in Datastore mode requires backend access.  

### Database Concepts

An index on a column creates a b-tree to more efficiently search through the column.  A b-tree is NOT a binary tree, 
because a binary tree can have at most 2 children, whereas a b-tree can have > 2.  A b-tree breaks numbers up into 
ranges and creates a hierarchy, e.g. top node = 1-100, next layer has nodes 1-50 and 51-100, next layer has nodes 1-10, 
11-20, 21-30, etc.

Sharding is splitting a DB into chunks to make it run faster.  Sharding requires deciding how to split data, either by 
write order/age, timestamp, some other key, or using a consistent hashing function to balance loads on each shard.

Partitioning is splitting a single table into chunks to make it run faster. 

CAP theorem states that when partitioning occurs, the system cannot be both available and consistent.  If you have 
separate NoSQL instances for example, 1 may update a record before the others, making them inconsistent but available.  
If on the other hand you ensure constant communication, the instances become unavailable while making updates to copy 
the record that was just updated in the first instance.  So consistency means all nodes see the same data but may not be 
able to write, while availability means all nodes can write but may not see the same data.  CAP theorem mainly applies 
to DB writes, and is more of an issue with NoSQL than relational.  

Data serialization (what happens in DB) != request serialization (what happens with JSON)
De-serialization is the process of taking an object stored on disk or memory, and converting it to a data structure that 
can be sent to a server.  Serialization is the process of taking a data structure and converting it to an object that 
can be stored on disk or memory.  To avoid write collisions, you can send user write requests to a queue to process them, 
and a second service that processes the writes one by one.  This lowers throughput, but ensures data consistency by 
avoiding race conditions. 

#### ACID vs BASE

ACID DBs favor consistency over availability.  They are usually used for transactional data, where failure midway 
through a transaction has dire consequences, like in finance.  Being ACID means adding complexity and slowness, which 
is why relational DBs, which are usually ACID, have a limited number of connections.  They store a lot in memory to 
ensure atomicity, they require heavy IO to ensure durability, and they require a lot of CPU for consistency.  Nothing 
comes free.
* Atomicity = if error occurs before operation is committed, everything in the statement gets rolled back
* Consistency = data is validated before it is persisted, e.g. enforce no duplicate keys
* Isolation = no updates are seen by other users until the update is committed
* Durability = everything is saved to disk on commit

BASE DBs favor availability over consistency.  They are usually used for high performance apps with high throughput, 
like social network sites where it is more important for users to be able to read and make posts (availability) than it 
is for users to have the most current posts in their feed (consistency).
* Basically Available = the DB is in a good state most of the time and accepts requests
* Soft state = data can change between states and does not need to match in every replica
* Eventual consistency = if there are no new updates to data, all reads will eventually return the current value as updates are propagated through the nodes/replicas, but the current value is not immediately available

#### CAP Theorem

CAP theorem states that a distributed system can only have 2 of 3 characteristics at any given time: consistency, 
availability, and partition tolerance.  
* Consistency = reads from different nodes return the same value, appears as if all operations are atomic
* Availability = every request to the system receives an immediate response
* Partition Tolerance = when DB nodes are split into multiple groups that cannot communicate, the system continues to operate

When choosing a DB type, you must decide which of these 3 characteristics are most important for your application.  For 
example, if you need strong consistency, you probably need a relational DB and you must recognize that this will have 
higher latency, because writes will need to sync before being available.  If you need high availability and high write 
throughput, you might lean towards NoSQL, while recognizing that you will have eventual consistency.  

#### Command and Query Responsibility Segregation (CQRS)
Suppose you have buyers and sellers accessing the same DB.  Sellers try to update products and buyers try to add 
themselves as a buyer.  You could optimize the DB table for buyers to make querying faster, but this would slow it down 
for sellers.  A compromise is to separate queries and commands (CQ) into different tables for buyers (who query a 
products table) and sellers (who send commands to a product inventory table).  The products table can be optimized for 
buyer querying.  The product inventory table can be optimized for sellers.  Then you need a scheduled job that will make 
changes to the product table based on the product inventory table.  So the bottom line is that CQRS optimizes use of data 
by splitting different types of requests (reads and writes) into separate, individually optimized services.  The 
drawbacks are complexity and delay while the scheduled job operates (eventual consistency).  

CQRS uses 1 service for commands and another for queries, like a master node for writing and read replicas for querying.  
The 2 DBs (e.g. master node and read replicas) are essentially separate DBs.  You can take this a step further by 
implementing CQRS using an event store for commands.  An event store stores the initial state of every entity in a table 
and all updates in another table.  To get the current state, you add the updates to the initial state.  This makes it 
time intensive to get the current state, but makes writes extremely fast, because there are no updates or deletions; 
everything is an insert (think blockchain).  CQRS can use a separate read DB that stores entities (it replays the events 
from the event store for each entity to store current state for faster reads).  The drawback to CQRS with an event store 
is that the entities in the read DB may not be current, as they need to sync with the commands DB.  

You should consider using CQRS when access to historical data is of paramount importance.  You should also consider 
using it when performance is important, for either reads or writes.  Finance and healthcare are examples where event 
stores can be helpful.  

### Cloud Storage Buckets

Cloud storage is serverless, auto-scaled storage that allows only complete modification (not partial) of files.  If you 
need to update a file, add a new version.  Cloud storage uses a global namespace, because objects in it are globally 
accessible, possibly even from the internet (every object has a URL that must be unique globally).  

Buckets can be multi-regional for storing data that needs to be accessed frequently from anywhere in the world with low 
latency.  Chose multi-regional instead of creating 1 bucket per region.  Buckets can also be regional with replication 
across zones in the region.  Only multi-region has auto-failover in the case of data loss though.

Storage transfer service (STS) is used to move files to cloud storage only.  STS can move from on-premise to cloud if 
bandwidth is fast enough, between cloud providers, and it can be a recurring or 1 time transfer. If you need to transfer 
very large amounts of data to cloud, apply for a transfer appliance because online transfers will take too long (years).  
Google will send you a device with a capacity up to 300 TB to ship back to them.  If you only need to upload a handful 
of small files, use the gsutil CLI.  To upload a file to a bucket with gsutil: 
`gsutil cp FILE_NAME.csv gs://BUCKET_NAME/FILE_NAME.csv`

Helpful commands for gsutil:
* `-m` parallel/multithread upload for speed
* `-c` continue copying if connection is interrupted
* `-o` additional options

Bucket storage classes:
* Standard
  * Min storage duration = None
  * Use for frequently used data or data to be stored temporarily
* Nearline
  * Min storage duration = 30 days
  * Use for data to be accessed 1x per month
* Coldline
  * Min storage duration = 90 days
  * Use for data to be accessed 1x per 3 months
* Archive
  * Min storage duration = 365 days
  * Use for data to be accessed 1x per year

Lifecycle management can be used to change object storage classes or delete objects after set time periods.  You can 
only change storage class from a higher class to a less frequently accessed class.  You can also create a retention 
policy for compliance/regulatory reasons, and it will prevent changing/deleting the object or the bucket in which it 
resides, until the retention period has been met.  Retention periods can be locked from editing too.  

Fixed-key metadata can set caching values for objects (max time 3600 seconds) and the filename for when users download 
the file.

Cloud storage encryption is automatic and uses Google managed keys by default, but you can also use customer managed 
keys using Cloud Key Management Service (CKMS) or customer supplied keys using keys created and managed by the customer.  

You can time limit read/write access to objects using a signed URL.  Signed URLs can be sent to anyone on the open 
internet.  Signed URLs should be created with a user managed SA, not the default bucket SA, because the bucket SA could 
have more permissions than are required.

If you need someone to have longer, persistent bucket access beyond a single file, you can use IAM roles to give them 
broader storage access to all objects in a bucket.  If permission should be limited to certain files in the bucket, 
give them access using an access control list (ACL). ACLs are fine-grained for specific items in a bucket and are not 
recommended unless there is a good use case (IAM is preferred).  If you do not control the upload process to a bucket 
(somebody else or some other org does), you want to limit what can be uploaded to your bucket using restrictions for 
size, file type, or other attributes, that can be configured as a Signed Policy Document.  

Storage best practices:
* Use exponential backoff rates if your users see 500 server errors or 429 access errors (1, 2, 4, 8, 16 seconds)
* Do not use sensitive data, sequential numbers or timestamps in object names
* Use random object names (use metadata to handle download filename, labels, and type)
* Store data in the region closest to users
* Use cloud storage FUSE to enable file system access to cloud storage, or to mount buckets to Linux or Mac file systems

Example1: you have to access data for 30 days, then never again, but you need to retain the data for 4 years, what do 
you do?  Use standard initial storage class with a lifecycle policy to move to archive after 30 days and add a retention 
policy for 4 years.
Example2: you need to transfer 2 TB data from Azure to GCP: use cloud transfer service (not gsutil)
Example3: you need to transfer 40 TB data from on premises to GCP: use transfer appliance
Example4: you need a bucket for website files: create a bucket with the same name as the website (bucket name = DNS name) and give view access to all users (including public)

## Identity and Access Management (IAM)

IAM helps you manage access to cloud objects for both human an non-human users.  

Authentication = is it the right user?
Authorization = does the user have the right to access?

Member = who or what is getting identity managed
Resource = what thing in cloud a member is trying to use
Action = what a member is trying to do to a resource
Roles = sets of permissions to perform actions on resources (roles do NOT know about members - they are only rules)
Policy = binding a role to a member

If you need to provide access to something for someone, the steps are:
1. Identify the role with the right permissions
2. Assign that role to a member (set a policy)

Best practices:
* Assign users to groups -> do not give a user permission, give the group permission
* Assign roles to groups -> do not give a user permission, give the group permission
* Assign roles based on least privilege -> a group only needs the minimum permission to perform certain actions
* Never use basic roles, go with pre-defined roles first and use custom only when you must
* Never use a user account to run actions, use a SA instead
* Use workload identity federation to manage SA's -> no need to store SA creds if you have federated identity verification with okta, jump cloud, etc.
* Assign policies to the right level of the resource hierarchy
* Use cloud audit logs to monitor changes to IAM policies and export the logs from cloud logging (ends after 30 days) to cloud storage
* Limit access to audit logs

Workload identity federation makes it possible to give a AWS user access to a Google resource.

An identity aware proxy makes it possible for a remote worker to access GCP resources using IAM credentials.

### Roles

3 basic roles:
1. Viewer = read only 
2. Editor = read + edit
3. Owner = read + edit + manage roles & permissions + billing

Do NOT use basic roles in production, as they will be too broad.  Use predefined roles instead, as they are more fine 
grained.  Examples: storage admin, storage object admin, storage object viewer, storage object creator

### Service Accounts

A service account is a type of member.  You would use it if an application needs access to something in cloud.  You 
would not use a user account - you need a generic non-human account instead.  That is a service account.  

SAs do not have passwords but private/public keys instead.  They are identified by email address.  Many services have 
defaults SAs that are created when an API is enabled.  It is not recommended to use these, because they have too many 
permissions, but custom SAs instead.  You can grant users access to a SA if they need to perform actions as the SA.  
Thus, a SA is both an identity and a role (it can both identify who/what is performing an action and determine the rules 
or permissions for performing actions on resources).

Federation is possible, so that you can have GCP users authenticate with an external service to gain GCP access.

### Access Control Lists (ACLs)

ACS defines who has access to buckets and objects and what level of access they have.  It is different from IAM because 
IAM permissions apply to all objects within a bucket and ACLs customize access to specific objects in a bucket.  Thus, 
a user can access objects in a bucket if they have either IAM or ACL.  Therefore, the recommendation is to use IAM for 
common permissions to all objects and ACLs if you need to customize access for certain objects.  

If you want a user to access an object for a limited time (even without a Google account), you can create a signed URL.  
Steps to create a signed URL:
1. Create a key for a SA or user with the desired permissions
2. Create a signed URL with the key: `gsutil signurl -d 10m YOUR_KEY gs://BUCKET/OBJECT`

### Cloud Key Management Service (KMS) 

KMS is a fully managed service that allows you to encrypt data at rest with your own encryption keys. By using Cloud 
KMS, you can encrypt sensitive data stored in GCP and manage your own encryption keys without the operational overhead 
of managing your own key management system.

Google default encryption, on the other hand, is a feature that encrypts data by default using a unique encryption key 
created by Google, and is useful for preventing unauthorized access to data in the event of a data breach. However, if 
you need to control the encryption keys and have the ability to rotate, revoke or manage access to them, then you 
should use Cloud KMS.

### SSH'ing Into VMs

You can add SSH public keys to compute engine's metadata management section on the left side of the console, or you can 
manage many users across projects by linking your OS (Linux) account to your Google identity by enabling OS login in 
metadata: `gcloud compute PROJECT_ID/INSTANCES add-metadata --metadata enable-oslogin=TRUE`.  Users must have roles 
compute.osLogin or compute.osAdminLogin assigned in order for OS login to work.  You can also upload your public SSH 
keys to OS Login: `gcloud compute os-login ssh-keys add`, if you have custom SSH keys (like one you created for GitHub).

In cloud shell, the default execution path is `~/bin` and anything stored there persists between connections.  

### GCP Data Loss Prevention API

The Data Loss Prevention API is designed to keep some data private and secure.  It is able to discover and auto identify 
PII, credentials, secrets, and country specific identifiers like SSNs and passport numbers.  Data can be auto-masked 
with cryptographic functions.  The API can also calculate the risk of masked data being inferred from other attributes.  

Cloud Armor is a service that protects against level 7 (HTTP) attacks, like DDoS.  

## Database Management

For max availability and data durability (you do not lose data and have little down time), you can create a synchronous 
copy of a DB in another region than your data center.  The synchronous copy has periodic snapshots for additional 
protection.  This is costly of course, so you can have hot, warm, or cold starts for the copy (hot is always on, warm 
is up and ready for a few minutes of down time, cold is ready in an hour of down time or just a DB snapshot).

For analytics, you can create read replicas of your DBs to prevent analytics for slowing down the DB.  The replica will 
have eventual consistency, because it is asynchronously updated.

Use eventual consistency when scalability is more important than integrity, e.g. social media posts.

### Database Types

SQL DBs
* Cloud SQL = Managed Postgres (TB scale)
* Cloud Spanner (PB scale, globally and horizontally distributed)

NoSQL DBs
* BigTable (pure NoSQL, more like IaaS bc requires cluster config, ATOMIC in 1 row only -> no transactional support, charge by node, faster than DataStore, single zone)
  * Compared to DataStore: Better for writes, analysis on NoSQL data, higher throughput for IoT, if BigTable is the wheel then DataStore is the car
* DataStore = Managed MongoDB (document key-value store, high performance, multi-zone -> highly available, ATOMIC transactional support, allows GQL like queries but not SQL, costly but charged by read/write)
* FireStore (DataStore lite, small docs like JSON files, offline support -> mobile friendly, serverless, good for startups at small scale), support GQL not SQL

Data Warehouse for SQL + NoSQL
* BigQuery (use for batch processing NoSQL - if you have NoSQL with real time data, use BigTable for analysis)

#### Database vs Data Warehouse vs Data Lake

Database = storage for data, records data and allows it to be read, uses schema on write

Data warehouse = stores structured data from many sources for the purpose of analysis, commonly contain data from ETL 
processes, mainly used for generating reports and BI, not intended to be used for queries, transactions, or to serve 
requests, uses schema on write

Data lake = stores any type of data in raw, original form, inexpensive, mean to hold data from upstream sources, 
consumers of a data lake use schema on read approaches where format is applied to the data when it is queried

#### Relational

Used for online transactional processing (OLTP) and online analytics processing (OLAP)

1. OLTP = large number of users making small transactions (read/write/delete), e.g. banking, e-commerce 
   1. Uses row storage (change 1 row at a time), good for small transactions 
2. OLAP = when you run a lot of standard queries, e.g. BI, insurance premium analysis
   1. Uses column storage (change 1 column at a time), good for compressing data to store a lot of it and distributing it over nodes, which makes querying more efficient

Relational DBs have predefined schemas and relationships.

GCP Products for relational DBs:
* BigQuery is a managed data warehouse that works with relational + NoSQL and is great for analytics (OLAP)
* Cloud SQL has all major SQL DB types, except Oracle, that scale to TB of data, it has auto-replication for availability and disaster recovery, automated backups & encryption
* Cloud Spanner is a globally distributed SQL DB that scales to PB of data and can be used for disaster recovery

Cloud SQL is a fully managed relational database service that provides high availability, scalability, and security features. It 
supports encryption at rest and in-transit and is compliant with industry regulations such as HIPAA and PCI DSS. Cloud 
SQL is a suitable choice for a financial services company that needs to store sensitive financial information.  Cloud 
SQL is different from BigQuery in that BigQuery is a managed data warehouse instead of a DB.  Cloud SQL is different 
from Cloud Spanner in that Cloud Spanner is horizontally distributed and scales bigger.  Cloud SQL is limited to regional 
availability and the zones within 1 region.  Multi-region is available for cloud SQL backups only.  It is also limited 
to 30 TB in size (use cloud spanner if you need > 30 TB). 

High Availability (HA) is the recommended configuration for critical data in Cloud SQL. It provides a failover replica 
in another zone in the same region to ensure data protection in the event of a zone outage. With HA, Cloud SQL 
automatically replicates data to a standby replica in a different zone within the same region. If there is a zone 
failure, Cloud SQL automatically fails over to the standby replica, ensuring that your application remains available.

#### NoSQL

Used for document centric data, massive scale, rapid prototyping (no schema building).  

NoSQL DBs have flexible schemas that evolve over time, and is therefore easier to scale to PB of data with millions of 
transactions per second.  NoSQL DBs have different types:
1. key-value
   1. Frequent, small reads and writes
   2. Redis is example
2. document store
   1. key-value pair = document and groups of documents = collection
   2. Allow arbitrary complexity where not every document needs to have the same keys, and documents can be embedded infinitely 
   3. Writes typically insert new whole documents
   4. Better for app storage since you can insert data faster
   5. Think JSON structured data
   6. MongoDB (consistency + partition), CouchDB (availability + partition) are examples
3. column-oriented
   1. Allows at most 1 or 2 level complexity in a document (no docs nested/embedded many layers deep)
   2. Columns themselves are key-value pairs and do not need to be pre-defined
   3. Writes typically insert new columns (key-value pairs) for a row -> writes are slow but reads + analytics on specific columns are fast
   4. Better for analytics since you can read & analyze individual columns
   5. Each row can have arbitrary columns, i.e. key-value pairs
   6. Cassandra (availability + partition), Vertica (consistency + availability), HBase are examples
4. graph
   1. Stores graph structured data (nodes + edges)

GCP Products for NoSQL DBs:
* BigQuery works with relational + NoSQL and is great for analytics (OLAP)
* Cloud Firestore (datastore) allows ACID transactions and graph query language (GQL) queries, 0 - few TB, does not support SQL
* Cloud BigTable is a managed, non-serverless, NoSQL wide column DB, 10 TB+, but not recommended for multi-row transactional workloads

BigTable is recommended for storing IoT device streaming data and huge streams of time series data.  In Bigtable, you 
can separate the workload of read and write operations by creating two different clusters within the same Bigtable 
instance. One cluster can be optimized for read-heavy workloads, while the other can be optimized for write-heavy 
workloads. This approach can help to minimize operational load because it allows you to distribute the workload across 
different nodes, which can help to reduce contention and improve performance. Additionally, you can use Bigtable 
replication to keep the clusters synchronized, which simplifies the management of the clusters and ensures consistency 
of the data between the two clusters.

#### In-Memory

Used for rapid retrieval, e.g. caching, session management, leader boards

GCP Products for In-Memory DBs:
* Memorystore (Redis or Memcache)
  * Memcache can store up to 5 Tb
  * Redis can store up to 300 Gb

It is not recommended to use sequential numbers or timestamps in keys.

Caching services are designed to store frequently-accessed data to improve application performance. They are not 
intended to handle spikes in data volume and are not a reliable mechanism for storing large volumes of data.  If you 
need that, or if your app is receiving more data that it can process, use Pub-Sub or a message queue instead.

### Data Modeling with SQL and NoSQL DBs

Table (relational DB) = Collection (noSQL)

Relational DBs are usually associated with analysis with OLTP and OLAP, business intelligence, and reporting.  NoSQL DBs 
are usually associated with real time analytics, logging, event based and IoT data (because they're often key-value 
type), recommendation engines and news feeds (because they're often graph type), high throughput messaging, and video 
and photo sharing.  

In a relational DB, you might have tables for playlist, artist, and song.  The playlist table would need a separate 
table to pair playlist ID to song ID.  A NoSQL DB could store the list of songs in the playlist in the playlist table.  
```
# example of a key-value entry in a collection
{
   "playlist_id": long,
   "created_timestamp": timestamp,
   "playlist_name": string,
   "user_id": long,
   "songs": [{"song_id": long, "title": string}]
}
```
The example above uses an embedded schema, because one entity (song) is embedded in another entity (playlist).  Embedded 
schemas improve query performance while sacrificing write performance, because updates to song have to iterate over the 
embedded key-value pairs to update each one, for each playlist.  Embedded schemas are ok to use when you want to favor 
read performance and the cardinality of the embedded elements is 1:few (if < 100 songs can be in a playlist).  

When designing databases, you usually create a data model.  There are 3 types of data models:
1. Conceptual - high level model that shows basic table or collection relations
2. Logical - more specific model that outlines entities, attributes, and how tables or collections are linked
3. Physical - detailed model that includes specifics about data structure (data type and primary/foreign keys), and relationship types (one to one, one to many, etc.)

Data models for relational DBs can be normalized or denormalized.  Normalization means storing data in non-redundant 
schemas to optimize write operations and results in less storage space.  A normalized schema requires many joins to 
combine data from different entities.  Denormalization allows redundancy to optimize read performance at the cost of 
write speed. Example:
* Normalized schema has a user table and a playlist table.  Playlist table has user_id field that can be joined with the user table to bring in user info
* Denormalized schema has user table and a playlist table, but the playlist table has user_id and other commonly used user data
Denormalization is useful for creating views and data marts that can be used for analytics, while normalization is 
useful for base tables that an application frequently writes to.  NoSQL DBs are more frequently denormalized than SQL.

## Cloud Migration with Cloud Migration Service

Phase 1 = identify the workloads you want to migrate and when
Phase 2 = plan the foundation; the network VPC, or hierarchy, IAM groups and roles
Phase 3 = deploy workloads to cloud, migrate data first and then move apps
Phase 4 = optimize environments in cloud by enabling logging, monitoring, auto-scaling, etc.

You have a few options to move applications.  One is simply to re-host them.  Another is to re-platform or make 
adjustments to make your app suit the cloud, like containerizing.  You can re-purchase or re-factor your app by making 
it serverless for example, or buying a new DB, but these are the most costly options.  You can also simply retire old 
apps.  

When migrating an application to the cloud, there are several strategies to consider. The "lift and shift" strategy 
involves moving the application as-is to the cloud without making any changes. While this strategy can be quick and 
easy, it may not take advantage of cloud-native features and may result in inefficient use of cloud resources.  To 
implement a lift and shift strategy, you would create compute instance VMs, set up images, and copy what you have 
already running on premise.  

The "rebuild" strategy involves rebuilding the application from scratch in the cloud, which allows the company to take 
full advantage of cloud-native features but can be time-consuming and costly.  This strategy may also be called "rip 
and rebuild" or "remove and replace".

The "refactor" strategy involves making changes to the application to optimize it for the cloud environment. This 
strategy is often the most appropriate for applications with a monolithic architecture as it allows the company to break 
the application down into smaller, more scalable components that can take advantage of cloud-native features like 
autoscaling and load balancing. This strategy also allows the company to optimize costs by only paying for the resources 
they need.  This strategy may also be called "improve and move".  An example is containerizing an app before moving it 
to Kubernetes.

Database Migration Service can be used to perform data migration from on premises DB to cloud DB with minimal downtime.
Storage transfer service (STS) is the same idea but for Cloud Storage.

Example: moving MS SQL server to GCP

You know that Cloud SQL for SQL server is fully managed, so you choose that as your replacement.  The next step is to 
create a Cloud SQL instance.  Then backup/copy/transfer your data to cloud storage.  Import data from cloud storage to 
cloud SQL and validate the imported data.  

Example: moving an app to GCP by containerizing

Choose your deployment option: app engine, GKE, cloud run.  Move the app data, and then deploy the containerized app.  

### Cloud Eumulators

You can emulate GCP cloud environments:
* BitTable
* DataStore
* FireStore
* PubSub
* Spanner

These emulators can help you with local development, allowing you to develop cloud apps locally.

# CI, CD Notes

CICD is part of the Agile methodology of delivering working software fast and iterating.  

GCP offers Cloud Deployment Manager, which is managed Terraform and allows infrastructure to be specified as code, 
following SRE best practices.  

## Continuous Integration

Continuously run your tests, linting, and packaging as you commit code.

## Continuous Deployment

Continuously deploy to test environments.

## Continuous Delivery

Continuously deploy to production.  

## Infrastructure as Code

YAML config files to manage infrastructure is recommended because code can be versioned, tracked, etc.  This makes 
everything repeatable and transparent.  

GCP's Cloud Deployment Manager is a tool to help you manage CICD pipelines.  You specify all of your resources 
(VPC, subnet, DBs, etc.) in YAML files (Jinja or Python), and Deployment Manager takes care of everything, including 
the ability to rollback on errors and version control.  Deployment manager is like Google managed Terraform; it follows 
the infrastructure as code paradigm and lets you spin up a bunch of resources and environments.  

## Site Reliability Engineering (SRE)

Google's version of DevOps.  SRE teams focus on every aspect of an application, from availability to latency, 
performance, monitoring, capacity planning, and beyond.  All of these things are managed by service level objectives 
(SLOs).    

Key Principles of SRE:
* Minimize manual effort wherever possible
* Move fast by reducing the cost of failure
* Share ownership of DevOps with developers

Total cost of ownership = 
+ licensing cost
+ computing cost
+ storage cost
+ networking cost
+ personnel cost
+ other costs, like penalties for missing SLA

GCP offers sustained use discounts for when you use compute resources for a long time period during the monthly billing 
cycle, and committed use discounts for when you know how much time you will need to use compute resources.  

### Service Level Indicator (SLI)

An SLI is a quantitative measure of an aspect of a service, e.g. 99.99% available, 100 records per second throughput, 
type I error rate of 2%, etc.  

When you take an SLI and add a target, you get a service level objective.

### Service Level Objective (SLO)

SLO = SLI + target

Example: I want 99.99% availability, or I want a 99th percentile response time of 1 second.

When you take an SLO and add a contract with the customer, you get a service level agreement.  

You should avoid copying GCP's SLO as your own, even if your service is hosted in GCP.  E.g. if you need SLOs for 
availability, create a couple like 99% availability as measured in 200 responses and 99% responses in < 100 ms.  

### Service Level Agreement (SLA)

SLA = SLO + contract (consequences)

SLA describes what happens if you fail to guarantee service with certain metrics to the customer.  

Ideally you want to have stricter internal SLOs than external SLAs.  

### Error Budget

Another idea for measuring a team's ability to meet SLOs is to use an error budget.  The error budget = 1005% - SLO.  
It is used to manage development velocity.  So if a team is failing to meet their error budget, they are forbidden from 
releasing continuously until they fix the problem.  

### Data Recovery

Data recovery is organized into:
* Recovery Time Objective (RTO) = how long will it take to restore data?
* Recovery Point Objective (RPO) = how recent will the state of the data be, when it is restored?  

Cloud SQL and Cloud Storage are good options for disaster recovery storage, as they will help with RTO.  Adding a 
persistent disk will help with RPO, as it will help ensure the recency of state when recovered.  

### Deployment Approaches

There are many options for deploying versions of an app.  

One approach is to replace v1 with v2 by simply terminating v1 and rolling out v2.  This causes down time during the 
release, and it means the rollback needs a new deployment, causing more down time.  In short, it is cost effective and 
fast, but disruptive.  

Another approach is to roll out v2 to a subset of instances, and once testing is finished, roll v2 out to the remaining 
instances.  This approach is fast, casues 0 down time, requires no extra infrastructure, minimizes impact to users, but 
requires v2 to be backwards compatible with v1.  This approach is often used for A/B testing.  Canary approach.

Another approach is rolling deployment, which is the same as deploying v2 to a subset of instances, but the subset 
grows over time.  This is a slow approach.

Another approach is blue green deployment, where you create a whole new infrastructure set for v2 (a parallel 
environment), and then switch all traffic from v1 to v2, then remove v1 environment.  This approach is instant, 
requires 0 downtime, has easy rollback, zero reduction in capacity, but requires additional infrastructure during the 
release.  

Another approach is shadowing, which is the same as v2, but you send the same traffic to both v1 and v2.  This gives 
the same benefits as blue green, but also allows you to test v2 with prod data.  The drawback here is additional 
infrastructure and code complexity (you would want to avoid double payments for example).

# Hadoop Big Data Notes

The idea behind big data is a distributed cluster with many nodes, where data is stored and processed on the individual 
nodes.  Hadoop is a methodology for distributed data processing.  

Partition tolerance from CAP theorem is required with big data, so you really can only choose between consistency and 
availability for big data DBs.    

## Hadoop Distributed File Store (HDFS)

HDFS is the storage part of Hadoop, where file storage is distributed among cluster nodes.  HDFS is fault tolerant for 
data failure and can repair files that get lost. 

HDFS splits files into 128 Mb blocks that are stored across many nodes.  Blocks are stored redudantly for DB resiliency.  
HDFS has a single name node that tracks where blocks are stored, and many data nodes that store the blocks.  The name 
node has an edit log to track where things are and whether there are changes.  Name nodes have limits, so if you have 
too many files for 1 name node, you can have many that are assigned namespace volumes.  Name nodes can be duplicated or 
backed up to NFS to prevent down time on a cluster if the name node goes down.  

It is important to remember that in Hadoop based big data setups, data is actually stored in HDFS.  NoSQL DBs built on 
top may pull the data into their own structures, or may just create pointers.  You would use NoSQL DBs if you need 
real time analysis or frequent reads on HDFS stored data.  If your goal is to do offline analysis with no urgency, you 
do not need a NoSQL DB at all - just store the data in HDFS and run it through Spark.  

## Yet Another Resource Negotiator (YARN)

YARN sits on top of HDFS.  YARN manages computing resources, assigning tasks to available nodes.  YARN is a compute 
layer, as opposed to HDFs, which is a data layer.  

## MapReduce

MapReduce is built on top of YARN.  MapReduce is a programming model that allows you to process data across a cluster.  
It consists of mappers and reducers, which are different functions that you can define.  Mappers transform data and 
reducers aggregate it from all of the nodes.  

In order to program gradient descent type optimization in MapReduce, the parameters of the target function would have 
to be mapped to every node that holds the dataset.  The error would be computed at each node and then get reduced.  
After reduction, the parameters would be updated and fed into the next MapReduce job. This is done by chaining the 
error computation and update jobs together; however, on each job the data would have to be read from disk and the 
errors written back to it, causing significant I/O-related delay.  This is why MapReduce is slower than Spark 
(in-memory + DAG) for machine learning.  

## Pig and Hive

Pig and Hive are built on top of MapReduce.  If you do not want to write raw mappers and reducers with Java, you can use 
a scripting language like Pig or Hive, which translate instructions into map/reduce functions.  Pig and Hive are high 
level, SQL-like queries.  Pig and Hive work with relational data.

Hive has high latency because it translates SQL into map-reduce jobs, so it is not appropriate for OLTP.  Hive is mainly 
used for OLAP with relational data.  Hive stores data in a de-normalized state.  Hive uses a schema on read approach, 
meaning it reads the unstructured file data (data stored in HDFS) and imparts a schema that is defined by your query.  

## Spark

Spark if built on top of YARN (same level as MapReduce).  Spark lets you write map/reduce instructions with Python, R, 
Scala, etc.  Spark can handle SQL-like queries or perform machine learning tasks over the cluster.  It can also handle 
real time data streaming.  Spark is in-memory, meaning it stores data in the RAM of the servers in the cluster, allowing 
it to run faster than Hadoop native tools like MapReduce (and tools built on top of MapReduce, like Pig and Hive).  

Instead of a programming model that only supports map and reduce, the Spark API has many other powerful distributed 
abstractions similarly related to functional programming, including sample, filter, join, and collect, to name a few.

SparkContext is what your driver program uses to create RDDs.  

### Resilient Distributed Datasets (RDDs)

Spark primarily achieves its speed via a new data model called resilient distributed datasets (RDDs) that are stored in 
memory while being computed upon, thus eliminating expensive intermediate disk writes that plague MapReduce. It also 
takes advantage of a directed acyclic graph (DAG) execution engine that can optimize computation, particularly iterative 
computation, which is essential for data theoretic tasks such as optimization and machine learning. These speed gains 
allow Spark to be accessed in an interactive fashion (as though you were sitting at the Python interpreter), making the 
user an integral part of computation and allowing for data exploration of big datasets.  

As mentioned, Spark uses resilient distributes datasets (RDDs).  RDDs are a programming abstraction that represents a 
read-only collection of objects that are partitioned across a set of machines. RDDs can be rebuilt from a lineage 
(and are therefore fault tolerant), are accessed via parallel operations, can be read from and written to distributed 
storages (e.g., HDFS or S3), and most importantly, can be cached in the memory of worker nodes for immediate reuse.  
RDDs are immutable, and transformations are carried out in order. If a dataset is too large to fit in memory, the RDDs 
can be re-partitioned.  When a Spark job runs, it typically runs on a partition at a time, and cycles through, so only 1 
partition is actually in-memory at any time.  If a single partition is too large for memory, Spark can keep some on the 
disk.  Otherwise, suppose you have 1 TB of data and nodes with 64 GB RAM each, Spark will partition the 1 TB RDD into 
as many partitions as it takes to meet each node's RAM limit.  

There are two types of operations that can be applied to RDDs: transformations and actions. Transformations are 
operations that are applied to an existing RDD to create a new RDD—for example, applying a filter operation on an RDD 
to generate a smaller RDD of filtered values. Actions, however, are operations that actually return a result back to 
the Spark driver program—resulting in a coordination or aggregation of all partitions in an RDD. In this model, map is 
a transformation, because a function is passed to every object stored in the RDD and the output of that function maps 
to a new RDD. On the other hand, an aggregation like reduce is an action, because reduce requires the RDD to be 
repartitioned (according to a key) and some aggregate value like sum or mean computed and returned. Most actions in 
Spark are designed solely for the purpose of output—to return a single value or a small list of values, or to write 
data back to distributed storage.

An additional benefit of Spark is that it applies transformations “lazily”—inspecting a complete sequence of 
transformations and an action before executing them by submitting a job to the cluster. This lazy-execution provides 
significant storage and computation optimizations, as it allows Spark to build up a lineage of the data and evaluate 
the complete transformation chain in order to compute upon only the data needed for a result; for example, if you run 
the first() action on an RDD, Spark will avoid reading the entire dataset and return just the first matching line.

#### RDD Transformations and Actions

Transformations = map function from map reduce; they take one RDD and turn it into another
Actions = reduce function from map reduce; they aggregate 

Spark does not run anything until an action is called (lazy evaluation), and then it runs all transformations in the 
DAG before performing an action.  

These functions apply transformations to RDDs:
* Map = 1:1 relationship of input row of old RDD to output row of new RDD
* Flat Map = 1:many relationship of input row of old RDD to output row(s) of new RDD
* Filter = removes rows from RDD based on criteria (like a lambda function)
* Distinct = de-duplicate rows
* Sample = draw a sample of rows
* Union, Intersection, Subtract, Cartesian = combine RDDs
Examples:
```
rdd = sc.parallelize([1,2,3,4])
squared_rdd = rdd.map(lambda x: x*x)
```

These functions apply actions to RDDs:
* collect = take RDD from memory and return an object
* count = counts rows in the RDD
* county by value = count rows in the RDD by value group
* take/top = get the top few rows of RDD
* reduce = use a function to combine values with each unique key

#### Spark DataFrames

DataFrames are extensions of RDDs for structured data.  DataFrames contain row objects, allow SQL queries, read/write to 
JSON, Hive, and parquet formats, and communicate with JDBC, Tableau, and others.  A spark DataFrame can be operated on, 
in many the same ways as a Pandas dataframe.  

A DataFrame is really a DataSet of row objects under the hood.  

### Interactive Spark with Pyspark

There are 2 ways you can use Python with Spark: interactive with Pyspark, and submitting python script jobs to Spark.  
The typical route is to develop on a subset of the data in Jupyter with Pyspark, then make a script to submit as a 
Spark job to run on the whole dataset.  

Pyspark is an interactive shell implemented by a Python REPL (read-evaluate-print loop).  It allows you to interact with 
data on a Hadoop cluster as an RDD.  All interactive Spark shells create a spark context, sc, automatically.  You can 
wrap this sc in another context, like Hive `HiveContext(sc)`, or use it to load data from files `sc.textFile()` or other 
sources like Cassandra, ElasticSearch, JSON, Kafka, etc.  

### Submitting Python Jobs to Spark

There are 2 ways you can use Python with Spark: interactive with Pyspark, and submitting python script jobs to Spark.
The typical route is to develop on a subset of the data in Jupyter with Pyspark, then make a script to submit as a 
Spark job to run on the whole dataset.  

Writing Spark applications in Python is similar to working with Spark in the interactive console because the API is 
the same. However, instead of typing commands into an interactive shell, you need to create a complete, executable 
driver program to submit to the cluster. This involves a few housekeeping tasks that were automatically taken care of 
in pyspark, like getting access to the SparkContext, which was automatically loaded by the shell.

Here is an example script:
```
## Spark Application - execute with spark-submit

## Imports
from pyspark import SparkConf, SparkContext

## Shared variables and data
APP_NAME = "My Spark Application"

## Closure functions

## Main functionality
def main(sc):
    """
    Describe RDD transformations and actions here.
    """
    pass

if __name__ == "__main__":
    # Configure Spark
    conf = SparkConf().setAppName(APP_NAME)
    conf = conf.setMaster("local[*]")
    sc   = SparkContext(conf=conf)

    # Execute main functionality
    main(sc)
```

## Apache Storm

Storm lets you process streaming data (it's an alternative to Spark streaming).  

## ZooKeeper

ZooKeeper helps you coordinate everything on your Hadoop cluster.  It tracks which nodes are up, which are down, shared 
states across the cluster, etc.  Basically, ZooKeeper acts like K8s' deployment, as a resource manager.  It tracks 
which nodes are the master nodes, what tasks are assigned to which workers, and which nodes are available to do work.  

ZooKeeper manages cluster level resources, whereas YARN just manages resources for workloads.  

## Zeppelin

Zeppelin is like Jupyter for Hadoop.  It has plugins for all types of things, from wide column DBs to Spark, Hive, and 
Pig APIs.  It provides visualization capabilities for Spark.  

## Wide Column Databases

Wide column DBs are NoSQL DBs that support high frequency, low latency writes.  Data is stored in rows, meaning each 
row must have a key.  There are no foreign keys or joins in wide column DBs.  Row keys determine where data is written.  
Row keys determine which node in the distributed data store a row of data is written.  This means your row keys should 
be evenly distributed, so you should avoid linearly incrementing row keys and use low cardinality attributes in the key.  

Tables in wide column DBs have 1 index based on the row key.  Operations are atomic at the row level.  Related entities 
should be stored in adjacent rows and therefore have similar row keys, because rows are sorted by row key.  This 
improves read efficiency.  

Wide column DBs use eventual consistency.  BigTable is a managed wide column DB and it has a strong consistency option.  
The name "BigTable" is appropriate for wide column DBs because they store data in a way that make bigger tables 
preferable to smaller tables.  Small tables require a lot of reads.  

Time series use cases are good for wide column DBs.  You might have row keys like `us-west1#3698#2021-03-05-1200` and 
`us-west1#3698#2021-03-05-1201`.  You can use new rows for new events with keys like these.  You could also structure 
the data as a time bucket, where the row key is an hour, and each column is an event in that time bucket.  The drawback 
to this approach is that rows are limited to 100 Mb in size, so make sure your buckets will not be too large.

### HBase

HBase sits on top of HDFS, and it exposes the data in HDFS to other platforms.  It is a NoSQL, wide-column DB.  It can 
handle large loads of OLTP transactions.  HBase is part of the Hadoop tech stack.  It favors consistency and 
partition-tolerance over availability.

HBase = open source BigTable: It is built on the ideas of BigTable (they took the ideas from BigTable's paper published 
by Google).  HBase has no QL but an API that can be used for CRUD operations.  HBase is split into ranges of keys called 
regions that operate similar to relational DB shards.  It does this automatically, and since it sits atop HDFS, which is 
also distributed, HBase's regions distribute the data even more: files -> rows.  Every HBase cluster has a master 
instance that tracks where records are located (which region).  Zookeeper tracks which instance is the master and 
replaces it if needed.  It is important to note that the regions are pointers - the data is actually stored on HDFS.  

HBase identifies rows by unique row-keys.  Each row has column families with an arbitrary number of columns.  This is 
useful for storing sparse data, like user-item matrices.  When designing your HBase schema, you want to minimize column 
families and let there be as many columns as needed per family.  A cell is a row-column entry, and HBase versions cell 
contents with timestamps, making it easy to look at data at points in time.  

Keys are stored lexicographically in HBase, so if you want rows close together, name them with a similar key.  Example:
Google wants to know which websites link to each other.  It stores a row for CNN with a key of `com.cnn.www`.  This row 
has a column family for the contents of CNN's main page, where every version of the main page is a column within the 
column family.  It has another column family for anchors, where every column is a URL to a website that links back to 
CNN.  The syntax for describing a column is `column_family:column_name`.  So the anchor column family stores URls as 
column names and the anchor text (the text highlighted blue for the link) is stored as the value.  

Another example is storing user-item matrices.  For a user-movie rating dataset, you might store it as follows:
```
row key = userID
column family = rating
columns = movieID
cell value = movieID rating value
```
Note that rows (users) do not need to have the same columns (movies).

You can access HBase through a shell, Spark, Hive, Pig, Java or Python API, or REST.  If you are using Python, 
`pip install starbase` to set up a REST API client wrapper for using Python with HBase.  Then you can create a 
connection and write movie ratings to a table in HBase:
```
from starbase import Connection

# connect to REST server sitting on top of HBase
c = Connection("127.0.0.1", "8000")

# create a ratings table
ratings = c.table('ratings')

# clear existing data
if ratings.exists():
   ratings.drop()

# create a column family called 'rating'
ratings.create('rating')

# write the data from the file to HBase
with open('path to movielens file.csv', 'r') as ratingData:
   batch = ratings.batch()
   for line in ratingData:
      (userID, movieID, rating, timestamp) = line.split()
      batch.update(userID, {'rating': {movieID: rating}})
batch.commit(finalize=True)

# get ratings for user ID = 1
print(ratings.fetch("1"))
```

If your data is too big for a file, or it's already on HDFS and you just need to move it into an HBase table, you can 
use Pig.  To do this, you would need to create the HBase table ahead of time.  

### Cassandra

Cassandra is a wide-column NoSQL DB that has no single point of failure (no master node) so it is engineered for 
availability above all else.  Since there is no master node, every node runs the same software and performs the same 
functions.  Its data model is similar to BigTable and HBase: there are no joins and it is meant for massive transactions 
rates.  Cassandra has a SQL-like query language called Cassandra Query Language (CQL) but it is not SQL in that it is 
very limited in what it can do.  

Cassandra is a greek figure that can tell the future, like an Oracle, but was named to imply that it can replace Oracle 
(relational DB). 

Partition tolerance from CAP theorem is required with big data, so you really can only choose between consistency and 
availability.  Cassandra chooses availability and partition-tolerance, but has tunable consistency (it lets you decide 
how late the eventual consistency is).  Cassandra maintains availability without a master node by allowing all nodes to 
communicate with one another in a circular fashion.  The tunable consistency tells Cassandra how many of the nodes you 
will require to be consistent before a value is returned for a query.  You can replicate Cassandra clusters for 
analytics to avoid hurting performance for your application.  

### MongoDB

MongoDB is free to use but is not open source - it is owned by a corporation.  MongoDB chooses consistency and 
partition-tolerance over availability.  It has a master node.  MongoDB is unique in that any kind of data can go into 
it - there is no schema at all, unless you create one and if you do it will adhere to it with all writes.  MongoDB has 
a document based data model, and its flexibility means that documents can be embedded in other documents.  There is no 
single key like there is in other DBs, but you can create indices.  Joins are inefficient, so you will want to 
denormalize the data as much as possible.  

MongoDB has collections of documents instead of tables of rows.  Data cannot move between collections across different 
DBs.  

MongoDB uses replica sets to back up data from the primary/master node to secondary nodes.  Note that these nodes are 
not part of a distributed big data structure, they are literally backups of MongoDB as a whole monolith.  When a primary 
node goes down, the secondaries elect a backup with majority vote, meaning you must have a minimum of 3 secondaries if 
you want to use replication.  Furthermore, you must maintain an odd number of secondaries at all times.  Replicas 
address MongoDB's durability, not its ability to scale.  Mongo scales by sharding over the replica sets.  

MongoDB has Hadoop-like functionality, like GridFS instead of HDFS, and built in aggregation instead of MapReduce.  So 
you may hear that if you use MongoDB you do not need Hadoop.  

Since MongoDB and HBase favor consistency over availability, they are better for stock trading or financial platforms.  

#### Key-Value vs Wide-Column vs Document

The 3 common types of NoSQL data storage are key-value like Redis, wide-column like hbase, and document like Mongo.  
Wide-column limits the number of nested items and stores data, more efficiently than document stores, in rows.  It can 
be indexed for efficient querying, such as with time series data where rows are timestamps and the data is sensor 
readings.  So wide-column DBs are better for IoT or real time storage at massive scale.  Document DBS require re-writing 
the entire document if something is updated, which is why writes are slower.  But it is better for storing nested data, 
like user profiles.  

## Query Engines for Big Data

Query engines for big data allow you to execute SQL like queries across your distributed data, regardless of where it 
is.  If you have data in MongoDB + Cassandra + HDFS, you can query them all with these tools.  

Tools not listed in this section include:
* ElasticSearch = distributed document search (keyword based boolean search), used by wikipedia, BM25 algorithm, paired with Kibana for visualization

### Apache Drill

Drill lets you run SQL queries for NoSQL data.  Supports:
* Hive, MongoDB, HBase
* JSON, HDFS, local file systems

Drill cannot talk to Cassandra.

Drill can join data from different NoSQL DBs.

Drill is based on Google's Dremel tool.  

### Facebook Presto

Drill lets you run SQL queries for NoSQL data.  Supports:
* Hive, Cassandra, HBase
* MySQL, Kafka, Postgres, Redis
* JSON, HDFS, local file systems

Presto cannot talk to MongoDB.

Presto is optimized for OLAP and data warehousing.  Facebook developed it but open sourced it.  They use it for querying 
their 300 PB data warehouse, running 30k queries per day.  

## Moving Data in GCP

* Dataproc - Spark/Hadoop service for processing big data in batches.  You have to set up and manage the clusters yourself, so it accrues cost while the cluster is active.   
* Dataflow - Managed service for processing big data in batches or streams.  It's serverless so it only runs when requested and only accrues cost while the job runs.  Dataflow uses Apache Beam under the hood.
* Cloud Composer - Managed service for orchestrating workflows (it's Google managed Airflow).  Cloud Composer doesn't process big data itself, but helps manage workflows that process big data.  
* Dataprep - A GUI for exploring, cleaning, and preparing data for analysis.  It's serverless so it only runs when requested and only accrues cost while the job runs.   
* Datastream - Service to stream data from SQL DB's into BigQuery.
* Cloud Data Fusion - Managed service for building and managing data pipelines.  It lets you build ETL pipelines with a visual tool.  It can connect to data outside of GCP.  It uses Dataproc under the hood for batch processing.

### DataFlow

DataFlow (Google managed Apache Beam).  Used for automated stream or batch jobs that require map reduce.

### Cloud Composer

Cloud composer = managed Airflow; a direct competitor of Dagster.  A general purpose orchestration tool.
