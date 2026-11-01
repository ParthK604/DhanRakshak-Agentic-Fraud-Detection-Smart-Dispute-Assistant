# Postman collection

Import `DhanRakshak.postman_collection.json`, then import either the local or
Render environment. Select the environment and run the collection in the
Collection Runner. The first Render request may take about a minute while the
free service wakes up.

To use the Postman CLI, sign in if required and run:

```text
postman collection run postman/DhanRakshak.postman_collection.json -e postman/DhanRakshak-render.postman_environment.json
```

The collection has no secrets. It uses `{{base_url}}` and `{{demo_user_id}}`
variables and stores IDs returned by earlier requests when available.
