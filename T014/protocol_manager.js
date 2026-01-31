class ProtocolManager extends ProtocolExecutor {
    constructor() {
        super();
        Object.assign(this, new ProtocolSteps());
        this.executions = new Map();
        this.listeners = [];
    }

    async startExecution(protocolId, protocolData) {
        const executionId = 'exec_' + Date.now();
        const execution = {
            id: executionId,
            protocolId,
            status: 'starting',
            startTime: new Date(),
            currentStep: 0,
            totalSteps: 13
        };
        
        this.executions.set(executionId, execution);
        this.notifyListeners('execution_started', execution);
        
        try {
            const result = await this.executeProtocol({
                id: protocolId,
                ...protocolData
            });
            
            execution.status = result.success ? 'completed' : 'failed';
            execution.endTime = new Date();
            execution.result = result;
            
            this.notifyListeners('execution_completed', execution);
            return execution;
        } catch (error) {
            execution.status = 'error';
            execution.error = error.message;
            execution.endTime = new Date();
            
            this.notifyListeners('execution_failed', execution);
            throw error;
        }
    }

    getExecutionStatus(executionId) {
        return this.executions.get(executionId) || null;
    }

    getAllExecutions() {
        return Array.from(this.executions.values());
    }

    addListener(callback) {
        this.listeners.push(callback);
    }

    removeListener(callback) {
        const index = this.listeners.indexOf(callback);
        if (index > -1) this.listeners.splice(index, 1);
    }

    notifyListeners(event, data) {
        this.listeners.forEach(listener => {
            try {
                listener(event, data);
            } catch (error) {
                console.error('Listener error:', error);
            }
        });
    }

    getStepProgress() {
        return {
            current: this.currentStep,
            total: this.steps.length,
            percentage: Math.round((this.currentStep / this.steps.length) * 100),
            currentStepName: this.steps[this.currentStep - 1] || 'not started'
        };
    }
}