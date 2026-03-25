/* ============================
   Piano Jazz Concept — Feedback JS
   ============================ */

async function sendFeedback() {
    const text = document.getElementById('feedbackText').value.trim();
    if (!text) return;
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Envoi en cours...';
    try {
        const d = [99,111,108,105,110,46,109,105,103,110,111,116,49,64,103,109,97,105,108,46,99,111,109];
        const addr = d.map(c => String.fromCharCode(c)).join('');
        const formData = new FormData();
        formData.append('message', text);
        formData.append('_subject', 'Retour \u2014 Piano Jazz Concept');
        formData.append('_captcha', 'false');
        formData.append('_template', 'box');
        await fetch('https://formsubmit.co/ajax/' + addr, {
            method: 'POST',
            body: formData
        });
        document.getElementById('feedbackText').value = '';
        btn.textContent = 'Envoy\u00e9 !';
        setTimeout(() => {
            document.getElementById('feedbackModal').style.display = 'none';
            btn.textContent = 'Envoyer \u2709\ufe0f';
            btn.disabled = false;
        }, 1500);
    } catch(e) {
        btn.textContent = 'Erreur, r\u00e9essayez';
        btn.disabled = false;
    }
}
