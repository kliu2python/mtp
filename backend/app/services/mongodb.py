import json
import urllib
import requests

from bson.objectid import ObjectId

from app.services.logger import get_logger

logger = get_logger()


class MongoDBAPI:
    def __init__(self,
                 api_base="http://10.160.24.17:31742/api/v1/mongodb/document",
                 db_name="jenkins",
                 collection="jobs"):
        """
        :param api_base:   REST endpoint root, e.g.
                           "http://host:port/api/v1/mongodb/document"
        :param db_name:    the database to use
        :param collection: the collection to use
        """
        url = api_base.rstrip('/')
        self.api_base = url
        self.db = db_name
        self.collection = collection

    def get_test_templates(self):
        """Fetch all test templates from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection=test_templates")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("documents", [])
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching test templates from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching test templates from MongoDB: {e}")
            return []

    def get_test_template_by_id(self, template_id: str):
        """Fetch a test template by ID from the MongoDB collection."""
        import json
        import urllib.parse

        filter_json = json.dumps({"id": template_id})
        encoded_filter = urllib.parse.quote(filter_json)
        url = self._url(
            f"find?db={self.db}&collection=test_templates&filter={encoded_filter}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            templates = data.get("documents", [])
            return templates[0] if templates else None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching test template from MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching test template from MongoDB: {e}")
            return None

    def insert_test_template(self, template_doc: dict):
        """Insert a test template into the MongoDB collection."""
        return self.insert_document(template_doc, collection="test_templates")

    def update_test_template(self, template_id: str, update_data: dict):
        """Update a test template in the MongoDB collection."""
        update_body = {
            "filter": {"id": template_id},
            "update": {"$set": update_data}
        }
        url = self._url(f"update?db={self.db}&collection=test_templates")
        try:
            response = requests.put(url, json=update_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout updating test template in MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating test template in MongoDB: {e}")
            return None

    def delete_test_template(self, template_id: str):
        """Delete a test template from the MongoDB collection."""
        delete_body = {
            "filter": {"id": template_id}
        }
        url = self._url(f"delete?db={self.db}&collection=test_templates")
        try:
            response = requests.delete(url, json=delete_body, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("deletedCount", 0) > 0
        except requests.exceptions.Timeout:
            logger.error(f"Timeout deleting test template from MongoDB")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting test template from MongoDB: {e}")
            return False

    def _url(self, action: str) -> str:
        return f"{self.api_base}/{action}"

    def insert_document(self, document, db=None, collection=None):
        """Insert a document into the MongoDB collection."""
        if not db:
            db = self.db
        if not collection:
            collection = self.collection
        url = self._url(f"insert?db={db}&collection={collection}")
        try:
            response = requests.post(url, json=document, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout inserting document into MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inserting document into MongoDB: {e}")
            return None

    def insert_acceptable_test_record(self, record: dict):
        """Persist an acceptable test record into MongoDB."""
        logger.debug(
            "Inserting acceptable test record for job %s", record.get("name")
        )
        result = self.insert_document(record, collection="acceptable_tests")
        if result is not None:
            logger.info(
                "Inserted acceptable test record for job %s", record.get("name")
            )
        else:
            logger.error(
                "Failed to insert acceptable test record for job %s", record.get(
                    "name")
            )
        return result

    def get_acceptable_test_records(self):
        """Fetch acceptable test records from MongoDB."""
        url = self._url(f"find?db={self.db}&collection=acceptable_tests")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            records = data.get("documents", [])
            logger.info(
                "Fetched %d acceptable test records from MongoDB", len(records)
            )
            return records
        except requests.exceptions.Timeout:
            logger.error(
                f"Timeout fetching acceptable test records from MongoDB {url}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching acceptable test records from MongoDB: {e}")
            return []

    def update_acceptable_test_record(self, record_id, updates: dict):
        """Update an acceptable test record using its primary identifier."""
        if not record_id or not updates:
            logger.warning(
                "Skipping acceptable test update due to missing data")
            return None

        normalized_id = record_id
        if isinstance(record_id, dict):
            normalized_id = record_id.get("$oid") or record_id.get("oid")

        update_body = {
            "filter": {"_id": normalized_id or record_id},
            "update": {"$set": updates},
        }

        url = self._url(f"update?db={self.db}&collection=acceptable_tests")
        try:
            response = requests.put(url, json=update_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating acceptable test record: {e}")
            return None

    def delete_acceptable_test_record(self, record_id=None, name=None):
        """Delete an acceptable test record by _id or name."""
        if not record_id and not name:
            logger.warning(
                "No identifier provided for acceptable test deletion")
            return None

        normalized_id = record_id
        if isinstance(record_id, dict):
            normalized_id = record_id.get("$oid") or record_id.get("oid")

        filter_body = {"_id": str(ObjectId(normalized_id))} if record_id else {
            "name": name}
        delete_body = {"filter": filter_body}
        url = self._url(f"delete?db={self.db}&collection=acceptable_tests")
        try:
            response = requests.delete(url, json=delete_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout deleting acceptable test record")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error deleting acceptable test record: {e}")
            return None

    def get_res_of_build_number(self, job_name, build_num):
        """Fetch all job names from the MongoDB collection."""
        filter_json = json.dumps(f"name={job_name}")

        # Step 2: URL-encode the JSON string
        encoded_filter = urllib.parse.quote(filter_json)
        projection_filter = {
            f"builds.{build_num}.res": 1
        }
        projection_filter = json.dumps(projection_filter)
        projection_filter = urllib.parse.quote(projection_filter)
        get_url = self._url(f"find?db={self.db}"
                            f"&collection={self.collection}"
                            f"&filter={encoded_filter}"
                            f"&projection={projection_filter}")
        try:
            response = requests.get(get_url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            if not data["documents"][0].get("builds"):
                return []
            elif not data["documents"][0]["builds"].get(build_num):
                return []
            return data["documents"][0]["builds"][build_num]["res"]
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def update_jenkins_build_res(self, res, job_name, build_number):
        update_body = {
            "filter": {
                "name": job_name
            },
            "update": {
                "$set": {
                    f"builds.{build_number}.res": res
                }
            }
        }
        url = self._url(f"update?db={self.db}&collection={self.collection}")
        try:
            response = requests.put(url, json=update_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout updating document in MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inserting document into MongoDB: {e}")
            return None

    def update_jenkins_run_res(self, res, job_name, updated_at):
        update_body = {
            "filter": {
                "name": job_name
            },
            "update": {
                "$set": {
                    "res": res,
                    "updated_at": updated_at
                }
            }
        }
        url = self._url(f"update?db={self.db}&collection=runner")
        try:
            response = requests.put(url, json=update_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout updating document in MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inserting document into MongoDB: {e}")
            return None

    def fetch_test_env_info(self, test_env, custom_env: dict = None):
        filter_json = json.dumps(f"name={test_env}")
        # Step 2: URL-encode the JSON string
        encoded_filter = urllib.parse.quote(filter_json)

        # Step 3: Compose the URL safely
        get_url = self._url(
            f"find?db={self.db}&collection=test_env"
            f"&filter={encoded_filter}"
        )

        get_response = requests.get(get_url, timeout=30)
        if len(get_response.json().get("documents")) > 0:
            env_info = get_response.json().get("documents")[0]
        elif custom_env:
            env_info = custom_env
        else:
            raise Exception(
                f"no record found by {test_env} and no custom env provided.")
        return env_info

    def update_groups(self, group, append=True):
        groups = self.get_all_groups()
        counts = self.get_group_count()
        update_url = self._url(f"update?db={self.db}&collection=groups")
        upsert = False
        if group in groups:
            logger.info(f"group {group} is included already.")
            count = counts.get(group)
            if append:
                count += 1
            else:
                count -= 1
                if count == 0:
                    self.delete_job_by_name(group, collection="groups")
                    return
        else:
            logger.info(f"group {group} is not created yet.")
            count = 1
            upsert = True
        update_set = {"counts": count}
        update_body = {
            "filter": {"name": group},
            "update": {
                "$set": update_set
            },
            "upsert": upsert
        }

        try:
            response = requests.put(update_url, json=update_body, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout updating group in MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error update group into MongoDB: {e}")
            return None

    def update_document(self, document, db_filter=None):
        if db_filter:
            # Step 1: Convert filter dict to JSON string
            filter_json = json.dumps(db_filter)

            # Step 2: URL-encode the JSON string
            encoded_filter = urllib.parse.quote(filter_json)

            # Step 3: Compose the URL safely
            get_url = self._url(
                f"find?db={self.db}"
                f"&collection={self.collection}&filter={encoded_filter}"
            )

            get_response = requests.get(get_url, timeout=30)
            if len(get_response.json().get("documents")) > 0:
                transformed_filter = db_filter
                if document.get("documents")[0] == get_response.json().get(
                        "documents")[0]:
                    return "no_update"
                if isinstance(db_filter, str) and "=" in db_filter:
                    key, value = db_filter.split("=", 1)
                    transformed_filter = {key.strip(): value.strip()}
                elif not isinstance(db_filter, dict):
                    raise Exception("db_filter is incorrect.")
                if "_id" in document.get("documents")[0]:
                    del document.get("documents")[0]["_id"]
                update_body = {
                    "filter": transformed_filter,
                    "update": {"$set": document.get("documents")[0]}
                }
                url = self._url(
                    f"update?db={self.db}&collection={self.collection}")
                response = requests.put(url, json=update_body, timeout=30)
            else:
                url = self._url(f"insert?db={self.db}&collection"
                                f"={self.collection}")
                if "documents" not in document:
                    json_body = document
                else:
                    json_body = document.get("documents")
                    if isinstance(json_body, list) and len(json_body) > 0:
                        json_body = json_body[0]
                response = requests.post(url, json=json_body, timeout=30)
        else:
            url = self._url(f"insert?db={self.db}&collection"
                            f"={self.collection}")
            response = requests.post(url, json=document, timeout=30)
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Timeout updating document in MongoDB")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inserting document into MongoDB: {e}")
            return None

    def delete_job_by_name(self, job_name, db=None, collection=None):
        """Fetch all job names from the MongoDB collection."""
        if not db:
            db = self.db
        if not collection:
            collection = self.collection
        url = self._url(f"delete?db={db}&collection={collection}")
        body = {
            "filter": {"name": job_name}
        }
        try:
            response = requests.delete(url, json=body, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Timeout deleting job from MongoDB")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_all_jobs(self):
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection={self.collection}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_all_groups(self) -> list:
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection=groups")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            groups = []
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                groups.append(group.get('name'))
            return groups
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_all_run_results(self, app) -> list:
        """Fetch all job names from the MongoDB collection."""
        filter_json = json.dumps(f"app={app}")

        # Step 2: URL-encode the JSON string
        encoded_filter = urllib.parse.quote(filter_json)
        url = self._url(f"find?db={self.db}"
                        f"&collection=runner&filter={encoded_filter}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            groups = []
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                groups.append(group)
            return groups
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_run_result(self, name) -> dict:
        """Fetch all job names from the MongoDB collection."""
        filter_json = json.dumps(f"name={name}")

        # Step 2: URL-encode the JSON string
        encoded_filter = urllib.parse.quote(filter_json)
        url = self._url(f"find?db={self.db}"
                        f"&collection=runner&filter={encoded_filter}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()

            return data.get('documents')[0]
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_group_count(self) -> dict:
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection=groups")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            counts = {}
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                counts[group['name']] = group['counts']
            return counts
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return {}

    def get_job_by_name(self, name):
        """Fetch all job names from the MongoDB collection."""
        filter_json = json.dumps(name)

        # Step 2: URL-encode the JSON string
        encoded_filter = urllib.parse.quote(filter_json)
        url = self._url(f"find?"
                        f"db={self.db}&collection={self.collection}"
                        f"&filter={encoded_filter}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching jobs from MongoDB")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []
