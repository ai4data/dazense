import type { UIMessage } from '@dazense/backend/chat';

/** A group of user and response (agent) messages */
export interface MessageGroup {
	user: UIMessage;
	/** The response (agent) messages */
	responses: UIMessage[];
}
