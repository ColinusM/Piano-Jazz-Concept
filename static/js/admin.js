/* ============================
   Piano Jazz Concept — Admin JS
   Loaded only for admin users.
   ============================ */

// --- Undo system ---

let undoStack = [];
let undoTimeout = null;

document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undoLastChange();
    }
});

function showUndoNotification(message) {
    const notification = document.getElementById('undoNotification');
    const messageSpan = document.getElementById('undoMessage');
    messageSpan.textContent = message;
    notification.classList.add('show');
    if (undoTimeout) {
        clearTimeout(undoTimeout);
    }
    undoTimeout = setTimeout(() => {
        notification.classList.remove('show');
    }, 5000);
}

function hideUndoNotification() {
    const notification = document.getElementById('undoNotification');
    notification.classList.remove('show');
}

async function undoLastChange() {
    if (undoStack.length === 0) return;

    const lastChange = undoStack.pop();
    hideUndoNotification();

    try {
        if (lastChange.type === 'delete') {
            const response = await fetch('/api/restore_song', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ song_id: lastChange.songId })
            });
            const result = await response.json();
            if (result.success) {
                lastChange.cardParent.insertAdjacentHTML('beforeend', lastChange.cardHTML);
                const notification = document.getElementById('undoNotification');
                const messageSpan = document.getElementById('undoMessage');
                messageSpan.textContent = '\u2713 Song restored';
                notification.classList.add('show');
                setTimeout(() => { notification.classList.remove('show'); }, 2000);
            }
        } else {
            const response = await fetch('/api/update_song', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: lastChange.songId,
                    field: lastChange.field,
                    value: lastChange.oldValue
                })
            });
            const result = await response.json();
            if (result.success) {
                const editableField = document.querySelector(
                    `[data-id="${lastChange.songId}"][data-field="${lastChange.field}"]`
                );
                if (editableField) {
                    const fieldValue = editableField.querySelector('.field-value');
                    fieldValue.textContent = lastChange.oldValue || 'Non renseign\u00e9';
                }
                const notification = document.getElementById('undoNotification');
                const messageSpan = document.getElementById('undoMessage');
                messageSpan.textContent = '\u2713 Modification annul\u00e9e';
                notification.classList.add('show');
                setTimeout(() => { notification.classList.remove('show'); }, 2000);
            }
        }
    } catch (error) {
        alert('Erreur r\u00e9seau: ' + error.message);
    }
}

// --- Inline field editing ---

function editField(editIcon) {
    const editableField = editIcon.parentElement;
    const fieldValue = editableField.querySelector('.field-value');
    const currentValue = fieldValue.textContent.trim();
    const songId = editableField.dataset.id;
    const field = editableField.dataset.field;

    const linkParent = fieldValue.closest('a.filter-link');
    const elementToHide = linkParent || fieldValue;

    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentValue === 'Non renseign\u00e9' ? '' : currentValue;
    input.dataset.originalValue = currentValue;

    input.addEventListener('blur', () => saveField(input, fieldValue, linkParent, songId, field));
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            input.blur();
        } else if (e.key === 'Escape') {
            fieldValue.textContent = input.dataset.originalValue;
            elementToHide.style.display = '';
            input.remove();
            editIcon.style.display = '';
        }
    });

    elementToHide.style.display = 'none';
    editIcon.style.display = 'none';
    editableField.insertBefore(input, elementToHide);
    input.focus();
    input.select();
}

async function saveField(input, fieldValue, linkParent, songId, field) {
    const newValue = input.value.trim();
    const originalValue = input.dataset.originalValue;
    const elementToShow = linkParent || fieldValue;

    if (newValue === originalValue || (newValue === '' && originalValue === 'Non renseign\u00e9')) {
        elementToShow.style.display = '';
        input.remove();
        return;
    }

    const oldValue = originalValue === 'Non renseign\u00e9' ? null : originalValue;

    try {
        const response = await fetch('/api/update_song', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: songId,
                field: field,
                value: newValue || null
            })
        });
        const result = await response.json();

        if (result.success) {
            undoStack.push({
                songId: songId,
                field: field,
                oldValue: oldValue,
                newValue: newValue || null
            });
            fieldValue.textContent = newValue || 'Non renseign\u00e9';
            elementToShow.style.display = '';
            input.remove();
            showUndoNotification(`Modifi\u00e9: ${field} \u2192 "${newValue || 'vide'}"`);
        } else {
            alert('Erreur lors de la sauvegarde: ' + (result.error || 'Unknown error'));
            elementToShow.style.display = '';
            input.remove();
        }
    } catch (error) {
        alert('Erreur r\u00e9seau: ' + error.message);
        elementToShow.style.display = '';
        input.remove();
    }
}

// --- Category editing ---

function toggleCategoryDropdown(event, itemId, currentCategory) {
    event.stopPropagation();
    document.querySelectorAll('.category-dropdown').forEach(dd => {
        if (dd.id !== `category-dropdown-${itemId}`) {
            dd.classList.remove('show');
        }
    });
    const dropdown = document.getElementById(`category-dropdown-${itemId}`);
    dropdown.classList.toggle('show');
}

async function updateCategory(itemId, newCategory) {
    const view = new URLSearchParams(window.location.search).get('view') || 'songs';
    try {
        const response = await fetch('/api/update_category', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: itemId,
                category: newCategory,
                view: view
            })
        });
        const result = await response.json();
        if (result.success) {
            document.getElementById(`category-dropdown-${itemId}`).classList.remove('show');
            location.reload();
        } else {
            alert('\u274c Error: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        alert('\u274c Network error: ' + error.message);
    }
}

// Close category dropdowns when clicking outside
document.addEventListener('click', () => {
    document.querySelectorAll('.category-dropdown').forEach(dd => {
        dd.classList.remove('show');
    });
});


// --- YouTube Description Updater ---

function openYouTubeUpdateModal() {
    document.getElementById('ytModal1').style.display = 'flex';
}

function startYouTubeOAuth() {
    document.getElementById('ytModal1').style.display = 'none';
    window.location.href = '/api/youtube-oauth-start';
}

// Auto-open Modal 2 after OAuth redirect
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);

    if (params.get('youtube_update') === 'analyze') {
        // Clean URL without reloading
        const url = new URL(window.location);
        url.searchParams.delete('youtube_update');
        window.history.replaceState({}, '', url);
        runYouTubeAnalysis();
    }

    if (params.get('youtube_update') === 'error') {
        const url = new URL(window.location);
        url.searchParams.delete('youtube_update');
        window.history.replaceState({}, '', url);
        alert("L'autorisation n'a pas fonctionné. Il est possible que l'adresse Gmail avec laquelle vous échangez avec Colin ne soit pas la même que celle liée à votre chaîne YouTube. Contactez Colin en lui indiquant l'adresse Gmail associée à votre chaîne YouTube.");
    }
});

async function runYouTubeAnalysis() {
    const modal = document.getElementById('ytModal2');
    const title = document.getElementById('ytModal2Title');
    const content = document.getElementById('ytAnalysisContent');
    const actions = document.getElementById('ytAnalysisActions');

    modal.style.display = 'flex';
    actions.style.display = 'none';
    title.textContent = '📊 Analyse en cours...';
    content.innerHTML = '<div style="text-align:center; color:#888; padding:2rem;"><div class="yt-spinner"></div><br>Analyse de vos vidéos YouTube...<br><small>(peut prendre 30 secondes)</small></div>';

    try {
        const response = await fetch('/api/youtube-analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();

        if (!result.success) {
            if (result.error === 'not_authenticated') {
                content.innerHTML = '<div style="text-align:center; color:#c00; padding:1rem;">Session expirée. Relancez l\'outil depuis le bouton 🔗.</div>';
            } else {
                content.innerHTML = '<div style="color:#c00; padding:1rem;">Erreur : ' + result.error + '</div>';
            }
            title.textContent = '❌ Erreur';
            return;
        }

        title.textContent = '📊 Analyse terminée';
        const totalActions = (result.to_replace || 0) + (result.to_add || 0);
        content.innerHTML = `
            <div style="font-size:0.95rem; color:#333;">
                <p style="margin-bottom:0.8rem;">📹 <strong>${result.total}</strong> vidéos analysées</p>
                ${result.to_replace > 0 ? `<p style="margin-bottom:0.5rem; color:#c00;">🔄 <strong>${result.to_replace}</strong> vidéo(s) — lien à remplacer</p>` : ''}
                ${result.to_add > 0 ? `<p style="margin-bottom:0.5rem; color:#36c;">➕ <strong>${result.to_add}</strong> vidéo(s) — lien à ajouter</p>` : ''}
                ${result.already_correct > 0 ? `<p style="margin-bottom:0.5rem; color:#090;">✅ <strong>${result.already_correct}</strong> vidéo(s) déjà à jour</p>` : ''}
            </div>
        `;

        if (totalActions > 0) {
            const testCount = Math.min(3, totalActions);
            document.getElementById('ytTestBtn').textContent = '🧪 Tester sur ' + testCount + ' vidéo' + (testCount > 1 ? 's' : '');
            document.getElementById('ytAllBtn').innerHTML = '✅ Tout appliquer (' + totalActions + ' vidéo' + (totalActions > 1 ? 's' : '') + ')';

            // Show which videos will be tested
            if (result.test_preview && result.test_preview.length > 0) {
                let previewHtml = '<p style="margin-top:0.8rem; font-size:0.85rem; color:#555;">Le test sera effectué sur :</p>';
                previewHtml += '<ul style="list-style:none; padding:0; margin:0.3rem 0 0 0;">';
                for (const title of result.test_preview) {
                    previewHtml += '<li style="font-size:0.85rem; color:#333; margin-bottom:0.3rem;">📹 ' + title + '</li>';
                }
                previewHtml += '</ul>';
                content.innerHTML += previewHtml;
            }

            // If only 1-3 videos, hide test button — just show "Tout appliquer"
            if (totalActions <= 3) {
                document.getElementById('ytTestBtn').style.display = 'none';
            } else {
                document.getElementById('ytTestBtn').style.display = '';
            }

            actions.style.display = 'block';
        } else {
            content.innerHTML += '<p style="margin-top:1rem; color:#090; font-weight:600;">Toutes vos descriptions sont déjà à jour !</p>';
        }
    } catch (error) {
        title.textContent = '❌ Erreur';
        content.innerHTML = '<div style="color:#c00; padding:1rem;">Erreur réseau : ' + error.message + '</div>';
    }
}

async function applyYouTubeUpdate(mode) {
    const content = document.getElementById('ytAnalysisContent');
    const actions = document.getElementById('ytAnalysisActions');
    const title = document.getElementById('ytModal2Title');
    const count = mode === 'test' ? 3 : parseInt(document.getElementById('ytUpdateCount').textContent) || 0;
    const estimate = Math.max(10, Math.ceil(count * 2));

    actions.style.display = 'none';
    title.textContent = '⏳ Mise à jour en cours...';
    content.innerHTML = '<div style="text-align:center; color:#888; padding:2rem;">'
        + '<div class="yt-spinner"></div><br>'
        + 'Modification de ' + count + ' vidéo(s)...<br>'
        + '<small>Cela peut prendre environ ' + estimate + ' secondes.<br>Merci de ne pas fermer cette page.</small></div>';

    try {
        const response = await fetch('/api/youtube-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: mode })
        });
        const result = await response.json();

        document.getElementById('ytModal2').style.display = 'none';
        showYouTubeResults(result, mode);
    } catch (error) {
        content.innerHTML = '<div style="color:#c00; padding:1rem;">Erreur réseau : ' + error.message + '</div>';
    }
}

function showYouTubeResults(result, mode) {
    const modal = document.getElementById('ytModal3');
    const title = document.getElementById('ytResultsTitle');
    const content = document.getElementById('ytResultsContent');
    const actions = document.getElementById('ytResultsActions');

    modal.style.display = 'flex';

    if (!result.success) {
        title.textContent = '❌ Erreur';
        content.innerHTML = '<p style="color:#c00;">' + result.error + '</p>';
        actions.style.display = 'none';
        return;
    }

    title.textContent = mode === 'test' ? '🧪 Test terminé' : '✅ Mise à jour terminée';

    let html = '';

    if (result.updated && result.updated.length > 0) {
        html += '<p style="color:#090; font-weight:600; margin-bottom:0.8rem;">✅ ' + result.updated.length + ' vidéo(s) mise(s) à jour :</p>';
        html += '<ul style="list-style:none; padding:0; margin:0 0 1rem 0;">';
        for (const v of result.updated) {
            html += '<li style="margin-bottom:0.5rem; font-size:0.9rem;">';
            html += '<a href="' + v.youtube_url + '" target="_blank" style="color:#4a90d9; text-decoration:underline;">' + v.title + '</a>';
            html += '</li>';
        }
        html += '</ul>';

        if (mode === 'test') {
            html += '<p style="color:#555; font-size:0.85rem; background:#f8f8f8; padding:0.8rem; border-radius:8px;">';
            html += 'Cliquez sur les liens ci-dessus pour vérifier sur YouTube que les descriptions sont correctes.';
            html += '</p>';
        }
    }

    if (result.failed && result.failed.length > 0) {
        html += '<p style="color:#c00; font-weight:600; margin:1rem 0 0.5rem 0;">❌ ' + result.failed.length + ' échec(s) :</p>';
        html += '<ul style="list-style:none; padding:0; margin:0 0 1rem 0;">';
        for (const v of result.failed) {
            html += '<li style="margin-bottom:0.3rem; font-size:0.85rem; color:#c00;">' + v.title + ' — ' + v.error + '</li>';
        }
        html += '</ul>';
    }

    if (result.quota_exceeded) {
        html += '<p style="color:#c90; font-weight:600; margin-top:1rem;">⚠️ Limite YouTube atteinte pour aujourd\'hui. Revenez demain et relancez l\'outil pour terminer.</p>';
    }

    content.innerHTML = html;

    if (result.remaining > 0 && !result.quota_exceeded) {
        actions.style.display = 'block';
        actions.innerHTML = '<button onclick="applyYouTubeUpdateFromResults()" '
            + 'style="width:100%; padding:0.8rem; background:#333; color:#fff; border:none; border-radius:8px; font-size:1rem; cursor:pointer;">'
            + '✅ Appliquer aux ' + result.remaining + ' vidéos restantes</button>';
    } else {
        actions.style.display = 'none';
    }
}

async function applyYouTubeUpdateFromResults() {
    const remainingBtn = document.getElementById('ytResultsActions').querySelector('button');
    const count = remainingBtn ? parseInt(remainingBtn.textContent.match(/\d+/)?.[0]) || 0 : 0;
    const estimate = Math.max(10, Math.ceil(count * 2));

    document.getElementById('ytModal3').style.display = 'none';

    const modal2 = document.getElementById('ytModal2');
    const title2 = document.getElementById('ytModal2Title');
    const content2 = document.getElementById('ytAnalysisContent');
    const actions2 = document.getElementById('ytAnalysisActions');

    modal2.style.display = 'flex';
    actions2.style.display = 'none';
    title2.textContent = '⏳ Mise à jour en cours...';
    content2.innerHTML = '<div style="text-align:center; color:#888; padding:2rem;">'
        + '<div class="yt-spinner"></div><br>'
        + 'Modification de ' + count + ' vidéo(s)...<br>'
        + '<small>Cela peut prendre environ ' + estimate + ' secondes.<br>Merci de ne pas fermer cette page.</small></div>';

    try {
        const response = await fetch('/api/youtube-apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: 'all' })
        });
        const result = await response.json();
        modal2.style.display = 'none';
        showYouTubeResults(result, 'all');
    } catch (error) {
        content2.innerHTML = '<div style="color:#c00;">Erreur réseau : ' + error.message + '</div>';
    }
}
