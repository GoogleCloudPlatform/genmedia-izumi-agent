/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function generateUUID() { 
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
        return v.toString(16);
    });
}

function displayUserId() {
    const userIdSpan = document.getElementById('user-id');
    let userId = getCookie('adk_user_id');
    if (!userId) {
        userId = generateUUID();
        setCookie('adk_user_id', userId, 365);
    }
    userIdSpan.textContent = userId;
}

function updateLinks() {
    const userId = getCookie('adk_user_id');
    if (userId) {
        const adkWebLink = document.querySelector('a[href^="/adk-web/"]');
        if (adkWebLink) {
            adkWebLink.href = `/adk-web/?userId=${userId}`;
        }
        const debugUiLink = document.querySelector('a[href^="/debug-ui/"]');
        if (debugUiLink) {
            debugUiLink.href = `/debug-ui/?userId=${userId}`;
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    displayUserId();
    updateLinks();

    document.getElementById('reset-user-id').addEventListener('click', function() {
        const newUserId = generateUUID();
        setCookie('adk_user_id', newUserId, 365);
        document.getElementById('user-id').textContent = newUserId;
        updateLinks();
    });
});
