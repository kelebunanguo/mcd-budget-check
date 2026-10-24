import { buildPlans, money, parseBudget, receiptText } from './demo-engine.mjs';

const $ = id => document.getElementById(id);
const form = $('budget-form');
let current = null;
let selectedId = 'simple';
let inputTimer;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function options() {
  const rawPeople = $('people').value.trim();
  const people = /^\d+$/.test(rawPeople) ? Number(rawPeople) : NaN;
  return { people, budgetFen: parseBudget($('budget').value), mild: $('flavor').value === 'mild',
    sugarFree: $('sugar-free').checked, friesForAll: $('fries-all').checked, largeFries: $('large-fries').checked };
}

function drawCards(plans) {
  const fragment = document.createDocumentFragment();
  for (const plan of plans) {
    const card = element('button', `plan-card ${plan.color}${plan.withinBudget ? '' : ' over'}`);
    card.type = 'button';
    card.dataset.plan = plan.id;
    card.setAttribute('aria-pressed', String(plan.id === selectedId));
    card.setAttribute('aria-label', `${plan.name}，模拟总价 ${money(plan.totalFen)} 元，${plan.withinBudget ? '预算内' : '超预算'}，查看小票`);
    const heading = element('div', 'plan-heading');
    const dot = element('span', 'selection-dot', plan.id === selectedId ? '✓' : '');
    dot.setAttribute('aria-hidden', 'true');
    heading.append(element('h4', '', plan.name), dot);
    const price = element('div', 'plan-price');
    price.append(element('small', '', '¥'), document.createTextNode(money(plan.totalFen)));
    const status = element('div', 'plan-status');
    status.append(element('span', '', `${plan.withinBudget ? '余量' : '超出'} ¥${money(Math.abs(plan.remainingFen))}`), element('span', 'plan-view', plan.id === selectedId ? '正在查看 ✓' : '看小票 ↗'));
    const mains = plan.items.filter(item => item.kind === 'main').map(item => item.name).join(' / ');
    card.append(heading, element('p', 'plan-subtitle', plan.subtitle), price,
      element('p', 'plan-person', `人均 ¥${money(plan.perPersonFen)}`),
      element('p', 'plan-summary', `${mains}\n${plan.mainCount} 份主食 · ${plan.drinkCount} 杯饮料`), status);
    card.addEventListener('click', () => {
      selectedId = plan.id; drawCards(current.plans); drawReceipt(plan);
      $('plan-cards').querySelector(`[data-plan="${plan.id}"]`).focus({ preventScroll: true });
      if (matchMedia('(max-width: 767px)').matches) $('receipt').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' });
    });
    fragment.append(card);
  }
  $('plan-cards').replaceChildren(fragment);
}

function drawReceipt(plan) {
  $('receipt-title').textContent = plan.name;
  $('receipt-context').textContent = `${plan.people} 人 · 总预算 ¥${money(plan.budgetFen)} · 到店自取演示`;
  const lines = plan.items.map(item => {
    const line = element('li');
    const description = element('span', '', `${item.name} × ${item.quantity}`);
    description.append(element('small', '', `单价 ¥${money(item.unitFen)}`));
    line.append(description, element('span', '', `¥${money(item.subtotalFen)}`));
    return line;
  });
  $('receipt-items').replaceChildren(...lines);
  $('receipt-total').replaceChildren(element('small', '', '¥'), document.createTextNode(money(plan.totalFen)));
  $('receipt-person').textContent = `¥${money(plan.perPersonFen)}`;
  $('remaining-box').classList.toggle('over', !plan.withinBudget);
  $('remaining-label').textContent = plan.withinBudget ? '预算还剩' : '已经超出预算';
  $('receipt-remaining').textContent = `¥${money(Math.abs(plan.remainingFen))}`;
  $('budget-fill').style.width = `${Math.min(100, plan.totalFen / plan.budgetFen * 100)}%`;
  $('budget-caption').textContent = plan.withinBudget ? (plan.remainingFen === 0 ? '刚好用完预算，改餐品后记得重新算。' : `这套用了总预算的 ${(plan.totalFen / plan.budgetFen * 100).toFixed(1)}%。`) : '这套不属于预算内方案，可以改搭配或调整预算。';
}

function update({ announceError = true } = {}) {
  try {
    const config = options();
    const next = buildPlans(config);
    current = next;
    $('form-error').hidden = true;
    $('people-less').disabled = config.people <= 1;
    $('people-more').disabled = config.people >= 6;
    $('result-count').textContent = `${next.withinBudgetCount} / 3 套在预算内`;
    $('result-count').style.color = next.withinBudgetCount ? 'var(--green)' : 'var(--red)';
    $('result-context').textContent = `${config.people} 人 · 总预算 ¥${money(config.budgetFen)} · ${config.mild ? '不吃辣' : '口味不限'} · ${config.sugarFree ? '无糖饮料' : '饮料不限'}`;
    $('no-results').hidden = next.withinBudgetCount > 0;
    $('no-results-message').textContent = `当前设置下，最便宜的模拟方案为 ¥${money(next.minimumFen)}。也可以减少人数或取消部分小食。`;
    for (const preset of document.querySelectorAll('[data-budget]')) preset.setAttribute('aria-pressed', String(parseBudget(preset.dataset.budget) === config.budgetFen));
    if (!next.plans.some(plan => plan.id === selectedId)) selectedId = next.plans[0].id;
    drawCards(next.plans);
    drawReceipt(next.plans.find(plan => plan.id === selectedId));
    return true;
  } catch (error) {
    $('form-error').textContent = error.message;
    $('form-error').hidden = !announceError;
    if (announceError) $('result-context').textContent = '输入需要修正，下方保留上一次有效条件的模拟结果。';
    return false;
  }
}

form.addEventListener('submit', event => { event.preventDefault(); clearTimeout(inputTimer); update(); });
form.addEventListener('change', () => { clearTimeout(inputTimer); update(); });
for (const id of ['people', 'budget']) $(id).addEventListener('input', () => {
  clearTimeout(inputTimer);
  inputTimer = setTimeout(() => update(), 220);
});
for (const [id, amount] of [['people-less', -1], ['people-more', 1]]) $(id).addEventListener('click', () => {
  const value = Number($('people').value);
  $('people').value = String(Math.max(1, Math.min(6, (Number.isInteger(value) ? value : 2) + amount)));
  update();
});
for (const preset of document.querySelectorAll('[data-budget]')) preset.addEventListener('click', () => { $('budget').value = `${preset.dataset.budget}.00`; update(); });
$('use-minimum').addEventListener('click', () => {
  if (!current) return;
  $('budget').value = money(current.minimumFen);
  selectedId = current.plans.reduce((a, b) => a.totalFen <= b.totalFen ? a : b).id;
  update();
});
$('try-upgrade').addEventListener('click', () => {
  $('people').value = '2'; $('budget').value = '50.00'; $('flavor').value = 'any';
  $('sugar-free').checked = true; $('fries-all').checked = false; $('large-fries').checked = true;
  selectedId = 'complete'; update();
  $('receipt').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'center' });
});

async function copy(text, button, success) {
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(text);
    const previous = button.textContent;
    button.textContent = success;
    $('copy-status').textContent = success;
    setTimeout(() => { button.textContent = previous; }, 2500);
  } catch {
    $('copy-fallback').value = text;
    $('copy-dialog').showModal();
    $('copy-fallback').select();
  }
}
$('copy-receipt').addEventListener('click', () => {
  const plan = current?.plans.find(plan => plan.id === selectedId);
  if (plan) copy(receiptText(plan), $('copy-receipt'), '模拟餐单已复制 ✓');
});
$('copy-prompt').addEventListener('click', () => copy($('skill-prompt').textContent, $('copy-prompt'), '提问已复制 ✓'));
update();
