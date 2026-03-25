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
