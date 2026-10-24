# 麦麦预算核价助手 · mcd-budget-check

说清人数、预算、地点和口味，获得经麦当劳官方 MCP 实时计价的点餐方案。适合想控制一顿饭支出、又不想逐项研究菜单的个人与小组。

这是**对话 Skill**：由支持 `SKILL.md` 的 AI 客户端完成需求确认、实时查询、候选构建与解释。Python 脚本提供可选的只读直连及确定性核算，不是一个独立的自然语言聊天网站。首版支持到店自取和麦乐送已有地址，流程止于报价，由用户在官方渠道自行下单。

## 使用

1. 下载本项目，把整个目录导入支持本地 Skill 的客户端，入口文件是 [SKILL.md](SKILL.md)。不同客户端的导入入口与技能目录不同，按其文档操作。也可在本地助手中明确指定该文件，让助手按其中流程执行；仅复制文件不代表所有客户端都已完成安装。
2. 在客户端连接麦当劳 MCP：`https://mcp.mcd.cn`，Streamable HTTP；认证请求头为 `Authorization: Bearer <本地 Token>`。公开模板为 [mcp-config.example.json](mcp-config.example.json)，仅含环境变量占位符。`${MCD_MCP_TOKEN}` 是脱敏配置的表示方式，是否能直接展开取决于客户端；不支持时使用客户端私有的凭据输入功能，不要提交填入真实 Token 的配置。
3. 开始对话，例如：

> 使用 $mcd-budget-check，上海人民广场附近到店自取，现在吃，2 人总预算 50 元，每人至少一份主食和一杯饮料。比较几套不用新买会员卡的方案，先让我选择门店。

> 使用 $mcd-budget-check，麦乐送到我的已有地址，3 人总预算 100 元，其中一人不吃辣，每人一份主食，饮料需要无糖，含配送费。先核对地址和份量，再比较真实总价。

> 把刚才方案的一杯饮料换掉，重新计价，看看会不会超过预算。

输出包括餐品及数量、逐人分配、官方总价、人均、预算余量、门店、用餐方式、计价时间与方案取舍。若预算太低或部分候选失败，会明确说明；不会用估价冒充官方报价。

Codex 的本地项目可将该目录放入当前工作目录的 `.agents/skills/mcd-budget-check`（也支持目录软链接）。个人级目录为 `~/.agents/skills`。Codex 自动检测技能变动，若未出现再重启；这些路径和行为见 [OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)。本项目本地交付会在当前工作区建立目录链接，源码仍在 `outputs/mcd-budget-check`。

## 未连接客户端 MCP 时的可选直连

Skill 核心和预算核算只需 Python 3.10+ 标准库。只读直连脚本使用官方 MCP Python SDK，安装到项目自己的虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p private
chmod 700 private
```

Windows 下将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。用编辑器创建 `private/mcd.local.env`，填入 `MCD_MCP_TOKEN=` 及自己的 Token。此文件不要上传、截图或发到对话中，也不要把 Token 当作命令行参数。POSIX 系统执行 `chmod 600 private/mcd.local.env`。

```bash
.venv/bin/python scripts/mcd_readonly.py --env-file private/mcd.local.env --out private/tools.json tools
```

先读取 `private/tools.json` 的实际 schema，再创建 `private/stores-args.json`：

```json
{"searchType": 2, "beType": 1, "city": "上海市", "keyword": "人民广场"}
```

```bash
.venv/bin/python scripts/mcd_readonly.py --env-file private/mcd.local.env --out private/stores-result.json call query-nearby-stores --args-file private/stores-args.json
```

每次调用会先发现并校验实时工具 schema。文件输出采用仅本人可读写的权限且不覆盖已有文件；每次使用新的输出文件名。账户数据可能包含地址和券标识，只存私有目录。网络日志默认关闭，错误消息不输出 Token 或远端原文。缺依赖、缺 Token、业务失败或 MCP 错误返回非零退出码。暂未实现自动重试，失败后按 Skill 中规则判断是否重试。

直连支持九项白名单查询与计价，不提供订单、积分兑换、抽奖、领券或地址新增命令。固定官方域名，不向其他服务器发送 Token。

## 预算核算与测试

输入格式见 [references/report-input.md](references/report-input.md)。这一步只验证金额及报价请求是否对应，人数份量和口味由 Skill 在实时菜单/套餐详情上逐项核验。

```bash
python3 scripts/budget_report.py private/quotes.json
python3 -m unittest discover -s tests -v
```

[VALIDATION.md](VALIDATION.md) 记录已执行的真实链路、测试结果和未验证项。已成功的历史报价仅用于展示验证经过，不代表之后的实时价格。模拟单元测试与真实 MCP 联调分别记录。

## 参赛材料

本项目为麦当劳程序员创意开发大赛，官方报名截止为北京时间 **2026-10-25 23:59**。仓库需公开可访问，通过官方项目指定格式的 Issue 报名，并检查系统成功回复。

- [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md)：官方原文；提交前由项目所有者阅读并确认声明属实。
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md)：实际工具、调用流程与业务价值。
- [mcp-config.example.json](mcp-config.example.json)：仅使用环境变量占位符。
- [SUBMISSION.md](SUBMISSION.md)：报名正文与最新提交状态。

本项目在 Codex 中制作，未生成 `workbuddy.md`，不以虚构记录申领 WorkBuddy 专项奖励。项目采用 MIT 许可证；发布与报名状态见 SUBMISSION.md。

官方来源：[接口文档](https://open.mcd.cn/mcp/doc)、[活动项目](https://github.com/M-China/mcd-developer-innovation-challenge)、[完整规则](https://github.com/M-China/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md)。技术选择和依赖评估见 [references/design.md](references/design.md)。

## 许可证

原创代码和技能指引采用 [MIT 许可证](LICENSE)。官方参赛声明按赛事要求原文附入，其权利归原权利人；第三方依赖遵循各自许可证。
