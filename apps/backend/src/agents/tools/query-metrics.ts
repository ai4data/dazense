import type { queryMetrics } from '@nao/shared/tools';
import { queryMetrics as schemas } from '@nao/shared/tools';

import { QueryMetricsOutput, renderToModelOutput } from '../../components/tool-outputs';
import { env } from '../../env';
import { createTool, type ToolContext } from '../../types/tools';

async function executeQueryMetrics(
	{ model_name, measures, dimensions, filters, order_by, limit, database_id }: queryMetrics.Input,
	context: ToolContext,
): Promise<queryMetrics.Output> {
	const response = await fetch(`http://localhost:${env.FASTAPI_PORT}/query_metrics`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			nao_project_folder: context.projectFolder,
			model_name,
			measures,
			dimensions,
			filters,
			order_by,
			limit,
			...(database_id && { database_id }),
		}),
	});

	if (!response.ok) {
		const errorData = await response.json().catch(() => ({ detail: response.statusText }));
		throw new Error(`Error querying metrics: ${JSON.stringify(errorData.detail)}`);
	}

	const data = await response.json();
	return {
		_version: '1',
		...data,
		id: `query_${crypto.randomUUID().slice(0, 8)}`,
	};
}

export default createTool({
	description:
		'Query pre-defined metrics from the semantic layer. Use this instead of writing raw SQL when the required measures and dimensions are available in the semantic model.',
	inputSchema: schemas.InputSchema,
	outputSchema: schemas.OutputSchema,
	execute: executeQueryMetrics,
	toModelOutput: ({ output }) => renderToModelOutput(QueryMetricsOutput({ output }), output),
});
