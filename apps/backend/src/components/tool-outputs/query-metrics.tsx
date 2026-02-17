import { pluralize } from '@dazense/shared';
import type { queryMetrics } from '@dazense/shared/tools';

import { Block, CodeBlock, ListItem, Span, Title, TitledList } from '../../lib/markdown';
import { truncateMiddle } from '../../utils/utils';

const MAX_ROWS = 20;

export const QueryMetricsOutput = ({
	output,
	maxRows = MAX_ROWS,
}: {
	output: queryMetrics.Output;
	maxRows?: number;
}) => {
	if (output.data.length === 0) {
		return <Block>The metric query was successfully executed and returned no rows.</Block>;
	}

	const isTruncated = output.data.length > maxRows;
	const visibleRows = isTruncated ? output.data.slice(0, maxRows) : output.data;
	const remainingRows = isTruncated ? output.data.length - maxRows : 0;

	return (
		<Block>
			<Span>Query ID: {output.id}</Span>
			<Span>
				Model: {output.model_name} | Measures: {output.measures.join(', ')} | Dimensions:{' '}
				{output.dimensions.length > 0 ? output.dimensions.join(', ') : 'none'}
			</Span>

			<TitledList title={`${pluralize('Column', output.columns.length)} (${output.columns.length})`}>
				{output.columns.map((column) => (
					<ListItem>{column}</ListItem>
				))}
			</TitledList>

			<Title>
				{pluralize('Row', output.row_count)} ({output.row_count})
			</Title>

			<Block>
				{visibleRows.map((row, i) => (
					<CodeBlock header={`#${i + 1}`}>
						<Block separator={'\n'}>
							{Object.entries(row).map(([key, value]) => `${key}: ${formatRowValue(value)}`)}
						</Block>
					</CodeBlock>
				))}
			</Block>

			{remainingRows > 0 && <Span>...({remainingRows} more)</Span>}
		</Block>
	);
};

const formatRowValue = (value: unknown) => {
	let strValue = '';
	if (typeof value === 'object') {
		strValue = JSON.stringify(value);
	} else {
		strValue = String(value);
	}
	return truncateMiddle(strValue, 255);
};
