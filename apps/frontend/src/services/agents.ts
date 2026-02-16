import type { Chat } from '@ai-sdk/react';
import type { UIMessage } from '@nao/backend/chat';

/** An agent is a chat instance with tools */
export type Agent = Chat<UIMessage>;

/** A map of agent instances, to allow running agents in parallel across tabs */
const agents = new Map<string, Agent>();

export const agentService = {
	getAgent(agentId: string): Agent | undefined {
		return agents.get(agentId);
	},
	registerAgent(agentId: string, agent: Agent): Agent {
		agents.set(agentId, agent);
		return agent;
	},
	disposeAgent(agentId: string): void {
		agents.delete(agentId);
	},
	moveAgent(fromId: string, toId: string): void {
		const agent = agents.get(fromId);
		if (!agent) {
			console.warn(`moveAgent: agent ${fromId} not found, skipping move to ${toId}`);
			return;
		}
		agents.delete(fromId);
		agents.set(toId, agent);
	},
};
