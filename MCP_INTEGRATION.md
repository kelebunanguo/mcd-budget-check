# MCP 接入与业务价值

项目：麦麦预算核价助手（mcd-budget-check）。独立参赛作品，非麦当劳官方产品。

## 使用方式

官方 Server：`https://mcp.mcd.cn`；Streamable HTTP；本地私有 Token 以 Bearer 请求头发送，仅到该官方地址。核心 Skill 优先调用宿主客户端已连接的 MCP；辅助脚本通过官方 Python SDK 直连。真实工具 schema 优先于网页示例，避免版本变化导致传参错误。

## 实际调用链

已联调的到店链路：

`tools/list → query-nearby-stores → 选定测试门店 → query-meals + query-store-coupons → query-meal-detail → 构建完整餐品组合 → calculate-price → budget_report.py 比较预算`

这里的门店选择是公开地标测试场景的固定选店；正式对话会让用户从结果中选择。`query-store-coupons` 在本次测试门店返回空数组，因此测试使用无券方案，并未领取券或假设存在优惠。

已实现但尚待真实验收的外送分支：

`用户明确选择外送 → delivery-query-addresses → 用户选地址 → delivery-query-stores → 相同菜单/券/详情/计价链路`

本次未读取用户配送地址，外送分支尚无真实配送报价证据。`now-time-info`、`list-nutrition-foods` 为可选只读能力，不冒充已完成相关场景验收。

## 工具与决策

| Tool | 作用与约束 |
|---|---|
| query-nearby-stores | 将用户给定城市/地点映射为实际门店，不猜 storeCode |
| query-meals | 读取门店与就餐方式下的当前可售餐品、价格及优惠类型 |
| query-store-coupons | 只选当前门店和就餐方式可用券，不把券面价格视作整单总价 |
| query-meal-detail | 查明套餐主食/饮料等子项，按真实选项和数量限制组装 |
| calculate-price | 对整单核价，取得含相关费用的官方总价并核对返回餐品 |

预算比较使用人民币整数分。总价不重复叠加配送费/餐具费，不把购卡条件价直接当作无需购卡的最终价。报价改变就餐方式、门店、时间或餐品时重新计算。

## 业务价值

将“预算是多少、每人需要什么”转换为用户可比较的实际餐品组合。核心价值在于逐人需求核验、真实套餐组成、可用优惠与最终价格的一致性。只比较生成的候选，不宣称穷举所有组合或全局最低价。

每套方案展示总价、人均和预算余量；失败方案不掩盖，超额方案不能列为预算内。白名单直连脚本不接受下单、领券或扣积分工具，流程终点是报价。

## 证据与保护

公开结果见 [VALIDATION.md](VALIDATION.md)。原始响应留在本地私有工作区，公开文件不含 Token、会员标识、券码或配送地址。`mcp-config.example.json` 只含环境变量占位符。

活动及接口来源：[官方接口文档](https://open.mcd.cn/mcp/doc)、[官方赛事规则](https://github.com/M-China/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)。
