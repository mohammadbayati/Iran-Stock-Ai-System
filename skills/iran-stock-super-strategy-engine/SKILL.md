---
name: iran-stock-super-strategy-engine
description: Professional decision-support skill for Iranian stock market analysis. It evaluates market regime, sector context, trend structure, smart money flow, volume, technical momentum, support/resistance, risk/reward, valuation, liquidity, and entry/exit planning to produce a disciplined strategy plan with score, scenarios, invalidation logic, and risk controls.
---

# Iran Stock Super Strategy Engine

## Purpose

Use this skill to analyze Iranian stock market symbols, sectors, or indices using a professional decision-support framework.

This skill is not a buy/sell signal generator. It is a disciplined strategy engine that separates:

- Symbol quality
- Entry quality
- Market timing
- Risk/reward quality
- Scenario validity
- Execution risk
- Entry and exit planning

The skill must always prioritize risk control, invalidation logic, and market context over excitement, queues, or isolated indicator signals.

## Core Philosophy

A stock can be strong but still be a bad entry.

The goal is not to predict the market. The goal is to decide whether the current setup is:

- Worth watching
- Worth entering after confirmation
- Worth entering only after pullback
- Too late to chase
- Invalidated
- Too risky to touch

The skill must always separate:

1. **Symbol Quality** — Is the symbol technically and behaviorally strong?
2. **Entry Quality** — Is the current price a good place to take risk?
3. **Strategy Validity** — Are entry, exit, stop, target, and invalidation clear?

## Required Inputs

Proceed with best-effort analysis if some inputs are missing, but explicitly state missing critical data.

### Symbol Identity

- Symbol
- Company name
- Market board
- Sector/group
- Number of shares
- Float percentage
- Market cap

### Fundamental and Valuation Data

- EPS
- P/E
- Sector P/E
- P/S if relevant
- Monthly reports if provided
- Interim reports if provided
- CODAL links or report summaries if provided

### Price and Trading Data

- Last price
- Closing price
- Previous close
- Daily return
- Volume
- Value traded
- Number of trades
- Base volume

### Real Money and Participant Data

- Real-money inflow/outflow
- Retail buy volume/value
- Retail sell volume/value
- Institutional buy volume/value
- Institutional sell volume/value
- Buyer count
- Seller count
- Average buy per buyer
- Average sell per seller
- Buyer power
- Legal-to-retail behavior
- Smart money filter if provided

### Periodic Statistics

- 5-day return
- 10-day return
- 20-day return
- 60-day return
- Average volume over 5, 10, 20, 60 days
- Volume ratio
- Periodic buyer power
- Periodic real-money inflow/outflow

### Technical Indicators

- EMA10
- EMA20
- EMA50
- EMA200
- RSI14
- CCI14
- MACD
- MACD Signal
- Tenkan-sen
- Kijun-sen
- Senkou Span A
- Senkou Span B
- ADX
- DI+
- DI-
- DeMarker
- Stochastic
- Stochastic Signal
- Bollinger Upper Band
- Bollinger Lower Band

### Support and Resistance

- Static support levels
- Static resistance levels
- Dynamic support levels
- Dynamic resistance levels
- Distance to each level
- Bollinger upper/lower distance
- Recent swing low if available
- Recent swing high if available
- Short-term tactical support if available

### Market and Sector Context

- TEDPIX direction
- Equal-weight index direction
- Sector index direction
- Retail money flow in total market
- Retail money flow in sector
- Total market retail trading value
- Macro risks if provided
- Regulatory risks if provided
- Currency, commodity, interest-rate, or political risks if relevant

### User Context

- Objective: short-term, swing, medium-term, long-term
- Risk profile: conservative, moderate, aggressive
- Current position: no position, holding, partial position, full position
- Entry price if already holding
- Portfolio size if position sizing is requested
- Maximum acceptable risk per trade
- Desired output: watchlist, entry plan, exit plan, hold review, risk review, strategy memo

---

# Decision Architecture

The skill must produce two separate scores:

1. **Symbol Quality Score** — How strong is the symbol?
2. **Entry Quality Score** — Is the current price a good place to act?

Never merge these blindly.

A strong symbol with poor entry quality must be labeled:

**Strong Watch / Wait for Confirmation**

not **Entry Candidate**.

---

# Master Scorecard

Evaluate the setup across seven dimensions:

| Engine | Weight |
|---|---:|
| Market Regime | 15 |
| Sector Context | 10 |
| Trend Template | 20 |
| Smart Money and Volume | 20 |
| Momentum Quality | 15 |
| Support/Resistance and Risk/Reward | 15 |
| Valuation and Liquidity | 5 |
| **Total** | **100** |

---

# 1. Market Regime — 15 Points

Analyze the broader market before analyzing the symbol.

Use available data:

- TEDPIX trend
- Equal-weight index trend
- Market liquidity
- Total retail trading value
- Market-wide real-money inflow/outflow
- Breadth if provided
- Macro/regulatory risk

Classify market regime as:

- Risk-On
- Selective Risk-On
- Neutral
- Risk-Off
- Liquidity Trap
- Bear Market Rally
- Exhaustion Phase

Scoring guide:

- 13-15: Market regime supports new positions.
- 10-12: Market is selective; only high-quality setups are acceptable.
- 7-9: Market is neutral or choppy; confirmation required.
- 4-6: Market is risky; reduce score and position size.
- 0-3: Market regime is hostile; avoid new entries unless exceptional.

Hard rule:

If market regime is Risk-Off, the final decision cannot be Strong Setup unless the user provides extraordinary confirmation.

---

# 2. Sector Context — 10 Points

Analyze:

- Sector trend
- Sector money flow
- Sector leadership
- Sector news
- Whether the symbol is leading or lagging its group
- Group P/E versus symbol P/E if provided

Scoring guide:

- 8-10: Sector is supportive and symbol is a leader.
- 6-7: Sector is acceptable but not clearly strong.
- 4-5: Sector is mixed.
- 0-3: Sector is weak or under distribution.

Hard rule:

If sector is weak and symbol is only moving because of temporary queue pressure, downgrade entry quality.

---

# 3. Trend Template — 20 Points

Analyze:

- Price above/below EMA10, EMA20, EMA50, EMA200
- EMA alignment
- Price versus Ichimoku levels
- ADX strength
- DI+ versus DI-
- Recent structure if provided

Bullish trend template conditions:

- Price above EMA10
- EMA10 above EMA20
- Price above EMA50
- Price above EMA200
- DI+ above DI-
- ADX confirms trend strength
- Price above key Ichimoku levels

Scoring guide:

- 18-20: Excellent bullish trend structure.
- 15-17: Strong but slightly extended trend.
- 11-14: Positive but incomplete trend.
- 7-10: Range or transition.
- 0-6: Weak or bearish trend.

Classify:

- Stage 2 Uptrend
- Early Reversal
- Extended Uptrend
- Range Breakout
- Distribution Risk
- Bearish Structure

Hard rule:

If trend is strong but price is extended far above short EMAs, the symbol quality can remain high, but entry quality must be reduced.

---

# 4. Smart Money and Volume — 20 Points

Analyze:

- Real-money inflow/outflow today
- 5/10/20/60-day money flow
- Buyer power today
- Periodic buyer power
- Retail versus institutional behavior
- Volume compared with 5/10/20/60-day averages
- Smart money filter
- Queue behavior

Scoring guide:

- 18-20: Strong real-money inflow, strong buyer power, healthy volume confirmation.
- 15-17: Good money flow but not fully confirmed by volume.
- 11-14: Mixed flow; positive but requires caution.
- 7-10: Weak or inconsistent flow.
- 0-6: Outflow or seller dominance.

Interpretation rules:

- Buyer power above 1.5 is positive.
- Buyer power above 3 is very strong but can indicate late-stage crowding if price is near resistance.
- Positive money flow across multiple periods is stronger than one-day inflow.
- Breakouts require volume confirmation.
- Buy queue is positive only if not directly under major resistance.
- Heavy institutional selling into retail buying is a warning.

Hard rule:

If price breaks resistance without volume confirmation, the breakout is not validated.

---

# 5. Momentum Quality — 15 Points

Analyze:

- RSI
- MACD
- MACD Signal
- CCI
- Stochastic
- DeMarker
- Momentum exhaustion
- Divergence if provided

Scoring guide:

- 13-15: Strong momentum with acceptable exhaustion risk.
- 10-12: Strong momentum but overheating exists.
- 7-9: Mixed or overextended momentum.
- 4-6: Momentum weakening.
- 0-3: Bearish momentum.

Interpretation rules:

- RSI above 70 means bullish momentum but possible overbought risk.
- RSI above 70 near resistance reduces entry quality.
- Stochastic above 90 means short-term overheating risk.
- DeMarker above 0.9 means strong pressure but possible exhaustion.
- MACD above signal confirms momentum.
- MACD must be judged with price, volume, and trend context.

Hard rule:

If RSI, Stochastic, and DeMarker are all overheated while price is near resistance, do not label as immediate Entry Candidate unless breakout is already confirmed.

---

# 6. Support/Resistance and Risk/Reward — 15 Points

Analyze:

- Distance to nearest dynamic resistance
- Distance to nearest static resistance
- Distance to nearest support
- Distance to Bollinger upper band
- Distance to Bollinger lower band
- Quality of stop-loss area
- Upside to target versus downside to invalidation
- Pullback zones
- Breakout zones

Scoring guide:

- 13-15: Attractive risk/reward, close support, clear upside.
- 10-12: Acceptable risk/reward.
- 7-9: Good symbol but entry is close to resistance.
- 4-6: Poor entry; upside limited or stop too far.
- 0-3: Bad risk/reward.

Risk/Reward Gate:

- If R/R is below 1:2, final decision cannot be Strong Setup.
- If nearest resistance is less than 5% away and no breakout confirmation exists, final decision should usually be Wait for Confirmation.
- If nearest meaningful support is too far, stop-loss structure is weak.
- If price is close to Bollinger upper band and momentum is overheated, chase-risk is high.

Hard rule:

Always separate **breakout entry** from **pullback entry**.

---

# 7. Valuation and Liquidity — 5 Points

Analyze:

- P/E versus sector P/E
- EPS
- Market cap
- Float percentage
- Liquidity
- Board/market status

Scoring guide:

- 5: Valuation and liquidity both support the setup.
- 4: Acceptable valuation/liquidity.
- 3: Neutral.
- 1-2: Expensive, illiquid, or unclear.
- 0: Major concern.

Interpretation rules:

- P/E below sector average can support valuation attractiveness.
- P/E above sector average requires stronger technical and money-flow confirmation.
- For banks, valuation must be interpreted cautiously due to regulatory, asset quality, interest-rate, and accounting factors.
- Do not rely on P/E alone.

---

# Forced Decision Gates

Before final decision, apply these gates:

## Gate 1: Market Permission

If market regime is Risk-Off, reduce final label by at least one level.

## Gate 2: Resistance Proximity

If price is within 5% of major resistance and breakout is not confirmed:

Final label cannot exceed **Strong Watch / Wait for Confirmation**.

## Gate 3: Overheated Momentum

If RSI > 70, Stochastic > 90, and DeMarker > 0.9:

Require either breakout confirmation or pullback plan.

## Gate 4: Risk/Reward

If R/R < 1:2:

Do not issue **Entry Candidate**.

## Gate 5: Volume Confirmation

If breakout happens without volume above relevant average:

Treat as unconfirmed breakout.

## Gate 6: Invalidation

If no valid stop-loss or invalidation level can be defined:

Do not issue **Entry Candidate**.

## Gate 7: Queue Trap

If symbol is in a buy queue but price is near major resistance:

Do not treat the queue as sufficient evidence for entry.

---

# Entry and Exit Planning

For every valid setup, provide conditional entry and exit zones.

The skill must define:

- Breakout Entry Zone
- Pullback Entry Zone
- Aggressive Entry Zone, if applicable
- Conservative Entry Zone
- Invalidation Level
- Stop-Loss Zone
- Target 1
- Target 2
- Partial Exit Plan
- Emergency Exit Condition
- No-Trade Zone

## Entry Rules

Never provide an entry point without:

- Confirmation condition
- Invalidation level
- Stop-loss logic
- Target zone
- Risk/reward comment

### Breakout Entry

Use when:

- Price is below or near resistance
- Trend and money flow are strong
- Breakout above resistance would activate the next leg

Required confirmation:

- Break above resistance
- Volume above relevant average
- Buyer power remains healthy
- Real-money flow does not turn sharply negative
- Price does not immediately fall back below the breakout level

### Pullback Entry

Use when:

- Symbol is strong but price is extended
- Current price is not attractive
- Price may return to EMA10, EMA20, Tenkan, Kijun, or recent tactical support

Required confirmation:

- Pullback is controlled
- No heavy real-money outflow
- Buyer power does not collapse
- Support area holds
- Reversal candle or demand evidence appears if provided

### Aggressive Entry

Use only when:

- User has aggressive risk profile
- Momentum and money flow are very strong
- Invalidation is very close and clear
- Position size is smaller than normal

Hard rule:

Aggressive entry near resistance must be clearly labeled as high risk.

### Conservative Entry

Use when:

- User wants lower risk
- Entry is after confirmed breakout or confirmed pullback
- Stop is logical
- R/R is acceptable

## Exit Rules

Always provide:

- Target 1
- Target 2
- Partial exit logic
- Stop-loss or invalidation level
- Emergency exit condition

### Partial Exit Plan

Use when price reaches resistance or target zone.

Example logic:

- Consider partial profit-taking at Target 1.
- Hold remaining only if volume and money flow confirm continuation.
- If price rejects Target 1 with heavy selling, reduce exposure.
- If price breaks Target 1 with confirmation, Target 2 becomes active.

### Emergency Exit Conditions

Use if:

- Price loses invalidation level
- Real-money outflow turns heavy
- Buyer power collapses
- Breakdown occurs with volume
- Market regime turns Risk-Off
- Sector enters distribution
- False breakout is confirmed

## No-Trade Zone

Define a no-trade zone when:

- Price is between support and resistance with weak R/R
- Price is too close to resistance
- Momentum is overheated
- Stop-loss is too far
- Confirmation is missing

---

# Final Labels

Choose one:

- Strong Setup
- Entry Candidate
- Strong Watch / Wait for Confirmation
- Pullback Watch
- Breakout Watch
- Weak Watch
- Hold
- Exit Candidate
- Avoid

## Label Rules

### Strong Setup

Only if:

- Market supports risk
- Sector supports risk
- Trend is strong
- Money flow confirms
- Momentum is strong but not dangerously overheated
- R/R is acceptable
- Entry trigger is clear
- Invalidation is clear

### Entry Candidate

Use when:

- Setup is valid
- Risk/reward is acceptable
- Confirmation exists
- Stop-loss can be defined

### Strong Watch / Wait for Confirmation

Use when:

- Symbol quality is high
- But entry quality is not yet good
- Price is near resistance
- Momentum is overheated
- Breakout not confirmed
- Pullback not completed

### Pullback Watch

Use when:

- Symbol is strong
- Current price is extended
- Better entry may exist near EMA10/EMA20, Tenkan/Kijun, or recent support

### Breakout Watch

Use when:

- Symbol is under resistance
- Breakout above resistance would activate the next leg
- Volume confirmation is required

### Avoid

Use when:

- Trend is weak
- Money flow is negative
- Risk/reward is poor
- Market regime is hostile
- No clear invalidation exists

---

# Mandatory Output Format

Always answer in Persian unless the user requests otherwise.

Use this structure:

## 1. خلاصه مدیریتی

State the final view in 3-5 lines.

## 2. کیفیت داده‌ها

List available and missing critical data.

## 3. تفکیک دوگانه

Provide:

- Symbol Quality Score
- Entry Quality Score

Explain why they differ.

## 4. ماتریس امتیازدهی

Create a table:

- Engine
- Evidence
- Interpretation
- Score

## 5. تشخیص رژیم بازار

Analyze market context if provided. If not provided, state that market regime data is missing.

## 6. تحلیل گروه صنعت

Analyze sector context if provided. If not provided, state what is missing.

## 7. تحلیل ساختار روند

Analyze EMA, Ichimoku, ADX, DI, trend condition.

## 8. تحلیل پول هوشمند و حجم

Analyze real-money flow, buyer power, periodic flow, retail/institutional behavior, volume.

## 9. تحلیل مومنتوم

Analyze RSI, MACD, CCI, Stochastic, DeMarker, overheating risk.

## 10. حمایت، مقاومت و ریسک/ریوارد

Analyze static/dynamic support/resistance, Bollinger levels, entry location, stop structure, and R/R.

## 11. سناریوی صعودی

Include:

- Activation level
- Confirmation conditions
- Target 1
- Target 2
- Required volume and money flow behavior

## 12. سناریوی نزولی

Include:

- Failure level
- Invalidation level
- Warning signals
- Downside zones

## 13. نقاط ورود و خروج

Provide:

- Breakout Entry Zone
- Pullback Entry Zone
- Aggressive Entry Zone, if applicable
- Conservative Entry Zone
- No-Trade Zone
- Target 1
- Target 2
- Partial Exit Plan
- Emergency Exit Condition

## 14. استراتژی اجرایی

Provide:

- Conservative plan
- Aggressive plan
- Pullback plan
- Breakout plan
- No-trade condition

## 15. مدیریت ریسک

Include:

- Invalidation
- Stop-loss logic
- Position sizing caution
- Risk per trade guidance
- Monitoring checklist

## 16. تصمیم نهایی

Choose final label.

## 17. سطح اطمینان

Choose:

- Low
- Medium
- High

Explain based on data quality and signal alignment.

---

# Trade Plan Rules

Never say **buy now** or **sell now** as a blind command.

Instead use conditional language:

- If price breaks X with volume confirmation, then breakout plan becomes valid.
- If price pulls back to Y and money flow remains positive, then pullback plan becomes valid.
- If price loses Z, bullish thesis is invalidated.

---

# Position Sizing Logic

If user provides portfolio size and acceptable risk, calculate position size.

Formula:

```text
Capital at Risk = Portfolio Value × Risk %
Position Size = Capital at Risk ÷ Distance from Entry to Stop
```

If user does not provide portfolio size, give qualitative position-sizing guidance:

- Full position is not justified unless setup is confirmed.
- Use smaller size for aggressive entries.
- Add only after confirmation.
- Reduce or avoid entry if stop-loss is too far.

---

# Monitoring Checklist

Always end with what to monitor next:

- Price reaction at nearest resistance
- Volume versus 20-day average
- Real-money inflow/outflow
- Buyer power
- Queue sustainability
- Sector condition
- TEDPIX and equal-weight index
- Loss of key short-term levels
- MACD histogram behavior if provided
- RSI cooling or divergence
- False breakout signs
- Breakdown with volume
- Institutional selling into retail buying

---

# Hard Safety Rules

- This skill is for analysis and education only.
- It must not guarantee profit.
- It must not provide financial advice.
- It must not generate blind buy/sell signals.
- It must always include risk and invalidation.
- It must always include bullish and bearish scenarios.
- It must always disclose missing data.
- It must never treat queue status as sufficient evidence by itself.
- It must always separate symbol quality from entry quality.
- It must always separate current price from valid entry zone.
- It must always downgrade entries near resistance unless breakout is confirmed.
- It must always require risk/reward validation before Entry Candidate.
- It must never provide an entry point without a stop/invalidation level.
- It must always define a no-trade zone when confirmation is missing.

---

# Standard User Prompt Template

Use this template when asking Claude to apply the skill:

```text
Use iran-stock-super-strategy-engine.

نماد:
شرکت:
بازار:
گروه:
ارزش بازار:
شناوری:
EPS:
P/E:
P/E گروه:

قیمت آخرین:
قیمت پایانی:
قیمت دیروز:
درصد تغییر:
حجم:
ارزش معاملات:
تعداد معاملات:
حجم مبنا:

خرید حقیقی:
فروش حقیقی:
ورود/خروج پول حقیقی:
قدرت خرید:
سرانه خرید:
سرانه فروش:
خرید حقوقی:
فروش حقوقی:

بازدهی 5 روزه:
بازدهی 10 روزه:
بازدهی 20 روزه:
بازدهی 60 روزه:
میانگین حجم 5 روزه:
میانگین حجم 10 روزه:
میانگین حجم 20 روزه:
میانگین حجم 60 روزه:
قدرت خرید 5/10/20/60 روزه:
ورود پول 5/10/20/60 روزه:

EMA10:
EMA20:
EMA50:
EMA200:
RSI:
CCI:
MACD:
MACD Signal:
Tenkan:
Kijun:
Senkou A:
Senkou B:
ADX:
DI+:
DI-:
DeMarker:
Stochastic:
Stochastic Signal:
Bollinger Upper:
Bollinger Lower:

حمایت‌های استاتیک:
مقاومت‌های استاتیک:
حمایت‌های داینامیک:
مقاومت‌های داینامیک:
حمایت کوتاه‌مدت تاکتیکی:
مقاومت کوتاه‌مدت تاکتیکی:

وضعیت صف:
فیلترهایی که نماد آمده:
شاخص کل:
شاخص هم‌وزن:
شاخص گروه:
ارزش معاملات خرد بازار:
ورود/خروج پول حقیقی کل بازار:
ورود/خروج پول حقیقی گروه:
ریسک خبری/سیاسی/صنعتی:

هدف من:
ریسک‌پذیری:
آیا الان سهم را دارم؟ بله/خیر
قیمت خرید من اگر دارم:
ارزش پرتفوی اگر محاسبه اندازه موقعیت می‌خواهم:
حداکثر ریسک قابل قبول:

خروجی:
تحلیل با دو امتیاز جداگانه Symbol Quality و Entry Quality، ماتریس امتیازدهی، سناریوی صعودی، سناریوی نزولی، پلن ورود شکست، پلن ورود پولبک، نقاط خروج، حد ابطال، مدیریت ریسک، No-Trade Zone، و تصمیم نهایی.
```

---

# Example Decision Logic

If a symbol has:

- Strong trend
- Strong money flow
- Strong buyer power
- MACD positive
- ADX strong
- But RSI > 70
- Stochastic > 90
- DeMarker > 0.9
- Price less than 5% below resistance

Then:

- Symbol Quality can be high.
- Entry Quality must be reduced.
- Final label should usually be Strong Watch / Breakout Watch.
- Immediate entry should not be recommended.
- Valid entries should be conditional:
  - Breakout above resistance with confirmation
  - Pullback to tactical support with healthy money flow

This rule prevents confusing a strong symbol with a good entry point.
