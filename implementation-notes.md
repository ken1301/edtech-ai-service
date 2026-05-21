# Implementation Notes

- Chose a default S3 bucket name of `documents` with `MINIO_BUCKET_NAME` or `S3_BUCKET_NAME` overrides because the repo did not define a bucket setting.
- Added a small bucket auto-creation step in the S3 adapter so local MinIO setups can work without a separate provisioning step.
- Used path-style object keys for documents: `pdfs/{id}/{filename}` and `images/{id}/{filename}` so uploads and downloads stay symmetric.
- Kept the cloud adapter async by offloading boto3 calls to `asyncio.to_thread` instead of switching the whole adapter to a synchronous API.
- Renamed adapter log tags to match the requested file names, and removed non-error success/not-found logs in the touched store adapters.
- Stored exercises in a dedicated `exercises` collection rather than reusing `student_profiles`, which was clearly the wrong collection for this adapter.
- Serialized Mongo exercise payloads with `model_dump(mode="json")` so nested Pydantic and enum values stay Mongo-friendly and round-trip cleanly.
- Returned `False` for a Mongo exercise delete when no document existed, but raised store errors for missing exercises on read because the port returns a non-optional `Exercise`.