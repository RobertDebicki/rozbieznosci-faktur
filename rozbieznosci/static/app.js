const questionForm = document.querySelector('#question-form');
const filterForm = document.querySelector('#filter-form');
const feedback = document.querySelector('#analysis-feedback');

function showFeedback(message, error = false) {
  if (!feedback) return;
  feedback.hidden = false;
  feedback.classList.toggle('error', error);
  feedback.textContent = message;
}

async function runAnalysis(payload) {
  showFeedback('Analizujemy faktury i źródła. Poczekaj chwilę…');
  const buttons = document.querySelectorAll('#question-form button[type="submit"], #filter-form button[type="submit"]');
  buttons.forEach(button => button.disabled = true);
  try {
    const response = await fetch('/api/analyses', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (response.status === 409) {
      showFeedback('Potrzebujemy doprecyzowania, aby wynik był poprawny.');
      const box = document.querySelector('#clarification');
      const message = document.querySelector('#clarification-message');
      const list = document.querySelector('#clarification-options');
      box.hidden = false;
      message.textContent = data.message;
      list.replaceChildren();
      for (const name of data.options || []) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = name;
        button.addEventListener('click', () => {
          const input = document.querySelector('#question');
          const expression = /klienta?\s+(.+?)(?=\s+(?:z ostatniego|z ostatnich|od \d{4}|za okres|powyżej|minimum)|$)/i;
          input.value = expression.test(input.value) ? input.value.replace(expression, `klienta ${name}`) : `Pokaż rozbieżności na fakturach klienta ${name} z ostatniego roku`;
          box.hidden = true;
          input.focus();
        });
        list.append(button);
      }
      return;
    }
    if (!response.ok) {
      const message = typeof data.detail === 'string' ? data.detail : 'Sprawdź podane warunki i spróbuj ponownie.';
      throw new Error(message);
    }
    window.location.assign(`/analyses/${data.id}`);
  } catch (error) {
    showFeedback(error.message || 'Nie udało się przeprowadzić analizy.', true);
  } finally {
    buttons.forEach(button => button.disabled = false);
  }
}

questionForm?.addEventListener('submit', event => {
  event.preventDefault();
  const question = document.querySelector('#question').value.trim();
  if (question) runAnalysis({question});
});
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
  const input = document.querySelector('#question');
  input.value = button.dataset.question;
  input.focus();
}));
filterForm?.addEventListener('submit', event => {
  event.preventDefault();
  const client = document.querySelector('#client-id').value;
  runAnalysis({date_from: document.querySelector('#date-from').value,
    date_to: document.querySelector('#date-to').value,
    client_id: client ? Number(client) : null});
});

document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  const filter = button.dataset.filter;
  document.querySelectorAll('[data-filter]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  document.querySelectorAll('.case-row[data-status]').forEach(row => { row.hidden = filter !== 'all' && row.dataset.status !== filter; });
}));

const dialog = document.querySelector('#source-dialog');
document.querySelectorAll('.source-button').forEach(button => button.addEventListener('click', async () => {
  try {
    const response = await fetch(button.dataset.url);
    if (!response.ok) throw new Error('Źródło jest niedostępne.');
    const source = await response.json();
    document.querySelector('#source-locator').textContent = `Dokument ${source.document_id} · ${source.locator}`;
    document.querySelector('#source-text').textContent = source.text;
    dialog.showModal();
  } catch (error) { window.alert(error.message); }
}));
dialog?.querySelector('.dialog-close')?.addEventListener('click', () => dialog.close());
dialog?.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });

const followupForm = document.querySelector('.followup-form');
document.querySelectorAll('[data-followup-example]').forEach(button => button.addEventListener('click', () => {
  const input = followupForm?.querySelector('input[name="question"]');
  if (input) { input.value = button.dataset.followupExample; input.focus(); }
}));
followupForm?.addEventListener('submit', async event => {
  event.preventDefault();
  const input = followupForm.querySelector('input[name="question"]');
  const button = followupForm.querySelector('button[type="submit"]');
  const feedback = document.querySelector('.followup-feedback');
  const question = input.value.trim();
  if (!question) return;
  button.disabled = true;
  feedback.textContent = 'Szukamy odpowiedzi w tej analizie…';
  const analysisId = followupForm.dataset.analysisId;
  try {
    const response = await fetch(`/api/analyses/${analysisId}/questions`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question, case_id: followupForm.dataset.caseId ? Number(followupForm.dataset.caseId) : null})
    });
    if (!response.ok) throw new Error('Nie udało się zapisać odpowiedzi. Spróbuj ponownie.');
    const answer = await response.json();
    const article = document.createElement('article');
    article.className = 'followup-answer';
    const label = document.createElement('span'); label.textContent = 'Twoje pytanie';
    const heading = document.createElement('strong'); heading.textContent = question;
    const paragraph = document.createElement('p'); paragraph.textContent = answer.text;
    article.append(label, heading, paragraph);
    if (answer.case_id && !followupForm.dataset.caseId) {
      const link = document.createElement('a');
      link.href = `/analyses/${analysisId}/cases/${answer.case_id}`;
      link.textContent = 'Otwórz sprawę →';
      article.append(link);
    }
    if (answer.status === 'new_analysis_required') {
      const link = document.createElement('a'); link.href = '/'; link.textContent = 'Rozpocznij nową analizę →'; article.append(link);
    }
    document.querySelector('.followup-answers').prepend(article);
    input.value = '';
    feedback.textContent = 'Odpowiedź dodana poniżej.';
  } catch (error) {
    feedback.textContent = error.message;
  } finally { button.disabled = false; }
});
