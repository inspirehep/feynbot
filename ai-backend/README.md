# ai-backend

## How to Start the Application

To start the application, use the following command:

```sh
make run
```

This will start the application and map port 8000 on your localhost.

### Environment variables

Create a local `.env` file and add the necessary environment variables. See `configMapGenerator.ai-globals` in https://github.com/cern-sis/kubernetes-inspire/blob/main/ai/environments/qa/kustomization.yml and don't forget the secrets (e.g. db url)

## How to Stop the Application

To stop the application, use the following command:

```sh
make stop
```

## Accessing the Application

Once the application is running, you can access it at:

- Application: [http://localhost:8000](http://localhost:8000)
- OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
