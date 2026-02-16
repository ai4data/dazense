import type { classify } from '@nao/shared/tools';
import { classify as schemas } from '@nao/shared/tools';

import { ClassifyOutput, renderToModelOutput } from '../../components/tool-outputs';
import { env } from '../../env';
import { createTool, type ToolContext } from '../../types/tools';

async function executeClassify({ name, tags }: classify.Input, context: ToolContext): Promise<classify.Output> {
	const response = await fetch(`http://localhost:${env.FASTAPI_PORT}/classify`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			nao_project_folder: context.projectFolder,
			...(name && { name }),
			...(tags?.length && { tags }),
		}),
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({ detail: response.statusText }));
		throw new Error(`Error fetching classifications: ${JSON.stringify(errorData.detail)}`);
	}

	const data = await response.json();
	return {
		_version: '1',
		...data,
	};
}

export default createTool({
	description:
		'Look up entity classifications to understand what category a data entity belongs to and why it has certain characteristics. Use this to explain patterns in data (e.g. why airport trips have flat fares, what defines a commute trip).',
	inputSchema: schemas.InputSchema,
	outputSchema: schemas.OutputSchema,
	execute: executeClassify,
	toModelOutput: ({ output }) => renderToModelOutput(ClassifyOutput({ output }), output),
});
