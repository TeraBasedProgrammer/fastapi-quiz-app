# Fast api quizz app (internship project)

# Tasks

## BE #1 - Init Project 

To launch the application execute main.py file:
```bash
$ python -m app.main
```

Result:

```bash
INFO:     Will watch for changes in these directories: ['/home/user/Desktop/code/internship-fastapi-app']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [718162] using WatchFiles
INFO:     Started server process [718164]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## BE #2 - Add Dockerfile

1. To build the docker image from the Dockerfile use this command:

```bash
$ docker build -t fastapi-app .
```
Where:

* __-t__  -  sets the name and a tag (optionally) of the image 
* fastapi-app - name of the image
* . - Dockerfile location

2. Use recently built image to create a docker container:

```bash
$ docker run -dp 8000:8000 --name "fastapi-container" fastapi-app 
```
Where:
* -d - makes container work in the background
* -p 8000:8000 - port forwarding (external port: internal port) to allow access to the container from the outside
* --name - names the container with custom name

3. To execute tests inside docker container use the following command:

```bash
$ docker exec fastapi-container pytest
```
Where:
* exec - allows you to execute the command inside working container
* fastapi-container - name of the container
* pytest - testing module


Result:

```bash
============================= test session starts ==============================
platform linux -- Python 3.10.6, pytest-7.4.0, pluggy-1.2.0
rootdir: /code
configfile: pyproject.toml
plugins: asyncio-0.21.0, anyio-3.7.1
asyncio: mode=auto
collected 1 item

tests/test_main.py .                                                     [100%]

============================== 1 passed in 1.06s ===============================
```
