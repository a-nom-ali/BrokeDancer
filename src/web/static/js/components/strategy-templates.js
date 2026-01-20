// src/web/static/js/components/strategy-templates.js

/**
 * Pre-built Strategy Templates
 *
 * Ready-to-use trading strategies that users can load and customize
 */

const STRATEGY_TEMPLATES = {
    momentum: {
        name: "Momentum Trading",
        description: "Buy when price breaks above resistance with strong volume",
        difficulty: "Beginner",
        category: "Trend Following",
        blocks: [
            {
                type: "price_cross",
                category: "triggers",
                x: 100,
                y: 100,
                properties: {
                    threshold: "0.05"
                }
            },
            {
                type: "volume_spike",
                category: "triggers",
                x: 100,
                y: 200,
                properties: {
                    multiplier: "1.5"
                }
            },
            {
                type: "and",
                category: "conditions",
                x: 300,
                y: 150,
                properties: {}
            },
            {
                type: "buy",
                category: "actions",
                x: 500,
                y: 150,
                properties: {
                    amount: "100"
                }
            },
            {
                type: "stop_loss",
                category: "risk",
                x: 700,
                y: 100,
                properties: {
                    percentage: "2"
                }
            },
            {
                type: "take_profit",
                category: "risk",
                x: 700,
                y: 200,
                properties: {
                    percentage: "5"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 1 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } },
            { from: { blockIndex: 3, outputIndex: 0 }, to: { blockIndex: 4, inputIndex: 0 } },
            { from: { blockIndex: 3, outputIndex: 0 }, to: { blockIndex: 5, inputIndex: 0 } }
        ]
    },

    meanReversion: {
        name: "Mean Reversion",
        description: "Buy when RSI is oversold, sell when overbought",
        difficulty: "Intermediate",
        category: "Mean Reversion",
        blocks: [
            {
                type: "rsi_signal",
                category: "triggers",
                x: 100,
                y: 100,
                properties: {
                    period: "14",
                    overbought: "70",
                    oversold: "30"
                }
            },
            {
                type: "threshold",
                category: "conditions",
                x: 300,
                y: 100,
                properties: {
                    min: "30",
                    max: "70"
                }
            },
            {
                type: "buy",
                category: "actions",
                x: 500,
                y: 80,
                properties: {
                    amount: "100"
                }
            },
            {
                type: "sell",
                category: "actions",
                x: 500,
                y: 180,
                properties: {
                    amount: "100"
                }
            },
            {
                type: "position_size",
                category: "risk",
                x: 700,
                y: 130,
                properties: {
                    capital: "1000",
                    risk_pct: "2"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 1, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 4, inputIndex: 0 } }
        ]
    },

    timeBasedEntry: {
        name: "Time-Based Entry",
        description: "Execute trades at specific times with risk management",
        difficulty: "Beginner",
        category: "Scheduled",
        blocks: [
            {
                type: "time_trigger",
                category: "triggers",
                x: 100,
                y: 150,
                properties: {
                    schedule: "09:30,15:00"
                }
            },
            {
                type: "buy",
                category: "actions",
                x: 300,
                y: 150,
                properties: {
                    amount: "50"
                }
            },
            {
                type: "max_trades",
                category: "risk",
                x: 500,
                y: 100,
                properties: {
                    limit: "3"
                }
            },
            {
                type: "stop_loss",
                category: "risk",
                x: 500,
                y: 200,
                properties: {
                    percentage: "1.5"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 1, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } }
        ]
    },

    volatilityBreakout: {
        name: "Volatility Breakout",
        description: "Trade on volume spikes with tight stop loss",
        difficulty: "Advanced",
        category: "Breakout",
        blocks: [
            {
                type: "volume_spike",
                category: "triggers",
                x: 100,
                y: 100,
                properties: {
                    multiplier: "2.0"
                }
            },
            {
                type: "price_cross",
                category: "triggers",
                x: 100,
                y: 200,
                properties: {
                    threshold: "0.02"
                }
            },
            {
                type: "and",
                category: "conditions",
                x: 300,
                y: 150,
                properties: {}
            },
            {
                type: "buy",
                category: "actions",
                x: 500,
                y: 150,
                properties: {
                    amount: "200"
                }
            },
            {
                type: "stop_loss",
                category: "risk",
                x: 700,
                y: 100,
                properties: {
                    percentage: "0.5"
                }
            },
            {
                type: "take_profit",
                category: "risk",
                x: 700,
                y: 200,
                properties: {
                    percentage: "3"
                }
            },
            {
                type: "notify",
                category: "actions",
                x: 500,
                y: 50,
                properties: {
                    message: "Breakout detected!"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 1 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 6, inputIndex: 0 } },
            { from: { blockIndex: 3, outputIndex: 0 }, to: { blockIndex: 4, inputIndex: 0 } },
            { from: { blockIndex: 3, outputIndex: 0 }, to: { blockIndex: 5, inputIndex: 0 } }
        ]
    },

    scalping: {
        name: "Quick Scalping",
        description: "Fast in-and-out trades with small profit targets",
        difficulty: "Advanced",
        category: "Scalping",
        blocks: [
            {
                type: "rsi_signal",
                category: "triggers",
                x: 100,
                y: 150,
                properties: {
                    period: "5",
                    overbought: "75",
                    oversold: "25"
                }
            },
            {
                type: "buy",
                category: "actions",
                x: 300,
                y: 150,
                properties: {
                    amount: "300"
                }
            },
            {
                type: "take_profit",
                category: "risk",
                x: 500,
                y: 100,
                properties: {
                    percentage: "0.5"
                }
            },
            {
                type: "stop_loss",
                category: "risk",
                x: 500,
                y: 200,
                properties: {
                    percentage: "0.3"
                }
            },
            {
                type: "max_trades",
                category: "risk",
                x: 700,
                y: 150,
                properties: {
                    limit: "10"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 1, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 1, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 4, inputIndex: 0 } }
        ]
    },

    safeTrader: {
        name: "Conservative Safe Trader",
        description: "Low-risk strategy with strict risk management",
        difficulty: "Beginner",
        category: "Conservative",
        blocks: [
            {
                type: "price_cross",
                category: "triggers",
                x: 100,
                y: 150,
                properties: {
                    threshold: "0.1"
                }
            },
            {
                type: "position_size",
                category: "risk",
                x: 300,
                y: 100,
                properties: {
                    capital: "1000",
                    risk_pct: "1"
                }
            },
            {
                type: "buy",
                category: "actions",
                x: 300,
                y: 200,
                properties: {
                    amount: "50"
                }
            },
            {
                type: "stop_loss",
                category: "risk",
                x: 500,
                y: 150,
                properties: {
                    percentage: "1"
                }
            },
            {
                type: "take_profit",
                category: "risk",
                x: 500,
                y: 250,
                properties: {
                    percentage: "2"
                }
            },
            {
                type: "max_trades",
                category: "risk",
                x: 700,
                y: 200,
                properties: {
                    limit: "2"
                }
            }
        ],
        connections: [
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 1, inputIndex: 0 } },
            { from: { blockIndex: 0, outputIndex: 0 }, to: { blockIndex: 2, inputIndex: 0 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 3, inputIndex: 0 } },
            { from: { blockIndex: 2, outputIndex: 0 }, to: { blockIndex: 4, inputIndex: 0 } },
            { from: { blockIndex: 3, outputIndex: 0 }, to: { blockIndex: 5, inputIndex: 0 } }
        ]
    }
};

// Template categories for filtering
const TEMPLATE_CATEGORIES = {
    "Trend Following": ["momentum"],
    "Mean Reversion": ["meanReversion"],
    "Scheduled": ["timeBasedEntry"],
    "Breakout": ["volatilityBreakout"],
    "Scalping": ["scalping"],
    "Conservative": ["safeTrader"]
};

// Difficulty levels
const DIFFICULTY_LEVELS = ["Beginner", "Intermediate", "Advanced"];
