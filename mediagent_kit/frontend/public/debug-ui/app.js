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

document.addEventListener('DOMContentLoaded', () => {
    const userIdSpan = document.getElementById('userId');
    const listItemsBtn = document.getElementById('listItems');
    const assetList = document.getElementById('assetList');
    const canvasList = document.getElementById('canvasList');
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('file');
    const fileNameInput = document.getElementById('fileName');
    const mimeTypeInput = document.getElementById('mimeType');
    const deleteAllAssetsBtn = document.getElementById('deleteAllAssets');
    const assetSearchInput = document.getElementById('assetSearch');
    const canvasSearchInput = document.getElementById('canvasSearch');
    const deleteAllCanvasesBtn = document.getElementById('deleteAllCanvases');
    const deleteAssetsStatus = document.getElementById('deleteAssetsStatus');
    const deleteCanvasesStatus = document.getElementById('deleteCanvasesStatus');
    const assetSortBy = document.getElementById('assetSortBy');
    const assetSortOrder = document.getElementById('assetSortOrder');
    const canvasSortBy = document.getElementById('canvasSortBy');
    const canvasSortOrder = document.getElementById('canvasSortOrder');
    const assetTypeFilter = document.getElementById('assetTypeFilter');
    const loader = document.getElementById('loader');

    let userId = '';

    // New user ID and redirect logic
    const urlParams = new URLSearchParams(window.location.search);
    const userIdFromUrl = urlParams.get('userId');

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

    if (userIdFromUrl) {
        userId = userIdFromUrl;
        userIdSpan.textContent = userId;
        loadItems();
    } else {
        const userIdFromCookie = getCookie('adk_user_id');
        userId = userIdFromCookie || 'user';
        window.location.href = `${window.location.pathname}?userId=${userId}`;
        return; // Stop further execution until redirect
    }

    fileInput.addEventListener('change', () => {
        const file = fileInput.files[0];
        if (file) {
            fileNameInput.value = file.name;
            mimeTypeInput.value = file.type;
        }
    });

    async function loadItems() {
        listItemsBtn.classList.add('hidden');
        loader.classList.remove('hidden');
        assetList.innerHTML = '';
        canvasList.innerHTML = '';

        if (!userId) {
            alert('User ID is missing.');
            listItemsBtn.classList.remove('hidden');
            loader.classList.add('hidden');
            return;
        }

        try {
            await Promise.all([loadAssets(userId), loadCanvases(userId)]);
        } catch (error) {
            console.error('Error loading items:', error);
            alert('Error loading items. See console for details.');
        } finally {
            listItemsBtn.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    }

    async function loadAssets(userId) {
        const response = await fetch(`/users/${userId}/assets`);
        if (!response.ok) {
            throw new Error(`Failed to fetch assets: ${response.statusText}`);
        }
        let assets = await response.json();

        const assetType = assetTypeFilter.value;
        if (assetType !== 'all') {
            assets = assets.filter(asset => asset.mime_type.startsWith(assetType));
        }

        const sortBy = assetSortBy.value;
        const sortOrder = assetSortOrder.value;

        assets.sort((a, b) => {
            const aValue = a[sortBy];
            const bValue = b[sortBy];
            if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        assetList.innerHTML = ''; // Clear previous list

        assets.forEach(asset => {
            const li = document.createElement('li');
            li.classList.add('asset-card');

            const mediaContainer = document.createElement('div');
            mediaContainer.classList.add('asset-media');

            const viewUrl = asset.current_version
                ? `/users/${userId}/assets/${asset.id}/view?version=${asset.current_version}`
                : `/users/${userId}/assets/${asset.id}/view`;

            if (asset.mime_type.startsWith('image/')) {
                const img = document.createElement('img');
                img.src = viewUrl;
                img.alt = asset.file_name;
                mediaContainer.appendChild(img);
            } else if (asset.mime_type.startsWith('video/')) {
                const video = document.createElement('video');
                video.controls = true;
                video.src = viewUrl;
                mediaContainer.appendChild(video);
            } else if (asset.mime_type.startsWith('audio/')) {
                const audio = document.createElement('audio');
                audio.controls = true;
                audio.src = viewUrl;
                mediaContainer.appendChild(audio);
            } else if (asset.mime_type === 'application/pdf') {
                const iframe = document.createElement('iframe');
                iframe.src = viewUrl;
                mediaContainer.appendChild(iframe);
            } else {
                const placeholder = document.createElement('div');
                placeholder.classList.add('file-placeholder');
                placeholder.textContent = asset.mime_type;
                mediaContainer.appendChild(placeholder);
            }

            const infoContainer = document.createElement('div');
            infoContainer.classList.add('asset-info');

            const fileName = document.createElement('span');
            fileName.textContent = asset.file_name;

            const assetId = document.createElement('span');
            assetId.classList.add('asset-id');
            assetId.textContent = `ID: ${asset.id}`;

            infoContainer.appendChild(fileName);
            infoContainer.appendChild(assetId);

            if (asset.current_version) {
                const versionSpan = document.createElement('span');
                versionSpan.classList.add('asset-version');
                versionSpan.textContent = `Version: ${asset.current_version}`;
                infoContainer.appendChild(versionSpan);
            }

            const currentVersion = asset.versions.find(v => v.version_number === asset.current_version);
            let generationConfig = null;
            if (currentVersion) {
                generationConfig = currentVersion.image_generate_config || currentVersion.video_generate_config || currentVersion.music_generate_config || currentVersion.speech_generate_config;
            }

            if (generationConfig) {
                const viewConfigLink = document.createElement('a');
                viewConfigLink.href = '#';
                viewConfigLink.textContent = 'View Config';
                viewConfigLink.classList.add('view-config-btn');
                viewConfigLink.style.fontSize = '0.8em'; // Smaller font size
                viewConfigLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    const modal = document.getElementById('generationConfigModal');
                    const configContent = document.getElementById('generationConfigContent');
                    configContent.textContent = JSON.stringify(generationConfig, null, 2);
                    modal.style.display = 'block';
                });
                infoContainer.appendChild(viewConfigLink);
            }

            const actionsContainer = document.createElement('div');
            actionsContainer.classList.add('asset-actions');

            const downloadUrl = asset.current_version
                ? `/users/${userId}/assets/${asset.id}/download?version=${asset.current_version}`
                : `/users/${userId}/assets/${asset.id}/download`;

            const downloadLink = document.createElement('a');
            downloadLink.href = downloadUrl;
            downloadLink.textContent = 'Download';
            downloadLink.classList.add('download-btn');
            downloadLink.setAttribute('download', asset.file_name);

            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('delete-btn');
            deleteBtn.textContent = 'Delete';
            deleteBtn.dataset.assetId = asset.id;

            actionsContainer.appendChild(downloadLink);
            actionsContainer.appendChild(deleteBtn);

            li.appendChild(mediaContainer);
            li.appendChild(infoContainer);
            li.appendChild(actionsContainer);

            assetList.appendChild(li);
        });
    }

    async function loadCanvases(userId) {
        const response = await fetch(`/users/${userId}/canvases`);
        if (!response.ok) {
            throw new Error(`Failed to fetch canvases: ${response.statusText}`);
        }
        let canvases = await response.json();

        const sortBy = canvasSortBy.value;
        const sortOrder = canvasSortOrder.value;

        canvases.sort((a, b) => {
            const aValue = a[sortBy] || '';
            const bValue = b[sortBy] || '';
            if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        canvasList.innerHTML = ''; // Clear previous list

        canvases.forEach(canvas => {
            const li = document.createElement('li');
            li.classList.add('canvas-card');

            const infoContainer = document.createElement('div');
            infoContainer.classList.add('canvas-info');

            const canvasTitle = document.createElement('span');
            canvasTitle.textContent = canvas.title || `Canvas ${canvas.id}`;

            const canvasType = document.createElement('span');
            canvasType.classList.add('canvas-type');
            canvasType.textContent = canvas.canvas_type;

            const canvasId = document.createElement('span');
            canvasId.classList.add('canvas-id');
            canvasId.textContent = `ID: ${canvas.id}`;

            infoContainer.appendChild(canvasTitle);
            infoContainer.appendChild(canvasType);
            infoContainer.appendChild(canvasId);

            const actionsContainer = document.createElement('div');
            actionsContainer.classList.add('canvas-actions');

            if (canvas.canvas_type === 'html') {
                const viewBtn = document.createElement('button');
                viewBtn.classList.add('view-btn');
                viewBtn.textContent = 'View';
                viewBtn.addEventListener('click', () => {
                    window.open(`/users/${userId}/canvases/${canvas.id}/view`, '_blank');
                });
                actionsContainer.appendChild(viewBtn);
            } else if (canvas.canvas_type === 'video_timeline') {
                const viewBtn = document.createElement('button');
                viewBtn.classList.add('view-btn');
                viewBtn.textContent = 'View';
                viewBtn.addEventListener('click', () => {
                    window.open(`video_timeline_viewer.html?userId=${userId}&canvasId=${canvas.id}`, '_blank');
                });
                actionsContainer.appendChild(viewBtn);
            }

            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('delete-btn');
            deleteBtn.textContent = 'Delete';
            deleteBtn.dataset.canvasId = canvas.id;

            actionsContainer.appendChild(deleteBtn);

            li.appendChild(infoContainer);
            li.appendChild(actionsContainer);

            canvasList.appendChild(li);
        });
    }

    listItemsBtn.addEventListener('click', loadItems);
    assetSortBy.addEventListener('change', loadItems);
    assetSortOrder.addEventListener('change', loadItems);
    canvasSortBy.addEventListener('change', loadItems);
    canvasSortOrder.addEventListener('change', loadItems);
    assetTypeFilter.addEventListener('change', loadItems);

    deleteAllAssetsBtn.addEventListener('click', async () => {
        if (!userId) {
            alert('User ID is missing.');
            return;
        }

        if (confirm('Are you sure you want to delete all assets for this user?')) {
            const assetCards = assetList.getElementsByClassName('asset-card');
            const assetIds = Array.from(assetCards).map(card => {
                const deleteBtn = card.querySelector('.delete-btn');
                return deleteBtn ? deleteBtn.dataset.assetId : null;
            }).filter(id => id);

            const totalAssets = assetIds.length;
            let deletedCount = 0;
            deleteAssetsStatus.textContent = `Deleting 0 / ${totalAssets}...`;

            try {
                for (const assetId of assetIds) {
                    const response = await fetch(`/users/${userId}/assets/${assetId}`, {
                        method: 'DELETE',
                    });

                    if (response.ok) {
                        deletedCount++;
                        deleteAssetsStatus.textContent = `Deleting ${deletedCount} / ${totalAssets}...`;
                    } else {
                        const error = await response.json();
                        alert(`Error deleting asset ${assetId}: ${error.detail}`);
                    }
                }
                assetList.innerHTML = ''; // Clear the list
                deleteAssetsStatus.textContent = `Deleted ${deletedCount} / ${totalAssets} assets.`;
                setTimeout(() => {
                    deleteAssetsStatus.textContent = '';
                }, 3000);
            } catch (error) {
                console.error('Error deleting assets:', error);
                alert('Error deleting assets. See console for details.');
                deleteAssetsStatus.textContent = 'Error deleting assets.';
            }
        }
    });

    deleteAllCanvasesBtn.addEventListener('click', async () => {
        if (!userId) {
            alert('User ID is missing.');
            return;
        }

        if (confirm('Are you sure you want to delete all canvases for this user?')) {
            const canvasCards = canvasList.getElementsByClassName('canvas-card');
            const canvasIds = Array.from(canvasCards).map(card => {
                const deleteBtn = card.querySelector('.delete-btn');
                return deleteBtn ? deleteBtn.dataset.canvasId : null;
            }).filter(id => id);

            const totalCanvases = canvasIds.length;
            let deletedCount = 0;
            deleteCanvasesStatus.textContent = `Deleting 0 / ${totalCanvases}...`;

            try {
                for (const canvasId of canvasIds) {
                    const response = await fetch(`/users/${userId}/canvases/${canvasId}`, {
                        method: 'DELETE',
                    });

                    if (response.ok) {
                        deletedCount++;
                        deleteCanvasesStatus.textContent = `Deleting ${deletedCount} / ${totalCanvases}...`;
                    } else {
                        const error = await response.json();
                        alert(`Error deleting canvas ${canvasId}: ${error.detail}`);
                    }
                }
                canvasList.innerHTML = ''; // Clear the list
                deleteCanvasesStatus.textContent = `Deleted ${deletedCount} / ${totalCanvases} canvases.`;
                setTimeout(() => {
                    deleteCanvasesStatus.textContent = '';
                }, 3000);
            } catch (error) {
                console.error('Error deleting canvases:', error);
                alert('Error deleting canvases. See console for details.');
                deleteCanvasesStatus.textContent = 'Error deleting canvases.';
            }
        }
    });

    assetSearchInput.addEventListener('input', () => {
        const searchTerm = assetSearchInput.value.toLowerCase();
        const assets = assetList.getElementsByClassName('asset-card');

        for (const asset of assets) {
            const fileName = asset.querySelector('.asset-info span').textContent.toLowerCase();
            if (fileName.includes(searchTerm)) {
                asset.style.display = '';
            } else {
                asset.style.display = 'none';
            }
        }
    });

    canvasSearchInput.addEventListener('input', () => {
        const searchTerm = canvasSearchInput.value.toLowerCase();
        const canvases = canvasList.getElementsByClassName('canvas-card');

        for (const canvas of canvases) {
            const title = canvas.querySelector('.canvas-info span').textContent.toLowerCase();
            if (title.includes(searchTerm)) {
                canvas.style.display = '';
            } else {
                canvas.style.display = 'none';
            }
        }
    });

    assetList.addEventListener('click', async (event) => {
        if (event.target.classList.contains('delete-btn')) {
            const assetId = event.target.dataset.assetId;

            if (!userId) {
                alert('User ID is missing.');
                return;
            }

            if (confirm('Are you sure you want to delete this asset?')) {
                try {
                    const response = await fetch(`/users/${userId}/assets/${assetId}`, {
                        method: 'DELETE',
                    });

                    if (response.ok) {
                        event.target.closest('.asset-card').remove();
                    } else {
                        const error = await response.json();
                        alert(`Error deleting asset: ${error.detail}`);
                    }
                } catch (error) {
                    console.error('Error deleting asset:', error);
                    alert('Error deleting asset. See console for details.');
                }
            }
        }
    });

    canvasList.addEventListener('click', async (event) => {
        if (event.target.classList.contains('delete-btn')) {
            const canvasId = event.target.dataset.canvasId;

            if (!userId) {
                alert('User ID is missing.');
                return;
            }

            if (confirm('Are you sure you want to delete this canvas?')) {
                try {
                    const response = await fetch(`/users/${userId}/canvases/${canvasId}`, {
                        method: 'DELETE',
                    });

                    if (response.ok) {
                        event.target.closest('.canvas-card').remove();
                    } else {
                        const error = await response.json();
                        alert(`Error deleting canvas: ${error.detail}`);
                    }
                } catch (error) {
                    console.error('Error deleting canvas:', error);
                    alert('Error deleting canvas. See console for details.');
                }
            }
        }
    });

    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (!userId) {
            alert('User ID is missing.');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('file_name', fileNameInput.value);
        formData.append('mime_type', mimeTypeInput.value);

        try {
            const response = await fetch(`/users/${userId}/assets`, {
                method: 'POST',
                body: formData,
            });

            if (response.ok) {
                alert('Asset uploaded successfully');
                loadItems(); // Refresh the asset and canvas lists
            } else {
                const error = await response.json();
                alert(`Error uploading asset: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error uploading asset:', error);
            alert('Error uploading asset. See console for details.');
        }
    });

    // Modal logic
    const imageModal = document.getElementById("imageModal");
    const modalImg = document.getElementById("modalImage");
    const closeImageModal = document.getElementsByClassName("close")[0];

    const generationConfigModal = document.getElementById('generationConfigModal');
    const closeConfigModal = document.getElementsByClassName('close-config')[0];

    assetList.addEventListener('click', (event) => {
        if (event.target.tagName === 'IMG') {
            imageModal.style.display = "flex";
            modalImg.src = event.target.src;
        }
    });

    closeImageModal.onclick = function() {
        imageModal.style.display = "none";
    }

    closeConfigModal.onclick = function() {
        generationConfigModal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == imageModal) {
            imageModal.style.display = "none";
        }
        if (event.target == generationConfigModal) {
            generationConfigModal.style.display = "none";
        }
    }
});