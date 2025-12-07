# Acceptable Test Run Persistence

## Current Data Flow
- The backend writes acceptable-scope Jenkins runs to the `acceptable_tests` MongoDB collection when a job is queued. This happens inside `JenkinsService.execute_job` via `MongoDBAPI.insert_acceptable_test_record`. The stored document mirrors the runner payload with `test_scope` set to `acceptable`. The payload now includes the build number, resolved Mantis IDs, and an app download link so these values are persisted alongside the run details.
- The frontend PreFlight page now requests previously stored acceptable test records from `/api/jenkins/run/acceptable-tests` and pre-populates the platform tables with the returned data when the page loads.

## Impact
- Acceptable test runs are now visible in the UI without re-uploading files, thanks to the new API endpoint and PreFlight fetch logic.
