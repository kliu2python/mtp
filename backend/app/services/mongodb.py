import json
import urllib
import requests
import logging

logger = logging.getLogger(__name__)


class MongoDBAPI:
    def __init__(self,
                 api_base="http://10.160.24.88:31742/api/v1/mongodb/document",
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
            response = requests.post(url, json=document)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error inserting document into MongoDB: {e}")
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
            response = requests.get(get_url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            if not data["documents"][0].get("builds"):
                return []
            elif not data["documents"][0]["builds"].get(build_num):
                return []
            return data["documents"][0]["builds"][build_num]["res"]
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
        response = requests.put(url, json=update_body)
        try:
            response.raise_for_status()
            return response.json()
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
        response = requests.put(url, json=update_body)
        try:
            response.raise_for_status()
            return response.json()
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

        get_response = requests.get(get_url)
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
            response = requests.put(update_url, json=update_body)
            response.raise_for_status()
            return response.json()
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

            get_response = requests.get(get_url)
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
                response = requests.put(url, json=update_body)
            else:
                url = self._url(f"insert?db={self.db}&collection"
                                f"={self.collection}")
                if "documents" not in document:
                    json_body = document
                else:
                    json_body = document.get("documents")
                    if isinstance(json_body, list) and len(json_body) > 0:
                        json_body = json_body[0]
                response = requests.post(url, json=json_body)
        else:
            url = self._url(f"insert?db={self.db}&collection"
                            f"={self.collection}")
            response = requests.post(url, json=document)
        try:
            response.raise_for_status()
            return response.json()
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
            response = requests.delete(url, json=body)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_all_jobs(self):
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection={self.collection}")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_all_groups(self) -> list:
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection=groups")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            groups = []
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                groups.append(group.get('name'))
            return groups
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
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            groups = []
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                groups.append(group)
            return groups
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
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()

            return data.get('documents')[0]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []

    def get_group_count(self) -> dict:
        """Fetch all job names from the MongoDB collection."""
        url = self._url(f"find?db={self.db}&collection=groups")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            counts = {}
            # Assuming that data contains a list of job names
            for group in data.get('documents'):
                counts[group['name']] = group['counts']
            return counts
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
            response = requests.get(url)
            response.raise_for_status()  # Will raise an error for HTTP errors
            data = response.json()
            # Assuming that data contains a list of job names
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching jobs from MongoDB: {e}")
            return []