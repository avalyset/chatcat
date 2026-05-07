# Contributing

## Ethics-first review

All pull requests that modify agent behaviour, stress thresholds, action
spaces, or session limits must carry the `ethics-required-review` label. These
PRs require explicit sign-off before merge.

Any person may open an issue raising a welfare concern. Such issues
automatically receive the `ethics-required-review` label.

## Code conventions

- TypeScript strict mode
- All behaviour parameters must cite a published source in a code comment
- Tests must pass before merge: `pnpm test`
- Conventional commits format

## What we will not merge

- Prey-mimicry actions without closed-loop reward validation
- Removal or weakening of ethics monitor thresholds
- Engagement-maximising features that lack welfare justification
- Changes that make the ethics monitor configurable or bypassable by the agent
