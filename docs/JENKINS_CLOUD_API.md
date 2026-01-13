# Jenkins Cloud Runner API

The Jenkins Cloud service exposes a set of endpoints under the `/api/v1/jenkins_cloud` prefix for triggering multi-platform test jobs and retrieving their status. The service is designed around the `JenkinsJobs` manager (see `manage.py`) and persists execution details in MongoDB.

## Base URL

```
http://10.160.24.88:31224/api/v1/jenkins_cloud
```

## Execute FTM test runs

Use the `POST /run/execute/ftm` endpoint to start Jenkins builds for one or more platforms. The request body is passed directly to `JenkinsJobs.execute_run_task`, which merges test environment details from MongoDB with any request-level parameters before triggering the builds.

### Request body

- `environment` (string): Logical test environment name. Lower-cased and used to look up environment-specific values in MongoDB via `fetch_test_env_info`.
- `platforms` (array of strings): List of platform identifiers. Each platform is looked up in `CONF['jenkins_info']['jobs']` to find the Jenkins job path to trigger.
- `parameters` (object): Arbitrary job parameters that should be sent to every triggered platform job.
- `custom` (object, optional): Per-request overrides merged into the environment data returned from MongoDB.
- `project` (string, optional): Logical project name stored with run results. Defaults to `ftm_ios`.

Example payload:

```json
{
  "environment": "qa",
  "platforms": ["ios", "android"],
  "parameters": {
    "TEST_SUITE": "smoke",
    "RETRY_COUNT": 1
  },
  "custom": {
    "APP_VERSION": "7.0.0"
  },
  "project": "ftm_ios"
}
```

### Execution flow

1. `execute_run_task` resolves the test environment data from MongoDB using `environment` and merges it with the request `parameters` and optional `custom` overrides.
2. For each `platform`, the method looks up the Jenkins job path from `CONF['jenkins_info']['jobs']` and calls `jenkins.build_job` with the merged parameters.
3. Once Jenkins assigns a build number, the helper thread stores a record in the `runner` MongoDB collection that includes the platform name, build URL, request parameters, and timestamps with an initial `res` value of `running`.
4. The API immediately returns `true` while the background threads continue tracking queue assignment.

### Fetching run results

The following endpoints surface the status persisted by `JenkinsJobs`:

- `GET /run/ios/ftm`: Returns all stored run documents for the `ftm_ios` app.
- `GET /run/results/ios/ftm`: Fetches all run records and refreshes their Jenkins status if needed.
- `GET /run/result/ios/ftm?job_name=<name>`: Returns the status for a single run keyed by its `name` field.
- `DELETE /run/result/ios/ftm/delete?job_name=<name>`: Deletes a stored run result if it is no longer running.

## Additional endpoints

The service also exposes helper endpoints for job discovery and management:

- `GET /list`: Recursively list all Jenkins jobs visible to the configured server.
- `GET /category/<type>`: List jobs under configured category paths for a given type.
- `POST /jobs/parameters`: Validate credentials against a Jenkins job and persist its parameter schema in MongoDB.
- `POST /execute/job`: Trigger a single Jenkins job with explicit server credentials and parameters.
- `GET /jobs/build/result`: Look up the result of a specific build number for a known job.
- `GET /db_jobs`: Return all jobs stored in MongoDB.
- `GET /groups`: Return the defined job groups.
- `GET /apk_images` and `POST /apk_images`: List and upload `.apk` or `.ipa` artifacts on the Jenkins server host.

These helpers reuse the `JenkinsJobs` manager to keep job metadata synchronized between Jenkins and MongoDB.
