/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const DB_NAME = 'IzumiStudio';
const DB_VERSION = 1;
const STORE_NAME = 'projects';

let db: IDBDatabase;

function init(): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };

    request.onsuccess = () => {
      db = request.result;
      resolve();
    };

    request.onerror = () => {
      console.error('Failed to open IndexedDB', request.error);
      reject(request.error);
    };
  });
}

function getStore(mode: IDBTransactionMode) {
  if (!db) {
    throw new Error('IndexedDB not initialized. Call init() first.');
  }
  const tx = db.transaction(STORE_NAME, mode);
  return tx.objectStore(STORE_NAME);
}

async function get<T>(id: string): Promise<T | undefined> {
  const store = getStore('readonly');
  const request = store.get(id);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result as T);
    request.onerror = () => reject(request.error);
  });
}

async function set<T>(data: T): Promise<void> {
  const store = getStore('readwrite');
  const request = store.put(data);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function getAll<T>(): Promise<T[]> {
  const store = getStore('readonly');
  const request = store.getAll();
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result as T[]);
    request.onerror = () => reject(request.error);
  });
}

async function remove(id: string): Promise<void> {
  const store = getStore('readwrite');
  const request = store.delete(id);
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export const dbService = {
  init,
  get,
  set,
  getAll,
  remove,
};
