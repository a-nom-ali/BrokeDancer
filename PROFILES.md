# Trading Profiles - Capital-Optimized Configuration

This bot includes **capital-based trading profiles** that automatically optimize trading parameters based on your available balance. Each profile is calibrated using real 2025 market data from Polymarket's BTC 15-minute arbitrage markets.

## 📊 Quick Profile Comparison

| Profile | Capital Range | Spread | Position Size | Max/Day | Cooldown | DRY_RUN |
|---------|--------------|--------|---------------|---------|----------|---------|
| **Learning** | $100-$200 | 3.0% | 5 shares | 10 trades | 30s | ✅ Yes |
| **Testing** | $200-$500 | 2.5% | 10 shares | 20 trades | 20s | ❌ No |
| **Scaling** | $500-$2,000 | 2.0% | 25 shares | 40 trades | 15s | ❌ No |
| **Advanced** | $2,000-$5,000 | 1.5% | 50 shares | 60 trades | 10s | ❌ No |
| **Professional** | $5,000+ | 1.0% | 100 shares | 100 trades | 5s | ❌ No |

## 🎯 Why Use Profiles?

### Research-Based Optimization

All profiles are calibrated based on:
- **Market fees**: ~2.5-3% total (2% outcome fee + 0.01-0.1% taker + gas)
- **Minimum profitable spread**: 2.5-3% after fees
- **Real success cases**: 98% win rate bots, $313 → $414K in 1 month (April 2025)
- **Conservative estimates**: 0.5-1% daily ROI achievable with proper risk management

### Automatic Risk Management

Each profile automatically sets:
- ✅ **Profit thresholds** - Optimal spread requirements for your capital tier
- ✅ **Position sizing** - Appropriate share counts to maximize returns without overexposure
- ✅ **Risk limits** - Daily loss caps, position limits, trade frequency controls
- ✅ **Execution parameters** - Cooldown times optimized for capital efficiency

## 🚀 Getting Started

### Option 1: Auto-Selection (Recommended)

Let the bot automatically select the best profile based on your balance:

```bash
# Copy the auto-selection template
cp .env.example.auto .env

# Edit .env and add your credentials
nano .env

# Set TRADING_PROFILE to "auto"
TRADING_PROFILE=auto
```

The bot will:
1. Fetch your account balance
2. Select the optimal profile tier
3. Apply all recommended settings
4. Log the selected profile and parameters

### Option 2: Manual Profile Selection

Choose a specific profile regardless of balance:

```bash
# Copy the profile template for your tier
cp .env.example.scaling .env  # Example: Scaling profile

# Edit .env and set TRADING_PROFILE
TRADING_PROFILE=scaling
```

Available profiles: `learning`, `testing`, `scaling`, `advanced`, `professional`

## 📋 Profile Details

### 1️⃣ Learning Profile ($100-$200)

**Purpose**: Learn the bot with minimal capital and risk.

**Key Parameters**:
- Spread requirement: **3.0%** (very conservative)
- Position size: **5 shares** per trade
- Max daily trades: **10**
- Max daily loss: **5%** ($5-$10)
- Cooldown: **30 seconds**
- **DRY_RUN: Recommended**

**Expected Performance**:
- Profit per trade: $0.25-$0.50
- Daily opportunities: 3-8 trades
- Monthly ROI: 5-10% (conservative)

**Best For**:
- First-time users learning the bot
- Testing strategy without risk
- Understanding market dynamics
- Validating configuration

**Configuration**:
```bash
cp .env.example.learning .env
# Set DRY_RUN=true for simulation
# Set SIM_BALANCE=150 to simulate $150 balance
```

---

### 2️⃣ Testing Profile ($200-$500)

**Purpose**: Real money testing with conservative parameters.

**Key Parameters**:
- Spread requirement: **2.5%** (safe margin above fees)
- Position size: **10 shares** per trade
- Max daily trades: **20**
- Max daily loss: **8%** ($16-$40)
- Cooldown: **20 seconds**
- **DRY_RUN: No** (live trading)

**Expected Performance**:
- Profit per trade: $1.25-$2.50
- Daily opportunities: 5-15 trades
- Monthly ROI: 7.5-15% (conservative)

**Best For**:
- Transitioning from DRY_RUN to live trading
- Building confidence with real executions
- Validating slippage and execution quality
- First real profits

**Configuration**:
```bash
cp .env.example.testing .env
# Set DRY_RUN=false for live trading
# Enable USE_WSS=true for better execution
```

---

### 3️⃣ Scaling Profile ($500-$2,000)

**Purpose**: Scale up with proven strategy for compounding growth.

**Key Parameters**:
- Spread requirement: **2.0%** (balanced risk/reward)
- Position size: **25 shares** per trade
- Max daily trades: **40**
- Max daily loss: **10%** ($50-$200)
- Cooldown: **15 seconds**
- **DRY_RUN: No**

**Expected Performance**:
- Profit per trade: $2.50-$10
- Daily opportunities: 10-30 trades
- Monthly ROI: 15-22.5% (moderate)

**Best For**:
- Proven strategy with consistent wins
- Compounding profits from lower tiers
- Balancing volume with risk
- Growing capital systematically

**Configuration**:
```bash
cp .env.example.scaling .env
# Focus on compounding: reinvest 50-75% of profits
# Monitor stats closely for optimization
```

---

### 4️⃣ Advanced Profile ($2,000-$5,000)

**Purpose**: High-volume trading with tighter spreads for experienced traders.

**Key Parameters**:
- Spread requirement: **1.5%** (tighter spreads, more opportunities)
- Position size: **50 shares** per trade
- Max daily trades: **60**
- Max daily loss: **12%** ($240-$600)
- Cooldown: **10 seconds**
- **DRY_RUN: No**

**Expected Performance**:
- Profit per trade: $7.50-$25
- Daily opportunities: 20-50 trades
- Monthly ROI: 18-30% (aggressive)

**Best For**:
- Experienced traders with proven track record
- High-frequency arbitrage execution
- Maximizing daily profit potential
- Scaling to professional tier

**Configuration**:
```bash
cp .env.example.advanced .env
# WebSocket REQUIRED (USE_WSS=true)
# Monitor performance metrics closely
```

---

### 5️⃣ Professional Profile ($5,000+)

**Purpose**: Maximum efficiency and volume for serious traders.

**Key Parameters**:
- Spread requirement: **1.0%** (aggressive, highest frequency)
- Position size: **100 shares** per trade
- Max daily trades: **100**
- Max daily loss: **15%** ($750+)
- Cooldown: **5 seconds**
- **DRY_RUN: No**

**Expected Performance**:
- Profit per trade: $10-$50
- Daily opportunities: 40-80 trades
- Monthly ROI: 20-40% (very aggressive)

**Best For**:
- Professional traders with substantial capital
- Maximizing absolute profit ($1,000-$3,000+/month potential)
- Multi-asset expansion ready
- High-volume systematic trading

**Configuration**:
```bash
cp .env.example.professional .env
# WebSocket REQUIRED (USE_WSS=true)
# Consider multi-asset expansion (ETH, SOL 15min markets)
```

## ⚙️ How Profiles Work

### Automatic Application

When you start the bot:

```
🚀 BTC 15-Minute Arbitrage Bot
Configuration loaded and validated

======================================================================
📊 APPLYING TRADING PROFILE
======================================================================
Current balance: $750.00
🤖 Auto-selected trading profile: Scaling (balance: $750.00)
✅ Capital ($750.00) is optimal for Scaling profile.
   Spread requirement: 2.0%
   Max daily trades: 40
   Position size: 25 shares
   Max daily loss: 10.0%
   ✓ Applied profit threshold: 0.980 (2.0% spread)
   ✓ Applied max position size: 100 shares
   ✓ Applied max trades per day: 40
   ✓ Applied max daily loss: $75.00 (10.0%)
   ✓ Applied balance utilization: 30%
   ✓ Applied cooldown: 15s
======================================================================
```

### Configuration Priority

Settings are applied in this order:

1. **Environment variables** (highest priority)
2. **Profile defaults**
3. **Original .env settings** (lowest priority)

This means you can override specific profile settings while keeping others:

```bash
# Use Scaling profile but override position size
TRADING_PROFILE=scaling
ORDER_SIZE=50  # Override profile's default of 25
```

### Profile Validation

The bot validates your capital against the selected profile:

```
⚠️ Warning: Your capital ($150.00) is below the minimum recommended
for Testing profile ($200.00). Consider using Learning profile.
```

```
ℹ️ Info: Your capital ($2,500.00) exceeds the recommended maximum
for Scaling profile ($2,000.00). Consider upgrading to Advanced profile.
```

## 📈 Expected Profit Trajectories

### Conservative Path (0.5% daily ROI)

| Starting Capital | Month 1 | Month 3 | Month 6 | Month 12 |
|-----------------|---------|---------|---------|----------|
| $200 | $230 | $310 | $490 | $1,200 |
| $500 | $575 | $775 | $1,225 | $3,000 |
| $1,000 | $1,150 | $1,550 | $2,450 | $6,000 |
| $2,000 | $2,300 | $3,100 | $4,900 | $12,000 |
| $5,000 | $5,750 | $7,750 | $12,250 | $30,000 |

### Aggressive Path (1.0% daily ROI)

| Starting Capital | Month 1 | Month 3 | Month 6 | Month 12 |
|-----------------|---------|---------|---------|----------|
| $200 | $270 | $490 | $1,200 | $7,200 |
| $500 | $675 | $1,225 | $3,000 | $18,000 |
| $1,000 | $1,350 | $2,450 | $6,000 | $36,000 |
| $2,000 | $2,700 | $4,900 | $12,000 | $72,000 |
| $5,000 | $6,750 | $12,250 | $30,000 | $180,000 |

*Assumes 50-75% profit compounding. Past performance does not guarantee future results.*

## 🛡️ Risk Management

All profiles include automatic risk controls:

### Daily Loss Limits

Protects against consecutive losses:
```
⚠️ Risk management blocked trade: Daily loss limit reached ($50.00 of $50.00)
```

### Position Size Caps

Prevents overexposure on single trades:
```
⚠️ Risk management blocked trade: Position size (300 shares) exceeds limit (250)
```

### Trade Frequency Controls

Prevents overtrading:
```
⚠️ Risk management blocked trade: Max trades per day reached (40 of 40)
```

### Balance Utilization

Ensures sufficient margin:
```
❌ Insufficient balance: need $250.00 but have $200.00
```

## 🎓 Recommended Progression

### Phase 1: Learning (Week 1-2)
- **Capital**: $100-$200
- **Profile**: Learning
- **Mode**: DRY_RUN=true
- **Goal**: Understand mechanics, validate configuration
- **Outcome**: 20+ simulated trades, strategy validation

### Phase 2: Testing (Week 3-4)
- **Capital**: $200-$500
- **Profile**: Testing
- **Mode**: Live trading
- **Goal**: Real execution, measure actual vs expected
- **Outcome**: 50+ real trades, performance tracking

### Phase 3: Scaling (Month 2-3)
- **Capital**: $500-$2,000
- **Profile**: Scaling
- **Mode**: Compounding enabled
- **Goal**: Grow capital through reinvestment
- **Outcome**: 500+ trades, consistent profitability

### Phase 4: Advanced/Professional (Month 4+)
- **Capital**: $2,000+
- **Profile**: Advanced or Professional
- **Mode**: High-volume optimization
- **Goal**: Maximize absolute profits
- **Outcome**: Multi-asset expansion, $1,000+/month

## 🔧 Customization

### Viewing Available Profiles

Run the profiles module directly:

```bash
python -m src.profiles
```

Output:
```
========================================================================================================================
CAPITAL-BASED TRADING PROFILES
========================================================================================================================
Profile         Capital Range        Spread     Size       Max/Day    Cooldown     DRY_RUN
------------------------------------------------------------------------------------------------------------------------
Learning        $100-$200            3.0%       5 shares   10 trades  30s          Yes
Testing         $200-$500            2.5%       10 shares  20 trades  20s          No
Scaling         $500-$2000           2.0%       25 shares  40 trades  15s          No
Advanced        $2000-$5000          1.5%       50 shares  60 trades  10s          No
Professional    $5000+               1.0%       100 shares 100 trades 5s           No
```

### Override Specific Parameters

You can override individual profile settings:

```bash
# Use Scaling profile but with custom spread threshold
TRADING_PROFILE=scaling
TARGET_PAIR_COST=0.975  # Override to 2.5% instead of profile's 2.0%

# Use Advanced profile but limit daily trades
TRADING_PROFILE=advanced
MAX_TRADES_PER_DAY=30  # Override profile's 60
```

### Disable Profile System

To use manual configuration without profiles:

```bash
# Don't set TRADING_PROFILE, or leave it empty
TRADING_PROFILE=

# All parameters must be set manually
TARGET_PAIR_COST=0.99
ORDER_SIZE=50
MAX_DAILY_LOSS=100
# ... etc
```

## 📊 Profile Performance Tracking

The statistics module tracks performance by profile:

```bash
# View trade statistics
cat trades.json

# Analyze performance
python -c "from src.statistics import StatisticsTracker; \
  tracker = StatisticsTracker('trades.json'); \
  print(tracker.get_stats())"
```

Key metrics to monitor:
- **Win rate**: Should be 95%+ for all profiles
- **Average slippage**: Should be < 0.5% for FOK orders
- **Execution time**: Should be < 500ms
- **Sharpe ratio**: Higher is better (risk-adjusted returns)

## ❓ FAQ

### Q: Can I change profiles mid-session?

**A**: Not recommended. Restart the bot with new profile settings. Profile changes affect risk limits and strategy.

### Q: What if my balance changes during trading?

**A**: Profile is selected once at startup based on initial balance. If your balance grows significantly (e.g., $500 → $2,000), restart the bot to upgrade to the next profile tier.

### Q: Should I use auto-selection or manual selection?

**A**: Use `auto` unless you have specific reasons to override. Auto-selection ensures optimal settings for your capital.

### Q: Why is my profile recommending DRY_RUN?

**A**: Learning profile recommends DRY_RUN for first-time users. Override with `DRY_RUN=false` once you're confident in the strategy.

### Q: Can I create custom profiles?

**A**: Yes! Edit `src/profiles.py` and add your custom `ProfileConfig`. Consider contributing back to the project.

### Q: What's the minimum capital to be profitable?

**A**: $200+ is recommended. Below $200, fees eat into profits significantly. See [PROFIT_ANALYSIS.md](./PROFIT_ANALYSIS.md) for detailed analysis.

## 🎯 Next Steps

1. **Choose your starting capital** based on risk tolerance
2. **Copy the appropriate .env template** for your tier
3. **Set TRADING_PROFILE=auto** for automatic optimization
4. **Start with DRY_RUN=true** if new to the bot
5. **Monitor performance** and upgrade tiers as capital grows
6. **Compound profits** to accelerate growth

## 📚 Related Documentation

- [PROFIT_ANALYSIS.md](./PROFIT_ANALYSIS.md) - Detailed budget and profit analysis
- [README.md](./README.md) - General bot setup and usage
- `.env.example.*` - Profile-specific configuration templates

---

*Profiles calibrated using 2025 Polymarket BTC 15-minute market data. Results may vary based on market conditions, execution quality, and trading discipline.*
