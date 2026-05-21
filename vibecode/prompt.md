Complete file "adapters/outbound/docs_storage/s3_adapter.py" and "adapters/outbound/persistence/mongo_exercise_store.py". Then update  the logging in file "adapters/outbound/persistence/mongo_session_store.py","adapters/outbound/persistence/mongo_profile_store.py" and "adapters/outbound/cache/redis_adapter.py".

Requirements:
- Complete all methods in the S3Adapter class and MongoExerciseAdapter.
- Logging should be added to each method with this format:
  - Do not log happy path successes.
  - Log only error case and raise exceptions with clear messages:
  ```python
  try:
      pass # Replace with actual code

  except <type_of_exception> as e:
    logger.error(
      "<current_adapter>.<method_name>.<error_case>",
      log_type="technical",
      error=str(e),
    )
    raise <ExceptionType>(f"Failed to <action> ") from e
  # You can have multiple except blocks for different exception types if needed

  # Finally, catch any unexpected exceptions to ensure they are logged and handled gracefully
  except Exception as e:
    logger.error(
      "<current_adapter>.<method_name>.unexpected_error",
      log_type="technical",
      error=str(e),
    )
    raise <ExceptionType>("An unexpected error occurred while <action>") from e

  
  # type_of_exception: any specific exceptions you expect (e.g., BotoCoreError, ClientError for S3 operations, or PyMongoError for MongoDB operations)
  # current_adapter: s3_apapter | mongo_session_store | mongo_profile_store | mongo_exercise_store | redis_adapter
  # ExceptionType: CloudAdapterError | SessionStoreError | ProfileStoreError | ExerciseStoreError 
  ```



