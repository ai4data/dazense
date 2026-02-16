import z from 'zod/v3';

export const InputSchema = z.object({
	category: z.string().optional().describe('Filter rules by category (e.g. "data_quality", "metrics")'),
	concepts: z
		.array(z.string())
		.default([])
		.describe('Filter rules by related concepts (e.g. ["tip_amount", "orders.total_revenue"])'),
});

export const RuleSchema = z.object({
	name: z.string(),
	category: z.string(),
	severity: z.string(),
	applies_to: z.array(z.string()),
	description: z.string(),
	guidance: z.string(),
});

export const OutputSchema = z.object({
	_version: z.literal('1').optional(),
	rules: z.array(RuleSchema),
	categories: z.array(z.string()),
});

export type Input = z.infer<typeof InputSchema>;
export type Output = z.infer<typeof OutputSchema>;
