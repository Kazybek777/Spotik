const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/data/ws';

let cameras = {};

async function fetchCameras() {
    try {
        const resp = await fetch(`${API_BASE}/data/cameras`);
        if (!resp.ok) throw new Error('Ошибка загрузки списка камер');
        const data = await resp.json();
        data.forEach(cam => {
            cameras[cam.id] = {
                name: cam.name,
                capacity: cam.capacity,
                streaming: true,
                vehicle_count: 0,
                free_spots: cam.capacity
            };
        });
        renderCameras();
    } catch (e) {
        console.error('Не удалось загрузить камеры, пробуем status:', e);
        fallbackCameras();
    }
}

function fallbackCameras() {
    fetch(`${API_BASE}/data/status`)
        .then(res => res.json())
        .then(data => {
            data.forEach(cam => {
                cameras[cam.camera_id] = {
                    name: `Камера ${cam.camera_id}`,
                    capacity: cam.capacity,
                    streaming: true,
                    vehicle_count: cam.vehicle_count,
                    free_spots: cam.free_spots
                };
            });
            renderCameras();
        })
        .catch(err => console.error('Не удалось получить статус:', err));
}

function renderCameras() {
    const container = document.getElementById('cameras');
    container.innerHTML = '';

    for (const [id, cam] of Object.entries(cameras)) {
        const card = document.createElement('div');
        card.className = 'camera-card';
        card.id = `camera-${id}`;

        const header = document.createElement('div');
        header.className = 'camera-header';
        header.innerHTML = `
            <h2>${cam.name}</h2>
            <button class="toggle-stream ${!cam.streaming ? 'off' : ''}" data-id="${id}">
                ${cam.streaming ? '🔴 Выключить видео' : '⚫ Включить видео'}
            </button>
        `;
        card.appendChild(header);

        const img = document.createElement('img');
        img.className = 'camera-image';
        img.alt = 'Видеопоток';
        if (cam.streaming) {
            img.src = `${API_BASE}/stream/${id}?t=${Date.now()}`;
        } else {
            img.style.background = '#2d2d2d';
        }
        card.appendChild(img);

        const stats = document.createElement('div');
        stats.className = 'stats';
        stats.innerHTML = `
            <div>
                <span class="occupied" id="occupied-${id}">${cam.vehicle_count}</span>
                <small>Занято</small>
            </div>
            <div>
                <span class="free" id="free-${id}">${cam.free_spots}</span>
                <small>Свободно</small>
            </div>
            <div>
                <span class="capacity" id="capacity-${id}">${cam.capacity}</span>
                <small>Всего</small>
            </div>
        `;
        card.appendChild(stats);

        container.appendChild(card);
    }

    document.querySelectorAll('.toggle-stream').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const id = e.target.dataset.id;
            toggleStream(id);
        });
    });
}

function toggleStream(cameraId) {
    const cam = cameras[cameraId];
    if (!cam) return;

    cam.streaming = !cam.streaming;
    const card = document.getElementById(`camera-${cameraId}`);
    if (!card) return;

    const img = card.querySelector('.camera-image');
    const btn = card.querySelector('.toggle-stream');

    if (cam.streaming) {
        img.src = `${API_BASE}/stream/${cameraId}?t=${Date.now()}`;
        btn.textContent = '🔴 Выключить видео';
        btn.classList.remove('off');
    } else {
        img.src = '';
        btn.textContent = '⚫ Включить видео';
        btn.classList.add('off');
    }
}

let socket;

function connectWebSocket() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log('✅ WebSocket подключён');
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateStats(data);
    };

    socket.onerror = (error) => {
        console.error('❌ WebSocket ошибка:', error);
    };

    socket.onclose = () => {
        console.log('🔌 WebSocket закрыт, переподключение через 2 сек...');
        setTimeout(connectWebSocket, 2000);
    };
}

function updateStats(data) {
    data.forEach(cam => {
        const occupiedSpan = document.getElementById(`occupied-${cam.camera_id}`);
        const freeSpan = document.getElementById(`free-${cam.camera_id}`);
        const capacitySpan = document.getElementById(`capacity-${cam.camera_id}`);

        if (occupiedSpan) occupiedSpan.textContent = cam.vehicle_count;
        if (freeSpan) freeSpan.textContent = cam.free_spots;
        if (capacitySpan) capacitySpan.textContent = cam.capacity;

        if (cameras[cam.camera_id]) {
            cameras[cam.camera_id].vehicle_count = cam.vehicle_count;
            cameras[cam.camera_id].free_spots = cam.free_spots;
        }
    });
}

(async () => {
    await fetchCameras();
    connectWebSocket();
})();