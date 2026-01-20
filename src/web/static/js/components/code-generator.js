// src/web/static/js/components/code-generator.js

class CodeGenerator {
    constructor() {
        this.indentLevel = 0;
        this.indentSize = 4;
        this.code = [];
        this.imports = new Set();
        this.variables = new Map();
    }

    generate(workflow) {
        this.reset();

        // Add imports
        this.addImports();

        // Generate class structure
        this.generateClassHeader(workflow.name || 'GeneratedStrategy');

        // Generate __init__ method
        this.generateInit();

        // Generate trigger methods
        this.generateTriggers(workflow);

        // Generate condition methods
        this.generateConditions(workflow);

        // Generate action methods
        this.generateActions(workflow);

        // Generate risk management methods
        this.generateRiskManagement(workflow);

        // Generate main execution method
        this.generateExecuteMethod(workflow);

        // Close class
        this.dedent();

        return this.code.join('\n');
    }

    reset() {
        this.indentLevel = 0;
        this.code = [];
        this.imports = new Set([
            'from datetime import datetime',
            'from typing import Dict, Any, Optional',
            'import asyncio'
        ]);
        this.variables = new Map();
    }

    addImports() {
        this.code.push('# Auto-generated trading strategy');
        this.code.push('# Generated at: ' + new Date().toISOString());
        this.code.push('');
        this.imports.forEach(imp => this.code.push(imp));
        this.code.push('');
        this.code.push('');
    }

    generateClassHeader(className) {
        this.addLine(`class ${className}:`);
        this.indent();
        this.addLine('"""Auto-generated trading strategy from visual workflow."""');
        this.addLine('');
    }

    generateInit() {
        this.addLine('def __init__(self, bot_instance):');
        this.indent();
        this.addLine('"""Initialize strategy with bot instance."""');
        this.addLine('self.bot = bot_instance');
        this.addLine('self.last_execution = None');
        this.addLine('self.execution_count = 0');
        this.addLine('self.variables = {}');
        this.dedent();
        this.addLine('');
    }

    generateTriggers(workflow) {
        const triggers = workflow.blocks.filter(b => b.category === 'triggers');

        if (triggers.length === 0) return;

        for (const trigger of triggers) {
            this.generateTriggerMethod(trigger);
        }
    }

    generateTriggerMethod(trigger) {
        const methodName = this.sanitizeName(trigger.name || trigger.type);

        this.addLine(`async def check_${methodName}(self, market_data: Dict[str, Any]) -> bool:`);
        this.indent();
        this.addLine(`"""Check if ${trigger.name || trigger.type} condition is met."""`);

        switch (trigger.type) {
            case 'price_cross':
                this.addLine('price = market_data.get("price", 0)');
                this.addLine('previous_price = market_data.get("previous_price", 0)');
                this.addLine(`threshold = ${trigger.config?.threshold || 50000}`);
                this.addLine(`direction = "${trigger.config?.direction || 'above'}"`);
                this.addLine('');
                this.addLine('if direction == "above":');
                this.indent();
                this.addLine('return previous_price < threshold <= price');
                this.dedent();
                this.addLine('else:');
                this.indent();
                this.addLine('return previous_price > threshold >= price');
                this.dedent();
                break;

            case 'volume_spike':
                this.addLine('volume = market_data.get("volume", 0)');
                this.addLine('avg_volume = market_data.get("avg_volume", 0)');
                this.addLine(`multiplier = ${trigger.config?.multiplier || 2.0}`);
                this.addLine('return volume >= (avg_volume * multiplier)');
                break;

            case 'time_trigger':
                this.addLine('current_time = datetime.now()');
                this.addLine(`interval_minutes = ${trigger.config?.interval || 60}`);
                this.addLine('');
                this.addLine('if self.last_execution is None:');
                this.indent();
                this.addLine('return True');
                this.dedent();
                this.addLine('');
                this.addLine('time_diff = (current_time - self.last_execution).total_seconds() / 60');
                this.addLine('return time_diff >= interval_minutes');
                break;

            case 'rsi_signal':
                this.addLine('rsi = market_data.get("rsi", 50)');
                this.addLine(`oversold = ${trigger.config?.oversold || 30}`);
                this.addLine(`overbought = ${trigger.config?.overbought || 70}`);
                this.addLine('return rsi <= oversold or rsi >= overbought');
                break;

            case 'webhook':
                this.addLine('webhook_data = market_data.get("webhook_data", {})');
                this.addLine(`signal = webhook_data.get("signal", "")`);
                this.addLine('return signal in ["buy", "sell"]');
                break;

            case 'event_listener':
                this.addLine('event_type = market_data.get("event_type", "")');
                this.addLine(`target_event = "${trigger.config?.event || 'market_update'}"`);
                this.addLine('return event_type == target_event');
                break;

            case 'manual_trigger':
                this.addLine('# Manual trigger - always returns False, execute via API');
                this.addLine('return market_data.get("manual_trigger", False)');
                break;

            default:
                this.addLine('# Unknown trigger type');
                this.addLine('return False');
        }

        this.dedent();
        this.addLine('');
    }

    generateConditions(workflow) {
        const conditions = workflow.blocks.filter(b => b.category === 'conditions');

        if (conditions.length === 0) return;

        for (const condition of conditions) {
            this.generateConditionMethod(condition);
        }
    }

    generateConditionMethod(condition) {
        const methodName = this.sanitizeName(condition.name || condition.type);

        this.addLine(`def evaluate_${methodName}(self, data: Dict[str, Any]) -> bool:`);
        this.indent();
        this.addLine(`"""Evaluate ${condition.name || condition.type} condition."""`);

        switch (condition.type) {
            case 'and':
                this.addLine('# AND condition - all inputs must be true');
                this.addLine('conditions = data.get("conditions", [])');
                this.addLine('return all(conditions)');
                break;

            case 'or':
                this.addLine('# OR condition - at least one input must be true');
                this.addLine('conditions = data.get("conditions", [])');
                this.addLine('return any(conditions)');
                break;

            case 'compare':
                this.addLine('value1 = data.get("value1", 0)');
                this.addLine('value2 = data.get("value2", 0)');
                this.addLine(`operator = "${condition.config?.operator || '=='}"`);
                this.addLine('');
                this.addLine('if operator == "==":');
                this.indent();
                this.addLine('return value1 == value2');
                this.dedent();
                this.addLine('elif operator == "!=":');
                this.indent();
                this.addLine('return value1 != value2');
                this.dedent();
                this.addLine('elif operator == ">":');
                this.indent();
                this.addLine('return value1 > value2');
                this.dedent();
                this.addLine('elif operator == ">=":');
                this.indent();
                this.addLine('return value1 >= value2');
                this.dedent();
                this.addLine('elif operator == "<":');
                this.indent();
                this.addLine('return value1 < value2');
                this.dedent();
                this.addLine('elif operator == "<=":');
                this.indent();
                this.addLine('return value1 <= value2');
                this.dedent();
                this.addLine('return False');
                break;

            case 'threshold':
                this.addLine('value = data.get("value", 0)');
                this.addLine(`threshold = ${condition.config?.threshold || 0}`);
                this.addLine(`direction = "${condition.config?.direction || 'above'}"`);
                this.addLine('');
                this.addLine('if direction == "above":');
                this.indent();
                this.addLine('return value > threshold');
                this.dedent();
                this.addLine('else:');
                this.indent();
                this.addLine('return value < threshold');
                this.dedent();
                break;

            case 'if':
                this.addLine('condition = data.get("condition", False)');
                this.addLine('return bool(condition)');
                break;

            case 'switch':
                this.addLine('value = data.get("value", "")');
                this.addLine(`case1 = "${condition.config?.case1 || ''}"`);
                this.addLine(`case2 = "${condition.config?.case2 || ''}"`);
                this.addLine(`case3 = "${condition.config?.case3 || ''}"`);
                this.addLine('');
                this.addLine('if value == case1:');
                this.indent();
                this.addLine('return "case1"');
                this.dedent();
                this.addLine('elif value == case2:');
                this.indent();
                this.addLine('return "case2"');
                this.dedent();
                this.addLine('elif value == case3:');
                this.indent();
                this.addLine('return "case3"');
                this.dedent();
                this.addLine('return "default"');
                break;

            default:
                this.addLine('return True');
        }

        this.dedent();
        this.addLine('');
    }

    generateActions(workflow) {
        const actions = workflow.blocks.filter(b => b.category === 'actions');

        if (actions.length === 0) return;

        for (const action of actions) {
            this.generateActionMethod(action);
        }
    }

    generateActionMethod(action) {
        const methodName = this.sanitizeName(action.name || action.type);

        this.addLine(`async def execute_${methodName}(self, data: Dict[str, Any]) -> Dict[str, Any]:`);
        this.indent();
        this.addLine(`"""Execute ${action.name || action.type} action."""`);

        switch (action.type) {
            case 'buy':
                this.addLine('market_id = data.get("market_id", "")');
                this.addLine(`side = "${action.config?.side || 'YES'}"`);
                this.addLine(`amount = ${action.config?.amount || 10.0}`);
                this.addLine('');
                this.addLine('try:');
                this.indent();
                this.addLine('result = await self.bot.place_order(');
                this.indent();
                this.addLine('market_id=market_id,');
                this.addLine('side=side,');
                this.addLine('amount=amount');
                this.dedent();
                this.addLine(')');
                this.addLine('return {"success": True, "order": result}');
                this.dedent();
                this.addLine('except Exception as e:');
                this.indent();
                this.addLine('return {"success": False, "error": str(e)}');
                this.dedent();
                break;

            case 'sell':
                this.addLine('position_id = data.get("position_id", "")');
                this.addLine(`amount = ${action.config?.amount || 10.0}`);
                this.addLine('');
                this.addLine('try:');
                this.indent();
                this.addLine('result = await self.bot.close_position(');
                this.indent();
                this.addLine('position_id=position_id,');
                this.addLine('amount=amount');
                this.dedent();
                this.addLine(')');
                this.addLine('return {"success": True, "result": result}');
                this.dedent();
                this.addLine('except Exception as e:');
                this.indent();
                this.addLine('return {"success": False, "error": str(e)}');
                this.dedent();
                break;

            case 'cancel':
                this.addLine('order_id = data.get("order_id", "")');
                this.addLine('');
                this.addLine('try:');
                this.indent();
                this.addLine('result = await self.bot.cancel_order(order_id)');
                this.addLine('return {"success": True, "cancelled": order_id}');
                this.dedent();
                this.addLine('except Exception as e:');
                this.indent();
                this.addLine('return {"success": False, "error": str(e)}');
                this.dedent();
                break;

            case 'notify':
                this.addLine(`message = "${action.config?.message || 'Strategy notification'}"`);
                this.addLine(`channel = "${action.config?.channel || 'email'}"`);
                this.addLine('');
                this.addLine('try:');
                this.indent();
                this.addLine('await self.bot.send_notification(');
                this.indent();
                this.addLine('message=message,');
                this.addLine('channel=channel,');
                this.addLine('data=data');
                this.dedent();
                this.addLine(')');
                this.addLine('return {"success": True, "sent": True}');
                this.dedent();
                this.addLine('except Exception as e:');
                this.indent();
                this.addLine('return {"success": False, "error": str(e)}');
                this.dedent();
                break;

            default:
                this.addLine('return {"success": True, "message": "Action executed"}');
        }

        this.dedent();
        this.addLine('');
    }

    generateRiskManagement(workflow) {
        const riskNodes = workflow.blocks.filter(b => b.category === 'risk');

        if (riskNodes.length === 0) return;

        for (const riskNode of riskNodes) {
            this.generateRiskMethod(riskNode);
        }
    }

    generateRiskMethod(riskNode) {
        const methodName = this.sanitizeName(riskNode.name || riskNode.type);

        this.addLine(`def check_${methodName}(self, data: Dict[str, Any]) -> Dict[str, Any]:`);
        this.indent();
        this.addLine(`"""Check ${riskNode.name || riskNode.type} risk management rule."""`);

        switch (riskNode.type) {
            case 'stop_loss':
                this.addLine('entry_price = data.get("entry_price", 0)');
                this.addLine('current_price = data.get("current_price", 0)');
                this.addLine(`percentage = ${riskNode.config?.percentage || 5.0}`);
                this.addLine('');
                this.addLine('loss = ((entry_price - current_price) / entry_price) * 100');
                this.addLine('triggered = loss >= percentage');
                this.addLine('');
                this.addLine('return {');
                this.indent();
                this.addLine('"triggered": triggered,');
                this.addLine('"loss_percentage": loss,');
                this.addLine('"should_exit": triggered');
                this.dedent();
                this.addLine('}');
                break;

            case 'take_profit':
                this.addLine('entry_price = data.get("entry_price", 0)');
                this.addLine('current_price = data.get("current_price", 0)');
                this.addLine(`percentage = ${riskNode.config?.percentage || 10.0}`);
                this.addLine('');
                this.addLine('profit = ((current_price - entry_price) / entry_price) * 100');
                this.addLine('triggered = profit >= percentage');
                this.addLine('');
                this.addLine('return {');
                this.indent();
                this.addLine('"triggered": triggered,');
                this.addLine('"profit_percentage": profit,');
                this.addLine('"should_exit": triggered');
                this.dedent();
                this.addLine('}');
                break;

            case 'position_size':
                this.addLine('balance = data.get("balance", 0)');
                this.addLine(`risk_percentage = ${riskNode.config?.percentage || 2.0}`);
                this.addLine('');
                this.addLine('max_position_size = (balance * risk_percentage) / 100');
                this.addLine('');
                this.addLine('return {');
                this.indent();
                this.addLine('"max_size": max_position_size,');
                this.addLine('"risk_percentage": risk_percentage');
                this.dedent();
                this.addLine('}');
                break;

            case 'max_trades':
                this.addLine(`max_per_day = ${riskNode.config?.maxPerDay || 10}`);
                this.addLine('current_trades = self.execution_count');
                this.addLine('');
                this.addLine('can_trade = current_trades < max_per_day');
                this.addLine('');
                this.addLine('return {');
                this.indent();
                this.addLine('"can_trade": can_trade,');
                this.addLine('"current_trades": current_trades,');
                this.addLine('"max_trades": max_per_day');
                this.dedent();
                this.addLine('}');
                break;

            default:
                this.addLine('return {"passed": True}');
        }

        this.dedent();
        this.addLine('');
    }

    generateExecuteMethod(workflow) {
        this.addLine('async def execute(self, market_data: Dict[str, Any]) -> Dict[str, Any]:');
        this.indent();
        this.addLine('"""Main strategy execution method."""');
        this.addLine('try:');
        this.indent();
        this.addLine('# Check all triggers');

        const triggers = workflow.blocks.filter(b => b.category === 'triggers');
        if (triggers.length > 0) {
            this.addLine('trigger_results = []');
            for (const trigger of triggers) {
                const methodName = this.sanitizeName(trigger.name || trigger.type);
                this.addLine(`trigger_results.append(await self.check_${methodName}(market_data))`);
            }
            this.addLine('');
            this.addLine('# If no triggers are met, exit');
            this.addLine('if not any(trigger_results):');
            this.indent();
            this.addLine('return {"executed": False, "reason": "No triggers met"}');
            this.dedent();
            this.addLine('');
        }

        // Generate execution flow based on connections
        this.addLine('# Execute workflow');
        this.addLine('self.execution_count += 1');
        this.addLine('self.last_execution = datetime.now()');
        this.addLine('');
        this.addLine('return {');
        this.indent();
        this.addLine('"executed": True,');
        this.addLine('"timestamp": datetime.now().isoformat(),');
        this.addLine('"execution_count": self.execution_count');
        this.dedent();
        this.addLine('}');

        this.dedent();
        this.addLine('except Exception as e:');
        this.indent();
        this.addLine('return {');
        this.indent();
        this.addLine('"executed": False,');
        this.addLine('"error": str(e),');
        this.addLine('"timestamp": datetime.now().isoformat()');
        this.dedent();
        this.addLine('}');
        this.dedent();
        this.dedent();
    }

    // Helper methods
    addLine(text) {
        const indent = ' '.repeat(this.indentLevel * this.indentSize);
        this.code.push(indent + text);
    }

    indent() {
        this.indentLevel++;
    }

    dedent() {
        this.indentLevel = Math.max(0, this.indentLevel - 1);
    }

    sanitizeName(name) {
        return name
            .toLowerCase()
            .replace(/[^a-z0-9_]/g, '_')
            .replace(/^[0-9]/, '_$&')
            .replace(/_+/g, '_');
    }
}

// Create global instance
const codeGenerator = new CodeGenerator();
