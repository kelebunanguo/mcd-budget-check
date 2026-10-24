# 报价核算输入

将真实请求与对应的 `calculate-price` **业务响应**保存为以下结构。原始数据仅保存在本地私有目录，不要提交账号、地址、券码或 Token。预算固定为人民币总预算，精确到分。

```json
{
  "budget_yuan": "50.00",
  "people": 2,
  "context": {
    "storeCode": "从门店查询取得",
    "orderType": 1,
    "beType": 1,
    "needTableware": false
  },
  "plans": [
    {
      "label": "候选方案名称",
      "price_unit": "fen",
      "request": {},
      "response": {}
    }
  ]
}
```

上面的空对象为结构说明，不能用于真实报价。`request` 必须是实际发出的完整计价参数，`response` 为含 `success/code/datetime/data` 的原始业务对象（SDK 辅助脚本的 `business` 字段）。`context` 为所有方案共享的门店、取餐方式、预约时间和餐具选择；若有 `beCode` 或 `reservationDate`，两处均须一致。脚本不接受空餐品，也不接受返回餐品与请求编码/数量不一致的报价。

```bash
python3 scripts/budget_report.py private/quotes.json
python3 scripts/budget_report.py private/quotes.json --json
```

退出码 0 表示至少一个成功且预算内的报价；2 表示输入无效或没有预算内报价。单个无效方案会列出排除原因，不使其他成功方案失效。所有超预算报价仍展示，但不计入合格方案。

脚本只做确定性核算，不负责判断每人吃得够不够，也不能证明输入来自真实服务。真实调用证据与份量核验必须由实际流程提供；离线示例不能替代联调。
