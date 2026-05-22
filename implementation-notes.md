(Running notes)

- Removed redundant service-layer error logging for known downstream exceptions so the lower layer remains the single place that logs the failure before the error is wrapped upward.
- Moved chatbot HTTP translation out of the use case and into the REST adapter so the use case can raise `ChatBotUseCaseError` like the rest of the application-layer flows.
- Kept helper warnings such as missing student profiles and missing extracted images because they are non-fatal signals rather than happy-path logging.
- Added `exc_info=True` only for unexpected exceptions so stack traces are preserved without making routine domain failures noisier.
- I did not change the existing `ExerciseSelectionUseCase.save_exercise()` call/signature mismatch because it is separate from the logging spec and would require a broader behavior change.
