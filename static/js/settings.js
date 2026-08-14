// ==========================================================================
// SETTINGS & API KEY MANAGEMENT
// ==========================================================================

const API_KEY_STORAGE_KEY = 'storyboard_gemini_api_key';

function getStoredApiKey() {
  return localStorage.getItem(API_KEY_STORAGE_KEY) || '';
}

function initSettings() {
  const storedKey = getStoredApiKey();
  if (storedKey) {
    document.getElementById('apiKeyInput').value = storedKey;
    updateApiKeyBadge(true);
  } else {
    // Verificar si el servidor ya tiene la clave en variables de entorno
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        if (data.has_env_key) {
          updateApiKeyBadge(true, "API Key (Servidor)");
        } else {
          updateApiKeyBadge(false);
        }
      })
      .catch(() => updateApiKeyBadge(false));
  }
}

function updateApiKeyBadge(isConfigured, customText = null) {
  const badge = document.getElementById('apiKeyBadge');
  if (!badge) return;

  if (isConfigured) {
    badge.className = 'api-status-badge configured';
    badge.querySelector('.status-text').textContent = customText || 'Gemini 3.5 Conectado';
  } else {
    badge.className = 'api-status-badge unconfigured';
    badge.querySelector('.status-text').textContent = 'Configurar API Key';
  }
}

function openSettingsModal() {
  document.getElementById('settingsModal').classList.remove('hidden');
}

function closeSettingsModal() {
  document.getElementById('settingsModal').classList.add('hidden');
  document.getElementById('testConnectionStatus').classList.add('hidden');
}

function togglePasswordVisibility(inputId) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
  } else {
    input.type = 'password';
  }
}

async function testApiKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  const statusBox = document.getElementById('testConnectionStatus');
  const statusIcon = document.getElementById('connStatusIcon');
  const statusText = document.getElementById('connStatusText');

  if (!key) {
    showToast("Por favor ingresa una API Key para probar.", "error");
    return;
  }

  statusBox.className = 'connection-status-box';
  statusBox.classList.remove('hidden');
  statusIcon.textContent = '⏳';
  statusText.textContent = 'Verificando con Gemini 3.5 API...';

  try {
    const res = await fetch('/api/settings/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key })
    });
    const data = await res.json();

    if (data.success) {
      statusBox.className = 'connection-status-box success';
      statusIcon.textContent = '✅';
      statusText.textContent = '¡Conexión exitosa! Gemini 3.5 listo.';
      showToast("API Key validada correctamente.", "success");
    } else {
      statusBox.className = 'connection-status-box error';
      statusIcon.textContent = '❌';
      statusText.textContent = `Error: ${data.message || 'Clave inválida'}`;
      showToast("Error al validar la clave.", "error");
    }
  } catch (err) {
    statusBox.className = 'connection-status-box error';
    statusIcon.textContent = '❌';
    statusText.textContent = `Error de red: ${err.message}`;
  }
}

function saveApiKey() {
  const key = document.getElementById('apiKeyInput').value.trim();
  if (key) {
    localStorage.setItem(API_KEY_STORAGE_KEY, key);
    updateApiKeyBadge(true);
    showToast("API Key guardada en tu navegador.", "success");
  } else {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    updateApiKeyBadge(false);
  }
  closeSettingsModal();
}

function clearApiKey() {
  localStorage.removeItem(API_KEY_STORAGE_KEY);
  document.getElementById('apiKeyInput').value = '';
  updateApiKeyBadge(false);
  showToast("API Key eliminada.", "info");
}

document.addEventListener('DOMContentLoaded', initSettings);
