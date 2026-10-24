import test from 'node:test';
import assert from 'node:assert/strict';
import { buildPlans, parseBudget, money, receiptText } from '../docs/demo-engine.mjs';

test('budget parsing preserves cents and rejects unsupported precision and ranges', () => {
  assert.equal(parseBudget('50.01'), 5001);
  assert.equal(parseBudget('0.01'), 1);
  assert.equal(money(-1), '-0.01');
  for (const value of ['1.001', '', '-1', 'Infinity', '1e2', '2000.01', '0']) assert.throws(() => parseBudget(value));
});

test('every scenario keeps one main and one drink per person and enforces preferences', () => {
  for (let people = 1; people <= 6; people++) for (const mild of [false, true]) for (const sugarFree of [false, true]) for (const friesForAll of [false, true]) for (const largeFries of [false, true]) {
    const result = buildPlans({ people, budgetFen: 10000, mild, sugarFree, friesForAll, largeFries });
    for (const plan of result.plans) {
      assert.equal(plan.mainCount, people);
      assert.equal(plan.drinkCount, people);
      assert.equal(plan.totalFen, plan.items.reduce((sum, item) => sum + item.unitFen * item.quantity, 0));
      if (mild) assert.ok(plan.items.every(item => !item.spicy));
      if (sugarFree) assert.ok(plan.items.filter(item => item.kind === 'drink').every(item => item.sugarFree));
      const sides = plan.items.filter(item => item.kind === 'side');
      if (friesForAll) assert.equal(sides.reduce((sum, item) => sum + item.quantity, 0), people);
      assert.ok(sides.every(item => item.key === (largeFries ? 'largeFries' : 'fries')));
    }
  }
});

test('one cent over is excluded, exact budget accepted, upgrade crosses 50 yuan', () => {
  const exact = buildPlans({ people: 2, budgetFen: 3380 });
  assert.equal(exact.withinBudgetCount, 1);
  assert.equal(exact.plans[0].remainingFen, 0);
  assert.equal(buildPlans({ people: 2, budgetFen: 3379 }).withinBudgetCount, 0);
  const upgraded = buildPlans({ people: 2, budgetFen: 5000, largeFries: true }).plans[1];
  assert.equal(upgraded.totalFen, 5180);
  assert.equal(upgraded.remainingFen, -180);
  assert.equal(upgraded.withinBudget, false);
  assert.match(receiptText(upgraded), /虚|演示数据/);
  assert.match(receiptText(upgraded), /超出预算 ¥1.80/);
});

test('invalid people and fractional fen cannot produce plans', () => {
  for (const people of [0, 7, 1.5, NaN, '2']) assert.throws(() => buildPlans({ people, budgetFen: 5000 }));
  assert.throws(() => buildPlans({ people: 2, budgetFen: 5000.1 }));
});
