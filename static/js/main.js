/* ============================
   Piano Jazz Concept — Main JS
   Loaded for all users.
   ============================ */

// Scroll to top
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- Notification bell ---

function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    if (dropdown.style.display === 'flex') {
        dropdown.style.display = 'none';
    } else {
        dropdown.style.display = 'flex';
        fetchNotifications();
    }
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/get_changelog');
        const data = await response.json();
        if (data.success) {
            displayNotifications(data.updates, data.count);
            updateNotificationBadge(data.count);
        } else {
            console.error('Failed to fetch notifications:', data.error);
        }
    } catch (error) {
        console.error('Error fetching notifications:', error);
    }
}

function displayNotifications(updates, count) {
    const content = document.getElementById('notificationContent');

    if (updates.length === 0) {
        content.innerHTML = '<div style="text-align: center; color: #888; padding: 2rem;">Aucune mise \u00e0 jour</div>';
        return;
    }

    content.innerHTML = updates.map((update, idx) => {
        const sectionsHtml = Object.entries(update.sections).map(([sectionName, changes]) => {
            if (changes.length === 0) return '';
            return `
                <div class="notification-section">
                    <div class="notification-section-title">${sectionName}</div>
                    <ul class="notification-changes">
                        ${changes.map(change => `<li>${change}</li>`).join('')}
                    </ul>
                </div>
            `;
        }).join('');

        return `
            <div class="notification-item ${update.is_new ? 'new' : ''}">
                <div class="notification-date" onclick="toggleNotificationDate(${idx})">
                    <span class="notification-date-arrow" id="arrow-${idx}">\u25bc</span>
                    ${update.date}
                </div>
                <div class="notification-sections" id="sections-${idx}" style="display: block;">
                    ${sectionsHtml}
                </div>
            </div>
        `;
    }).join('');

    markNotificationsSeen();
}

function toggleNotificationDate(idx) {
    const sections = document.getElementById(`sections-${idx}`);
    const arrow = document.getElementById(`arrow-${idx}`);
    if (sections.style.display === 'none') {
        sections.style.display = 'block';
        arrow.textContent = '\u25bc';
    } else {
        sections.style.display = 'none';
        arrow.textContent = '\u25b6';
    }
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

async function markNotificationsSeen() {
    try {
        await fetch('/api/mark_changelog_seen', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        setTimeout(() => updateNotificationBadge(0), 2000);
    } catch (error) {
        console.error('Error marking notifications as seen:', error);
    }
}

// Close notifications dropdown when clicking outside
document.addEventListener('click', function(event) {
    const bellContainer = document.querySelector('.notification-bell-container');
    const dropdown = document.getElementById('notificationDropdown');
    if (bellContainer && !bellContainer.contains(event.target) && dropdown) {
        dropdown.classList.remove('show');
    }
});

// --- Alphabet navigation ---

document.addEventListener('DOMContentLoaded', () => {
    fetchNotifications();

    const alphabetNav = document.getElementById('alphabetNav');
    const cards = document.querySelectorAll('.video-card');
    const letters = new Set();

    cards.forEach(card => {
        const letter = card.dataset.letter;
        if (letter && /[A-Z]/.test(letter)) {
            letters.add(letter);
        }
    });

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    alphabet.forEach(letter => {
        const btn = document.createElement('a');
        btn.textContent = letter;
        btn.className = 'letter-btn';
        if (letters.has(letter)) {
            btn.href = '#letter-' + letter;
            btn.onclick = (e) => {
                e.preventDefault();
                jumpToLetter(letter);
            };
        } else {
            btn.classList.add('inactive');
        }
        alphabetNav.appendChild(btn);
    });

    // Linkify URLs in video descriptions
    document.querySelectorAll('.video-description').forEach(el => {
        el.innerHTML = el.innerHTML.replace(
            /(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" style="color:#4a90d9; text-decoration:underline;">$1</a>'
        );
    });
});

function jumpToLetter(letter) {
    const cards = document.querySelectorAll('.video-card');
    for (let card of cards) {
        if (card.dataset.letter === letter) {
            card.scrollIntoView({ behavior: 'smooth', block: 'start' });
            break;
        }
    }
}

// --- Description toggle ---

function toggleDescription(id) {
    const desc = document.getElementById('desc-' + id);
    const btn = document.getElementById('btn-' + id);
    if (desc.classList.contains('truncated')) {
        desc.classList.remove('truncated');
        btn.textContent = 'R\u00e9duire';
    } else {
        desc.classList.add('truncated');
        btn.textContent = 'Lire la suite';
    }
}
