import type { classify } from '@dazense/shared/tools';

import { Block, Bold, CodeBlock, ListItem, Span, Title, TitledList } from '../../lib/markdown';

export const ClassifyOutput = ({ output }: { output: classify.Output }) => {
	if (output.classifications.length === 0) {
		return <Block>No classifications found matching the query.</Block>;
	}

	return (
		<Block>
			<Title>Classifications ({output.classifications.length})</Title>
			{output.classifications.map((classification) => (
				<Block>
					<Span>
						<Bold>{classification.name}</Bold>
					</Span>
					<Span>{classification.description}</Span>
					<CodeBlock header='Condition'>{classification.condition}</CodeBlock>
					{classification.tags.length > 0 && <Span>Tags: {classification.tags.join(', ')}</Span>}
					{Object.keys(classification.characteristics).length > 0 && (
						<TitledList title='Characteristics'>
							{Object.entries(classification.characteristics).map(([key, value]) => (
								<ListItem>
									<Bold>{key}</Bold>: {value}
								</ListItem>
							))}
						</TitledList>
					)}
				</Block>
			))}
			<Span>Available classifications: {output.available_names.join(', ')}</Span>
		</Block>
	);
};
