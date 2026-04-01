# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from firebase_admin import firestore


class BaseService:
    """Base class for services that interact with Firestore."""

    def __init__(self, db: firestore.Client):
        """Initializes the BaseService.

        Args:
            db: The Firestore client.
        """
        self._db = db

    def _get_collection(self, collection_name: str) -> firestore.CollectionReference:
        """Gets a Firestore collection.

        Args:
            collection_name: The name of the collection.

        Returns:
            The Firestore collection.
        """
        return self._db.collection(collection_name)
