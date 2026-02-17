import type { getBusinessContext } from '@dazense/shared/tools';

import { Block, Bold, ListItem, Span, Title, TitledList } from '../../lib/markdown';

export const GetBusinessContextOutput = ({ output }: { output: getBusinessContext.Output }) => {
	if (output.rules.length === 0) {
		return <Block>No business rules found matching the query.</Block>;
	}

	return (
		<Block>
			<Title>Business Rules ({output.rules.length})</Title>
			{output.rules.map((rule) => (
				<Block>
					<Span>
						<Bold>
							[{rule.severity}] {rule.name}
						</Bold>{' '}
						({rule.category})
					</Span>
					<Span>{rule.description}</Span>
					<Span>Guidance: {rule.guidance}</Span>
					{rule.applies_to.length > 0 && (
						<TitledList title='Applies to'>
							{rule.applies_to.map((item) => (
								<ListItem>{item}</ListItem>
							))}
						</TitledList>
					)}
				</Block>
			))}
			<Span>Categories: {output.categories.join(', ')}</Span>
		</Block>
	);
};
