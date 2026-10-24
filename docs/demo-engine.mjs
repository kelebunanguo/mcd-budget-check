// Fictional, browser-only demonstration. All money is stored as integer fen.
export const MENU = Object.freeze({
  beef: { name: '经典牛肉堡', unitFen: 1290, kind: 'main', spicy: false },
  chicken: { name: '香辣脆鸡堡', unitFen: 1390, kind: 'main', spicy: true },
  grilled: { name: '原味烤鸡堡', unitFen: 1490, kind: 'main', spicy: false },
  fish: { name: '酥脆鱼排堡', unitFen: 1590, kind: 'main', spicy: false },
  cola: { name: '无糖可乐', unitFen: 400, kind: 'drink', sugarFree: true },
  tea: { name: '无糖红茶', unitFen: 450, kind: 'drink', sugarFree: true },
  orange: { name: '橙味饮料', unitFen: 550, kind: 'drink', sugarFree: false },
  fries: { name: '中份薯条', unitFen: 550, kind: 'side' },
  largeFries: { name: '大份薯条', unitFen: 800, kind: 'side' },
});

export function parseBudget(value) {
  const text = String(value).trim();
  if (!/^\d{1,4}(?:\.\d{1,2})?$/.test(text)) throw new Error('预算请填写最多两位小数的金额。');
  const [yuan, cents = ''] = text.split('.');
  const fen = Number(yuan) * 100 + Number(cents.padEnd(2, '0'));
  if (fen < 1 || fen > 200000) throw new Error('演示预算范围为 0.01 至 2000 元。');
  return fen;
}

export function money(fen) {
  if (!Number.isSafeInteger(fen)) throw new Error('金额必须使用整数分。');
  return `${fen < 0 ? '-' : ''}${Math.floor(Math.abs(fen) / 100)}.${String(Math.abs(fen) % 100).padStart(2, '0')}`;
}

export function buildPlans({ people, budgetFen, mild = false, sugarFree = true, friesForAll = false, largeFries = false }) {
  if (!Number.isInteger(people) || people < 1 || people > 6) throw new Error('演示支持 1 至 6 人。');
  if (!Number.isSafeInteger(budgetFen) || budgetFen < 1 || budgetFen > 200000) throw new Error('预算金额无效。');
  const side = largeFries ? 'largeFries' : 'fries';
  const baskets = [[], [], []];
  for (let person = 0; person < people; person++) {
    baskets[0].push('beef', 'cola');
    baskets[1].push(mild ? 'grilled' : 'chicken', 'cola', side);
    baskets[2].push(person % 2 === 0 ? 'fish' : 'beef', person % 2 === 0 ? 'cola' : (sugarFree ? 'tea' : 'orange'));
    if (friesForAll) baskets[0].push(side);
  }
  const sharedSides = friesForAll ? people : Math.ceil(people / 2);
  baskets[2].push(...Array(sharedSides).fill(side));
  const labels = [
    { id: 'simple', name: '省一点', subtitle: '主食饮料，刚刚好', color: 'butter' },
    { id: 'complete', name: '吃完整', subtitle: '每人都有一份薯条', color: 'peach' },
    { id: 'variety', name: '换个口味', subtitle: people === 1 ? '换份鱼排，搭点小食' : (friesForAll ? '不同主食，各有小食' : '主食换着吃，小食一起分'), color: 'sage' },
  ];
  const plans = baskets.map((basket, index) => {
    const counts = new Map();
    for (const key of basket) counts.set(key, (counts.get(key) || 0) + 1);
    const items = [...counts].map(([key, quantity]) => ({ key, ...MENU[key], quantity, subtotalFen: MENU[key].unitFen * quantity }));
    const totalFen = items.reduce((sum, item) => sum + item.subtotalFen, 0);
    return { ...labels[index], items, totalFen, people, budgetFen, remainingFen: budgetFen - totalFen,
      perPersonFen: Math.floor((totalFen + Math.floor(people / 2)) / people), withinBudget: totalFen <= budgetFen,
      mainCount: items.filter(item => item.kind === 'main').reduce((sum, item) => sum + item.quantity, 0),
      drinkCount: items.filter(item => item.kind === 'drink').reduce((sum, item) => sum + item.quantity, 0),
    };
  });
  return { plans, withinBudgetCount: plans.filter(plan => plan.withinBudget).length,
    minimumFen: Math.min(...plans.map(plan => plan.totalFen)) };
}

export function receiptText(plan) {
  return ['麦麦预算核价助手｜模拟餐单', '演示数据，非麦当劳实时菜单或价格。',
    `${plan.people} 人 · 总预算 ¥${money(plan.budgetFen)} · 到店自取演示`,
    ...plan.items.map(item => `${item.name} × ${item.quantity}  ¥${money(item.subtotalFen)}`),
    `模拟总价 ¥${money(plan.totalFen)}`, `人均 ¥${money(plan.perPersonFen)}（四舍五入）`,
    `${plan.withinBudget ? '预算余量' : '超出预算'} ¥${money(Math.abs(plan.remainingFen))}`,
    '真实门店与价格请安装 Skill，通过自己的麦当劳 MCP 重新核价。',
    'https://github.com/kelebunanguo/mcd-budget-check'].join('\n');
}
