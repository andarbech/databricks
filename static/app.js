'use strict';
const $ = (id) => document.getElementById(id);
const labels = {open: 'Open', in_progress: 'In progress', resolved: 'Resolved'};
let tickets = [], selectedId = null, conversationVersion = 0, messagesReady = false;
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function notify(message, error = false) {
  $('notice').textContent = message;
  $('notice').className = error ? 'error' : '';
  $('notice').hidden = false;
}
function date(value) { return new Date(value).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'}); }
async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 75000);
  try {
    const response = await fetch(path, {...options, signal: controller.signal, headers: {'Content-Type': 'application/json', ...(options.headers || {})}});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}). Refresh and try again.`);
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Refresh to check whether your changes were saved.');
    throw error;
  } finally { clearTimeout(timer); }
}
function busy(form, value) {
  form.querySelectorAll('button,input,textarea,select').forEach(element => { element.disabled = value; });
}
function renderTickets() {
  const filter = $('filter').value;
  const visible = tickets.filter(ticket => filter === 'all' || ticket.status === filter);
  $('ticket-list').replaceChildren();
  if (!visible.length) $('ticket-list').append(node('p', 'empty', tickets.length ? 'No tickets match this status. Choose another filter.' : 'No tickets yet. Create your first request below.'));
  for (const ticket of visible) {
    const button = node('button', 'ticket' + (selectedId === ticket.ticket_id ? ' selected' : ''));
    button.type = 'button';
    button.setAttribute('aria-pressed', String(selectedId === ticket.ticket_id));
    const top = node('span', 'ticket-top');
    top.append(node('span', '', `#${ticket.ticket_id}`), node('span', `badge ${ticket.status}`, labels[ticket.status]));
    button.append(top, node('span', 'ticket-title', ticket.title), node('span', 'ticket-author', ticket.created_by));
    button.addEventListener('click', () => selectTicket(ticket.ticket_id));
    $('ticket-list').append(button);
  }
  $('count-all').textContent = tickets.length;
  for (const status of Object.keys(labels)) $('count-' + status).textContent = tickets.filter(ticket => ticket.status === status).length;
}
function renderSelectedTicket() {
  const ticket = tickets.find(ticket => ticket.ticket_id === selectedId);
  if (!ticket) return;
  $('ticket-number').textContent = `TICKET #${ticket.ticket_id}`;
  $('selected-title').textContent = ticket.title;
  $('ticket-meta').textContent = `Created by ${ticket.created_by} · ${date(ticket.created_at)}`;
  $('status').value = ticket.status;
}
async function loadTickets() {
  $('refresh').disabled = true;
  try {
    const data = await api('/tickets');
    tickets = data.tickets;
    renderTickets();
    renderSelectedTicket();
    $('freshness').textContent = `All tickets · Refreshed ${date(new Date())}`;
  } catch (error) {
    if (!tickets.length) $('ticket-list').replaceChildren(node('p', 'empty error', 'Tickets could not be loaded. Use Refresh tickets to try again.'));
    $('freshness').textContent = 'Refresh failed. Previously loaded data may be out of date.';
    throw error;
  } finally { $('refresh').disabled = false; }
}
async function selectTicket(id) {
  const version = ++conversationVersion;
  const changed = selectedId !== id;
  selectedId = id;
  messagesReady = false;
  if (changed) $('message-text').value = '';
  renderTickets();
  renderSelectedTicket();
  $('selection-empty').hidden = true;
  $('conversation').hidden = false;
  $('message-count').textContent = '';
  $('messages').replaceChildren(node('p', 'empty', 'Loading conversation…'));
  busy($('message-form'), true);
  try {
    const data = await api(`/tickets/${id}/messages`);
    if (version !== conversationVersion) return;
    $('messages').replaceChildren();
    $('message-count').textContent = `${data.messages.length} messages`;
    if (!data.messages.length) $('messages').append(node('p', 'empty', 'No messages yet. Start the conversation below.'));
    for (const message of data.messages) {
      const article = node('article', 'message');
      const header = node('div', 'message-header');
      header.append(node('strong', '', message.author), node('time', '', date(message.created_at)));
      article.append(header, node('p', '', message.message_text));
      $('messages').append(article);
    }
    messagesReady = true;
  } catch (error) {
    if (version !== conversationVersion) return;
    $('messages').replaceChildren(node('p', 'empty error', error.message));
    notify(error.message, true);
  } finally {
    if (version === conversationVersion) busy($('message-form'), !messagesReady);
  }
}
$('filter').addEventListener('change', renderTickets);
$('refresh').addEventListener('click', async () => {
  try { await loadTickets(); if (selectedId !== null) await selectTicket(selectedId); }
  catch (error) { notify(error.message, true); }
});
$('ticket-form').addEventListener('submit', async event => {
  event.preventDefault();
  const title = $('title').value.trim();
  if (!title) return notify('Enter a ticket title.', true);
  busy(event.currentTarget, true);
  try {
    const data = await api('/tickets', {method: 'POST', body: JSON.stringify({title})});
    $('title').value = '';
    $('filter').value = 'all';
    notify('Ticket created.');
    await loadTickets();
    await selectTicket(data.ticket.ticket_id);
  } catch (error) { notify(error.message, true); }
  finally { busy($('ticket-form'), false); }
});
$('message-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (selectedId === null || !messagesReady) return;
  const id = selectedId, messageText = $('message-text').value.trim();
  if (!messageText) return notify('Enter a message.', true);
  busy($('message-form'), true);
  try {
    await api(`/tickets/${id}/messages`, {method: 'POST', body: JSON.stringify({message_text: messageText})});
    if (selectedId === id) { $('message-text').value = ''; await selectTicket(id); }
    notify('Message added.');
  } catch (error) { notify(error.message, true); }
  finally { busy($('message-form'), !messagesReady); }
});
$('status-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (selectedId === null) return;
  const id = selectedId, status = $('status').value;
  busy($('status-form'), true);
  try {
    const data = await api(`/tickets/${id}`, {method: 'PATCH', body: JSON.stringify({status})});
    tickets = tickets.map(ticket => ticket.ticket_id === id ? data.ticket : ticket);
    renderTickets(); renderSelectedTicket();
    notify('Ticket status updated.');
  } catch (error) { renderSelectedTicket(); notify(error.message, true); }
  finally { busy($('status-form'), false); }
});
loadTickets().catch(error => notify(error.message, true));
