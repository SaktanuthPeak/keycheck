import { transition, type FlowEvent, type FlowState } from './machine';

/** Reactive wrapper around the pure state machine; one instance per page. */
export class Flow {
	state = $state<FlowState>('idle');

	constructor(initial: FlowState = 'idle') {
		this.state = initial;
	}

	send(event: FlowEvent): FlowState {
		this.state = transition(this.state, event);
		return this.state;
	}

	is(...states: FlowState[]): boolean {
		return states.includes(this.state);
	}
}
