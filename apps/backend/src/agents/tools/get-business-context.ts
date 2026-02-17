import type { getBusinessContext } from '@dazense/shared/tools';
import { getBusinessContext as schemas } from '@dazense/shared/tools';

import { GetBusinessContextOutput, renderToModelOutput } from '../../components/tool-outputs';
import { env } from '../../env';
import { createTool, type ToolContext } from '../../types/tools';

async function executeGetBusinessContext(
	{ category, concepts }: getBusinessContext.Input,
	context: ToolContext,
): Promise<getBusinessContext.Output> {
	const response = await fetch(`http://localhost:${env.FASTAPI_PORT}/business_context`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			dazense_project_folder: context.projectFolder,
			...(category && { category }),
			...(concepts?.length && { concepts }),
		}),
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({ detail: response.statusText }));
		throw new Error(`Error fetching business context: ${JSON.stringify(errorData.detail)}`);
	}

	const data = await response.json();
	return {
		_version: '1',
		...data,
	};
}

export default createTool({
	description:
		'Retrieve business rules and data caveats that apply to a given category or set of concepts. Use this to understand data quality issues, metric definitions, and business logic before querying data.',
	inputSchema: schemas.InputSchema,
	outputSchema: schemas.OutputSchema,
	execute: executeGetBusinessContext,
	toModelOutput: ({ output }) => renderToModelOutput(GetBusinessContextOutput({ output }), output),
});
