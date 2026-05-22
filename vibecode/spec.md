# Loggin and Error Handling Guidelines

- Adapter do not log happy path events, only errors and critical information:
```python
try: 
    # code
    logger.debug(
        "<adapter_name>.<method_name>.completed",
        log_type="debug",
        # any additional context fields
    )
        
except <type_of_error> as e:
    logger.error(
        "<adapter_name>.<method_name>.failed",
        log_type="technical",
        error=str(e),
    )
    raise <custom_adapter_error>(<failed_message>) from e
# You can catch specific exceptions (e.g., database errors, validation errors) to provide more granular error handling and logging. Always re-raise exceptions as custom service errors to maintain a consistent error handling strategy across the application.

# Finally, catch any unexpected exceptions to ensure that all errors are logged and handled gracefully:
except Exception as e:
    logger.error(
        "<adapter_name>.<method_name>.unexpected.failed",
        log_type="technical",
        error=str(e),
    )
    raise <custom_adapter_error>(<failed_message>) from e
```

- Service layer catch error from adapter and log it, then re-raise as custom service error:
```python
try:
    # code
    logger.info(
        "<service_name>.<method_name>.completed",
        log_type="business",
        # any additional context fields
    )

except <custom_adapter_error> as e:
    # Do not logger error at service layer, just re-raise as custom service error
    raise <custom_service_error>(<failed_message>) from e

# Only logging unexpected exceptions at service layer
except Exception as e:
    logger.error(
        "<service_name>.<method_name>.unexpected.failed",
        log_type="technical",
        error=str(e),
        exc_info=True,
    )
    raise <custom_service_error>(<failed_message>) from e
```

- Usecase layer catch error from service and log it, then re-raise as custom usecase error:
```python
try:
    # code
    logger.info(
        "<usecase_name>.<method_name>.completed",
        log_type="business",
        # any additional context fields
    )

except <custom_service_error> as e:
    logger.error(
        "<usecase_name>.<which_service>.failed",
        log_type="technical",
        error=str(e),
        exc_info=True,
    )
    raise <custom_usecase_error>(<failed_message>) from e

except Exception as e:
    logger.error(
        "<usecase_name>.<method_name>.unexpected.failed",
        log_type="technical",
        error=str(e),
        exc_info=True,
    )
    raise <custom_usecase_error>(<failed_message>) from e
```
