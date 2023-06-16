# Radiobooks Sample Code

[<img src="assets/logo/white_bg.png" width=25% height=25%>](https://www.radiobooks.io)

<p align="left">
<img src="https://img.shields.io/badge/python-3.10-brightgreen" alt="Supported Python versions">
</p>

## Overview

This repository contains a few code samples from the [radiobooks](https://www.radiobooks.io/) backend application. It is only meant for showcasing purposes and cannot be run as-is, since only few files and snippets from the original project have been kept.

The backend structure was inspired by:
- [this project](https://github.com/joaquimcampos/fastapi-mongo-docker-flyio-example) created by [tofran](https://github.com/tofran)
- [and this one](https://github.com/Youngestdev/fastapi-mongo) created by [Youngestdev](https://github.com/Youngestdev)

### On Radiobooks

[Radiobooks](https://www.radiobooks.io/) is a start-up that converts books into audiobooks using AI. Our services include an editing studio that gives users ample control over the generated audio, allowing them to customize their audiobooks to fit their requirements.

## Dependencies

Here we outline a few dependencies/technologies used in this project.

- [DockerCompose](https://docs.docker.com/compose/): used for management of development containers only.
- [Pipenv](https://pipenv.pypa.io/en/latest/): Python dependency management tool. Allows better control than the native PIP.
- [OpenAPI/Swagger](https://spec.openapis.org/oas/latest.html): Rest HTTP API specification format.
- [Fly.io](https://fly.io/docs/): Global application platform used to deploy the production container.
- [FastAPI](https://fastapi.tiangolo.com/): Python web framework;
- [Pydantic](https://pydantic-docs.helpmanual.io/): Python dependency used to create and validate DTOs.
- [Pymongo](https://pymongo.readthedocs.io): the Python <> mongo driver.
- [Beanie](https://beanie-odm.dev/): An an asynchronous Python ODM for MongoDB.
- [AWS aioboto3](https://aioboto3.readthedocs.io/en/latest/usage.html): Async AWS SDK.
